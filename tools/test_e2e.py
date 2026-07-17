#!/usr/bin/env python3
"""
End-to-end scenario tests — the REAL provider path, not the unit-test shortcut.

Motivation (audit-proven): the unit suite sends payloads via json.dumps (ASCII-escaped) and
reads hook output in the parent's locale — which made it STRUCTURALLY blind to the Windows
encoding class (cp1252 stdin mojibake, cp1252 subprocess reads) that produced three separate
MAJORs in one week. These scenarios emulate what providers actually do: raw UTF-8 bytes on
stdin, real subprocess chains, umlauts in paths/messages/output.
"""
import json
import os
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOOKS = os.path.join(ROOT, "team-kits", "dev-team", "hooks")
OFFICE_HOOKS = os.path.join(ROOT, "team-kits", "office-team", "hooks")
SCRIPTS = os.path.join(ROOT, "team-kits", "dev-team", "templates", "repo", "scripts")


def raw_hook(name, payload, project_dir, hooks_dir=None):
    """Run a hook exactly like a provider does: raw UTF-8 bytes on stdin, bytes captured."""
    env = dict(os.environ, CLAUDE_PROJECT_DIR=str(project_dir))
    return subprocess.run([sys.executable, os.path.join(hooks_dir or HOOKS, name)],
                          input=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                          capture_output=True, env=env, timeout=120)


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)


def _git(cwd, *args):
    return subprocess.run(["git", "-c", "core.quotepath=off", "-C", str(cwd), *args],
                          capture_output=True, text=True, encoding="utf-8",
                          errors="replace", timeout=30)


# ---------------- scenario: full gate_pipeline chain with UTF-8 runner output ----------------
def test_e2e_gate_pipeline_red_run_shows_utf8_fail_lines(tmp_path):
    """A RED quality.py emitting Vitest-style UTF-8 glyphs (❯) must yield a BLOCK whose stderr
    still contains the FAIL line — the cp1252 read once dropped the ENTIRE output (p.stdout was
    None) and the PM debugged blind for a night."""
    write(str(tmp_path / "project_memory" / "product_requirements.yaml"),
          "requirements:\n  PRD-0001:\n    title: x\n")
    write(str(tmp_path / "scripts" / "quality.py"),
          "import sys\n"
          "for s in (sys.stdout, sys.stderr):\n"
          "    try:\n"
          "        s.reconfigure(encoding='utf-8', errors='replace')\n"
          "    except Exception:\n"
          "        pass\n"
          "print('  \\u276f FAIL  frontend tests \\u2014 K\\u00e4ufer-Flow broken')\n"
          "sys.exit(1)\n")
    payload = {"tool_name": "Bash", "cwd": str(tmp_path),
               "tool_input": {"command": "git push origin main"}}
    r = raw_hook("gate_pipeline.py", payload, tmp_path)
    assert r.returncode == 2
    err = r.stderr.decode("utf-8", "replace")
    assert "FAIL" in err and "frontend tests" in err  # the red line SURVIVES into the block


def test_e2e_gate_pipeline_green_cache_with_umlaut_filename(tmp_path):
    """Green-tree cache round trip in a repo containing an umlaut filename — git status/rev-parse
    output flows through the pinned decoder; second push must hit the cache, not rerun."""
    repo = tmp_path / "repo"
    write(str(repo / "project_memory" / "product_requirements.yaml"),
          "requirements:\n  PRD-0001:\n    title: x\n")
    counter = tmp_path / "runs.txt"  # OUTSIDE the repo — the tree must stay clean
    write(str(repo / "scripts" / "quality.py"),
          "open(r'%s', 'a').write('x')\nprint('[quality] pipeline GREEN.')\n" % str(counter))
    write(str(repo / "Belege" / "Müller_Rechnung.md"), "beleg\n")
    write(str(repo / ".gitignore"), ".claude/.gate_pipeline_green\nproject_memory/.audit/\n")
    for args in (("init", "-q"), ("add", "-A"),
                 ("-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "init")):
        assert _git(repo, *args).returncode == 0
    payload = {"tool_name": "Bash", "cwd": str(repo),
               "tool_input": {"command": "git push origin main"}}
    assert raw_hook("gate_pipeline.py", payload, repo).returncode == 0
    assert raw_hook("gate_pipeline.py", payload, repo).returncode == 0
    assert counter.read_text() == "x"  # second run served from the green-tree cache


# ---------------- scenario: text-matching guards fed raw UTF-8 like a real provider ----------------
def test_e2e_office_fs_tripwire_blocks_umlaut_path_delete(tmp_path):
    """The office fs tripwire must still recognize inbox/archive targets when the path carries
    German umlauts and arrives as raw UTF-8 (the mojibake class silently missed patterns)."""
    payload = {"tool_name": "Bash", "cwd": str(tmp_path),
               "tool_input": {"command": 'rm -rf "archive/3-Rechnungen/Müller GmbH"'}}
    r = raw_hook("guard_fs_tripwire.py", payload, tmp_path, hooks_dir=OFFICE_HOOKS)
    assert r.returncode == 2


def test_e2e_gate_git_umlaut_commit_prose_passes_force_blocks(tmp_path):
    """Umlaut prose in a commit message must not trip the push gate; a real force-push in the
    same raw-UTF-8 shape must still block."""
    prose = {"tool_name": "Bash", "cwd": str(tmp_path),
             "tool_input": {"command":
                            'git commit -m "docs: erklärt warum git push --force verboten ist"'}}
    assert raw_hook("gate_git.py", prose, tmp_path).returncode == 0
    forced = {"tool_name": "Bash", "cwd": str(tmp_path),
              "tool_input": {"command": 'git push origin main --force'}}
    assert raw_hook("gate_git.py", forced, tmp_path).returncode == 2


# ---------------- scenario: kit_checks repo-wide YAML with umlaut filename ----------------
def test_e2e_repo_wide_yaml_parses_umlaut_filenames(tmp_path):
    """A tracked, BROKEN YAML with an umlaut name must be found and named (git quotepath once
    octal-escaped such paths so isfile() skipped them — the file was silently unchecked)."""
    pytest.importorskip("yaml")
    import importlib.util
    spec = importlib.util.spec_from_file_location("kit_checks_e2e",
                                                  os.path.join(SCRIPTS, "kit_checks.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    repo = tmp_path / "repo"
    write(str(repo / "project_memory" / "progress.yaml"), "status: x\nlog: []\n")
    write(str(repo / "config" / "Geschäftskonten.yaml"), "a: [unclosed\n")
    for args in (("init", "-q"), ("add", "-A")):
        assert _git(repo, *args).returncode == 0
    calls = {"ok": [], "fail": [], "warn": []}
    mod.check_project_memory_yaml(str(repo), lambda n, *a: calls["ok"].append(n),
                                  lambda n, m: calls["fail"].append((n, m)),
                                  lambda n, m: calls["warn"].append((n, m)))
    hits = [m for n, m in calls["fail"] if n == "yaml-lint (repo-wide)"]
    assert hits and "Geschäftskonten" in hits[0]  # found AND correctly named, no mojibake


# ---------------- scenario: session_status end-to-end with umlaut branch ----------------
def test_e2e_session_status_survives_umlaut_git_state(tmp_path):
    """SessionStart briefing in a repo whose branch name carries umlauts — the pinned git decode
    must deliver a readable branch line, never crash the hook (additionalContext JSON intact)."""
    repo = tmp_path / "repo"
    write(str(repo / "project_memory" / "progress.yaml"), "status: x\nlog: []\n")
    for args in (("init", "-q", "-b", "feature/PRD-1-büro"), ("add", "-A"),
                 ("-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "init")):
        assert _git(repo, *args).returncode == 0
    payload = {"hook_event_name": "SessionStart", "cwd": str(repo)}
    r = raw_hook("session_status.py", payload, repo)
    assert r.returncode == 0
    out = json.loads(r.stdout.decode("utf-8", "replace"))
    ctx = out["hookSpecificOutput"]["additionalContext"]
    assert "büro" in ctx  # branch survived the decode intact, no mojibake
