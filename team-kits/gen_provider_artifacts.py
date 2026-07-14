#!/usr/bin/env python3
"""
gen_provider_artifacts.py — generate per-provider agent artifacts from the INSTALLED kit state.

Called by scaffold_team.(ps1|sh) AFTER agents/hooks/settings/constitution are installed, when the
project's project_config.yaml lists extra providers (`providers: [claude, codex]`). Single source
of truth = the installed `.claude/**` + the repo `AGENTS.md`; nothing generated here is ever
hand-maintained per provider (a real agent once hand-cloned the whole kit into `.codex/` — byte
copies that expected the wrong payloads and referenced paths that did not exist).

Generates:
  codex:    .codex/hooks.json           (translated from .claude/settings.json hook registrations;
                                         Codex GA hooks share the event names + exit-2 contract,
                                         verified 2026-07 against the official docs)
            .codex/agents/<role>.toml   (one per installed specialist; NEVER the project lead —
                                         the lead role is carried by AGENTS.md §0, not spawnable)
  copilot:  .github/hooks/team-kit-hooks.json  (PascalCase events -> snake_case payloads + exit-2
                                         deny, per the official hooks reference; UNVERIFIED live —
                                         CI stays the mandatory backstop on Copilot)
            .github/agents/<role>.agent.md

Both providers run the SAME .claude/hooks/*.py scripts (hooks/_compat.py absorbs payload
differences); hook commands are repo-relative because Codex/Copilot run hooks with the session
cwd as working directory and do not set CLAUDE_PROJECT_DIR (_root.py walks to the repo root).
Models are translated per tier via model_tiers.yaml (next to this script). Stdlib only.
"""
import argparse
import json
import os
import re
import sys


HERE = os.path.dirname(os.path.abspath(__file__))

# Claude matcher -> Codex matcher (Codex tool vocabulary: Bash, apply_patch, mcp__*).
# None = do not register on Codex (documented gap, see parity matrix in the README):
#   Agent|Task  — Codex's spawn tool name/blockability is unverified; role existence is enforced
#                 by Codex itself (only defined .codex/agents/*.toml are spawnable).
#   Notification — no such Codex event.
CODEX_MATCHER = {"Write": "apply_patch", "Edit|Write": "apply_patch",
                 "Bash|PowerShell": "Bash", "Agent|Task": None}
CODEX_EVENTS = ("SessionStart", "PreToolUse", "PostToolUse", "SubagentStop", "Stop")
COPILOT_EVENTS = ("SessionStart", "PreToolUse", "PostToolUse", "SubagentStop", "Stop")

ROLE_PREAMBLE = (
    "You are the specialist role described below inside a team-kit governed repository.\n"
    "MANDATORY, in this order: (1) follow ./AGENTS.md — the team constitution — completely;\n"
    "(2) read .claude/skills/%(role)s/SKILL.md BEFORE starting (your full role playbook);\n"
    "(3) end with your YAML output contract (`summary:` — see the skill), never prose-only.\n"
    "Reply to the user in German; ALL artifacts/code (names, comments, YAML keys) in English.\n"
)


def read(path):
    with open(path, encoding="utf-8-sig") as fh:
        return fh.read()


def parse_frontmatter(text):
    """(meta dict, body). Frontmatter = leading --- block of `key: value` lines; folded/literal
    block scalars (`key: >` / `>-` / `|` / `|-`) are joined into one line — an audit found the
    single-line parser collapsed a folded description to a literal '>'."""
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    meta = {}
    lines = parts[1].splitlines()
    i = 0
    while i < len(lines):
        raw = lines[i]
        m = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", raw) if raw[:1].strip() else None
        if not m:
            i += 1
            continue
        key, val = m.group(1), m.group(2).strip()
        if val in (">", ">-", "|", "|-"):
            block = []
            i += 1
            while i < len(lines) and (not lines[i].strip() or lines[i][:1] in (" ", "\t")):
                if lines[i].strip():
                    block.append(lines[i].strip())
                i += 1
            meta[key] = " ".join(block)
            continue
        meta[key] = val
        i += 1
    return meta, parts[2].lstrip("\n")


def load_tiers():
    """Parse model_tiers.yaml with a stdlib mini-parser (file is kit-owned, flat two-level)."""
    tiers, aliases, section, prov = {}, {}, "", ""
    for raw in read(os.path.join(HERE, "model_tiers.yaml")).splitlines():
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        m = re.match(r"^(\s*)([A-Za-z_][A-Za-z0-9_.-]*):\s*(.*)$", line)
        if not m:
            continue
        indent, key, val = len(m.group(1)), m.group(2), m.group(3).strip().strip('"')
        if indent == 0:
            section, prov = key, ""
        elif section == "aliases" and val:
            aliases[key] = val
        elif section == "tiers" and indent == 2:
            prov = key
            tiers[prov] = {}
        elif section == "tiers" and prov and val:
            tiers[prov][key] = val
    return tiers, aliases


def tier_of(model, aliases):
    """Canonical claude-vocabulary tier of a model_map/frontmatter value."""
    return aliases.get(model, model)  # lead->opus etc.; opus/sonnet/haiku pass through


def provider_model(model, provider, tiers, aliases):
    canon = tier_of(model, aliases)             # opus | sonnet | haiku
    rev = {"opus": "lead", "sonnet": "worker", "haiku": "light"}
    tier = rev.get(canon)
    if not tier:
        return model  # unknown/explicit model id — pass through untouched
    return tiers.get(provider, {}).get(tier, model)


def hook_entries(settings, event):
    for group in settings.get("hooks", {}).get(event, []) or []:
        matcher = group.get("matcher", "")
        for h in group.get("hooks", []) or []:
            if h.get("type") == "command" and h.get("command"):
                yield matcher, h


def rel_command(command):
    """`python "${CLAUDE_PROJECT_DIR}/.claude/hooks/x.py"` -> `python ".claude/hooks/x.py"`."""
    return command.replace("${CLAUDE_PROJECT_DIR}/", "").replace("${CLAUDE_PROJECT_DIR}\\", "")


def gen_codex_hooks(settings):
    out = {}
    for event in CODEX_EVENTS:
        groups = {}
        for matcher, h in hook_entries(settings, event):
            cm = CODEX_MATCHER.get(matcher, matcher) if matcher else ""
            if matcher and cm is None:
                continue  # documented no-register gap
            entry = {"type": "command", "command": rel_command(h["command"]),
                     "commandWindows": rel_command(h["command"])}
            if h.get("timeout"):
                entry["timeout"] = h["timeout"]
            groups.setdefault(cm, []).append(entry)
        if groups:
            out[event] = [({"matcher": m, "hooks": hs} if m else {"hooks": hs})
                          for m, hs in groups.items()]
    return {"hooks": out}


def gen_copilot_hooks(settings):
    """PascalCase event names -> Copilot sends snake_case payloads (official hooks reference) and
    treats command exit 2 as deny — i.e. the SAME contract our hooks already speak. No matcher:
    Copilot's tool-name vocabulary is unverified, the hooks filter by normalized tool_name."""
    out = {}
    for event in COPILOT_EVENTS:
        entries = []
        for _matcher, h in hook_entries(settings, event):
            cmd = rel_command(h["command"])
            entry = {"type": "command", "bash": cmd, "powershell": cmd,
                     "timeoutSec": h.get("timeout", 60)}
            entries.append(entry)
        if entries:
            out[event] = entries
    return {"version": 1, "hooks": out}


def toml_str(s):
    return '"""\n' + s.replace('\\', '\\\\').replace('"""', '\\"\\"\\"') + '\n"""'


def gen_codex_agent(role, meta, body, tiers, aliases):
    lines = ['name = "%s"' % role,
             'description = "%s"' % meta.get("description", role).replace('"', "'")]
    model = provider_model(meta.get("model", "sonnet"), "codex", tiers, aliases)
    lines.append('model = "%s"' % model)
    effort = meta.get("effort", "high")
    if effort == "max":
        effort = "xhigh"  # conservative cap: Codex's documented ladder tops at xhigh
    lines.append('model_reasoning_effort = "%s"' % effort)
    instructions = (ROLE_PREAMBLE % {"role": role}) + "\n" + body
    lines.append("developer_instructions = " + toml_str(instructions))
    return "\n".join(lines) + "\n"


def gen_copilot_agent(role, meta, body, tiers, aliases):
    model = provider_model(meta.get("model", "sonnet"), "copilot", tiers, aliases)
    desc = meta.get("description", role).replace('"', "'")  # quoted: colons in prose stay valid YAML
    fm = ["---", "name: %s" % role,
          'description: "%s"' % desc,
          "model: %s" % model, "---", ""]
    return "\n".join(fm) + (ROLE_PREAMBLE % {"role": role}) + "\n" + body


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--providers", required=True, help="comma list: codex,copilot")
    ap.add_argument("--lead", default="project-manager",
                    help="lead role — carried by AGENTS.md, never generated as a spawnable agent")
    args = ap.parse_args()
    repo = os.path.abspath(args.repo)
    providers = [p.strip().lower() for p in args.providers.split(",") if p.strip()]
    providers = [p for p in providers if p in ("codex", "copilot")]
    if not providers:
        return 0

    settings = json.loads(read(os.path.join(repo, ".claude", "settings.json")))
    tiers, aliases = load_tiers()
    agents_dir = os.path.join(repo, ".claude", "agents")
    roles = []
    if os.path.isdir(agents_dir):
        for fn in sorted(os.listdir(agents_dir)):
            if fn.endswith(".md") and fn[:-3] != args.lead:
                meta, body = parse_frontmatter(read(os.path.join(agents_dir, fn)))
                roles.append((fn[:-3], meta, body))

    if "codex" in providers:
        cdir = os.path.join(repo, ".codex")
        os.makedirs(os.path.join(cdir, "agents"), exist_ok=True)
        with open(os.path.join(cdir, "hooks.json"), "w", encoding="utf-8", newline="\n") as fh:
            json.dump(gen_codex_hooks(settings), fh, indent=2)
            fh.write("\n")
        for role, meta, body in roles:
            with open(os.path.join(cdir, "agents", role + ".toml"), "w",
                      encoding="utf-8", newline="\n") as fh:
                fh.write(gen_codex_agent(role, meta, body, tiers, aliases))
        print("  [ok] codex artifacts: .codex/hooks.json + %d agent toml(s) "
              "(BETA: run /hooks once in Codex to trust the project hooks)" % len(roles))

    if "copilot" in providers:
        gdir = os.path.join(repo, ".github")
        os.makedirs(os.path.join(gdir, "hooks"), exist_ok=True)
        os.makedirs(os.path.join(gdir, "agents"), exist_ok=True)
        with open(os.path.join(gdir, "hooks", "team-kit-hooks.json"), "w",
                  encoding="utf-8", newline="\n") as fh:
            json.dump(gen_copilot_hooks(settings), fh, indent=2)
            fh.write("\n")
        for role, meta, body in roles:
            with open(os.path.join(gdir, "agents", role + ".agent.md"), "w",
                      encoding="utf-8", newline="\n") as fh:
                fh.write(gen_copilot_agent(role, meta, body, tiers, aliases))
        print("  [ok] copilot artifacts: .github/hooks/team-kit-hooks.json + %d .agent.md "
              "(UNVERIFIED live — branch protection + CI required checks stay mandatory)" % len(roles))
    return 0


if __name__ == "__main__":
    sys.exit(main())
