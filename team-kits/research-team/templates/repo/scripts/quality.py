#!/usr/bin/env python3
"""
quality.py — the deterministic quality pipeline (the thing the constitution promised).

Runs the real tools and FAILS (exit 1) on any hard problem, so "pipeline green" is a fact, not a
self-reported YAML string. Used three ways: by the `gate_pipeline` hook before merge/push, by the
shipped pre-commit config, and by CI. The DevOps role owns and may extend it.

Config-driven, not hardcoded to Python+JS:
  - Active stacks come from project_memory/project_config.yaml `stacks: [...]` (inline OR block list) if
    present, else they are auto-detected. A DECLARED stack with no check definition here is a FAIL (no
    silent "green empty gate" for Rust/Go/.NET/…) — DevOps must add its checks.
  - Per stack: lint, types, tests+coverage (core, hard-fail) and SAST/SCA (security).
  - Repo-wide security: secret scan + SBOM.

Policy: a CORE tool missing for an ACTIVE stack is a FAIL (the pipeline must be set up). SECURITY tools
missing are a WARN locally but are installed + enforced in CI (requirements-dev.txt + ci.yml). Findings
from any tool are a hard FAIL (with a tail of the tool's own output for debugging). No source for a stack
-> that stack is skipped (auto-detect) or fails cleanly (explicitly declared but its files are absent).

Exit 0 = all green. Exit 1 = at least one hard failure. Cross-platform (uses shutil.which).
"""
import importlib.util
import os
import re
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FAILS, WARNS, OKS = [], [], []


def have(tool):
    return shutil.which(tool) is not None


def run(cmd, cwd=None):
    try:
        p = subprocess.run(cmd, cwd=cwd or ROOT, capture_output=True, text=True, timeout=1800)
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except Exception as e:
        return 1, str(e)


def has_files(rel_dir, exts, skip=("node_modules", "dist", "build", "__pycache__", ".venv", "venv", "target")):
    d = os.path.join(ROOT, rel_dir)
    if not os.path.isdir(d):
        return False
    for dp, dn, fn in os.walk(d):
        dn[:] = [x for x in dn if x not in skip]
        for f in fn:
            if os.path.splitext(f)[1].lower() in exts:
                return True
    return False


def rootfile(*names):
    return any(os.path.isfile(os.path.join(ROOT, n)) for n in names)


def coverage_threshold():
    p = os.path.join(ROOT, "project_memory", "testing_guidelines.yaml")
    try:
        m = re.search(r"(?m)^\s*threshold:\s*(\d+)", open(p, encoding="utf-8", errors="ignore").read())
        return int(m.group(1)) if m else 80
    except Exception:
        return 80


def declared_stacks():
    """Parse `stacks:` from project_config.yaml — supports inline `[a, b]` AND block (`- a`) form."""
    p = os.path.join(ROOT, "project_memory", "project_config.yaml")
    try:
        txt = open(p, encoding="utf-8", errors="ignore").read()
    except Exception:
        return []
    out = []
    m = re.search(r"(?m)^\s*stacks:\s*\[([^\]]*)\]", txt)
    if m:
        out = [s.strip().strip("'\"").lower() for s in m.group(1).split(",") if s.strip()]
    else:
        m = re.search(r"(?m)^[ \t]*stacks:[ \t]*$", txt)
        if m:
            for line in txt[m.end():].splitlines():
                mm = re.match(r"[ \t]*-[ \t]*([A-Za-z0-9_+-]+)[ \t]*$", line)
                if mm:
                    out.append(mm.group(1).lower())
                elif line.strip():
                    break  # left the list block
    return [s for s in out if s != "todo"]  # the [TODO] placeholder does not count as declared


def ok(name):
    OKS.append(name)


def fail(name, detail=""):
    FAILS.append(name + ((" — " + detail) if detail else ""))


def warn(name, detail=""):
    WARNS.append(name + ((" — " + detail) if detail else ""))


def _tail(out):
    out = (out or "").strip()
    return (" :: " + out[-300:]) if out else ""


def _core(name, tool, cmd, detail):
    if not have(tool):
        fail(name, "%s not installed — set up the dev requirements" % tool)
        return
    rc, out = run(cmd)
    ok(name) if rc == 0 else fail(name, detail + _tail(out))


def _sec(name, tool, cmd, detail):
    if not have(tool):
        warn(name, "%s not installed; runs + hard-fails in CI" % tool)
        return
    rc, out = run(cmd)
    ok(name) if rc == 0 else fail(name, detail + _tail(out))


# ---------------- per-stack check definitions ----------------
def check_python():
    tgt = "src" if os.path.isdir(os.path.join(ROOT, "src")) else "."
    thr = coverage_threshold()
    _core("ruff (lint)", "ruff", ["ruff", "check", "."], "lint errors")
    _core("mypy (types)", "mypy", ["mypy", tgt], "type errors")
    if os.path.isdir(os.path.join(ROOT, "tests")) and has_files("tests", {".py"}):
        # pytest-xdist (requirements-dev) parallelizes across cores when installed — a serial suite is
        # the measured top time eater; pytest-cov combines per-worker coverage correctly.
        par = ["-n", "auto"] if importlib.util.find_spec("xdist") else []
        name = "pytest (+cov>=%d%%%s)" % (thr, ", -n auto" if par else "")
        if not have("pytest"):
            fail(name, "pytest not installed — set up the dev requirements")
        else:
            rc, out = run(["pytest", "-q", *par, "--cov=" + tgt, "--cov-fail-under=" + str(thr)])
            if rc != 0 and par and "unrecognized arguments" in out:
                # xdist importable in THIS interpreter but the PATH pytest lacks the plugin —
                # retry serial instead of hard-failing on a tooling mismatch (mirrors check_node)
                rc, out = run(["pytest", "-q", "--cov=" + tgt, "--cov-fail-under=" + str(thr)])
            ok(name) if rc == 0 else fail(name, "tests failed or coverage below %d%%" % thr + _tail(out))
    _sec("bandit (SAST)", "bandit", ["bandit", "-r", tgt, "-ll", "-q"], "high-severity finding")
    _sec("pip-audit (SCA)", "pip-audit", ["pip-audit"], "vulnerable dependency")


def check_node():
    fe = os.path.join(ROOT, "frontend")
    pkgf = os.path.join(fe, "package.json")
    if not os.path.isfile(pkgf):
        fail("frontend (node)", "declared a node/typescript stack but no frontend/package.json")
        return
    if not have("npm"):
        fail("npm toolchain", "npm not installed — set up the frontend toolchain")
        return
    pkg = open(pkgf, encoding="utf-8", errors="ignore").read()
    if '"lint"' in pkg:
        rc, out = run(["npm", "run", "-s", "lint"], cwd=fe)
        ok("eslint (lint)") if rc == 0 else fail("eslint (lint)", "lint errors" + _tail(out))
    # type-check only when the project is actually TypeScript-configured
    if os.path.isfile(os.path.join(fe, "tsconfig.json")):
        rc, out = run(["npx", "--no-install", "tsc", "--noEmit"], cwd=fe)
        ok("tsc (types)") if rc == 0 else fail("tsc (types)", "type errors" + _tail(out))
    if '"test"' in pkg:
        rc, out = run(["npm", "run", "-s", "test", "--", "--run", "--coverage"], cwd=fe)
        if rc != 0:
            rc, out = run(["npm", "run", "-s", "test"], cwd=fe)
        ok("frontend tests") if rc == 0 else fail("frontend tests", "tests failed" + _tail(out))
    else:
        fail("frontend tests", "no test script — frontend must be tested")
    rc, out = run(["npm", "audit", "--audit-level=high"], cwd=fe)
    if rc != 0 and "vulnerab" in out.lower():
        fail("npm audit (SCA)", "high/critical vulnerability")


def check_go():
    _core("go vet", "go", ["go", "vet", "./..."], "vet errors")
    _core("go test (+cover)", "go", ["go", "test", "-cover", "./..."], "tests failed")


def check_rust():
    _core("cargo clippy", "cargo", ["cargo", "clippy", "--", "-D", "warnings"], "clippy warnings")
    _core("cargo test", "cargo", ["cargo", "test"], "tests failed")


def check_dotnet():
    _core("dotnet format", "dotnet", ["dotnet", "format", "--verify-no-changes"], "format/style issues")
    _core("dotnet test", "dotnet", ["dotnet", "test"], "tests failed")


def check_embedded():
    # firmware / C-C++ — PlatformIO build + tests + static analysis; Wokwi is the simulation real-run.
    if rootfile("platformio.ini"):
        _core("pio build", "pio", ["pio", "run"], "firmware build failed")
        _core("pio test", "pio", ["pio", "test"], "unit/sim tests failed")
    else:
        fail("embedded toolchain", "declared embedded but no platformio.ini — DevOps must wire the "
             "build/test (PlatformIO) + Wokwi simulation into scripts/quality.py")
    if have("cppcheck"):
        rc, out = run(["cppcheck", "--error-exitcode=1", "--enable=warning,style", "."])
        ok("cppcheck (SAST)") if rc == 0 else fail("cppcheck (SAST)", "static analysis findings" + _tail(out))


STACKS = {
    "python": {"detect": lambda: has_files("src", {".py"}) or rootfile("app.py", "main.py"), "run": check_python},
    "node": {"detect": lambda: os.path.isfile(os.path.join(ROOT, "frontend", "package.json")), "run": check_node},
    "typescript": {"detect": lambda: os.path.isfile(os.path.join(ROOT, "frontend", "package.json")), "run": check_node},
    "go": {"detect": lambda: rootfile("go.mod"), "run": check_go},
    "rust": {"detect": lambda: rootfile("Cargo.toml"), "run": check_rust},
    "dotnet": {"detect": lambda: has_files(".", {".csproj", ".sln"}), "run": check_dotnet},
    "embedded": {"detect": lambda: rootfile("platformio.ini"), "run": check_embedded},
    "cpp": {"detect": lambda: has_files(".", {".c", ".cpp", ".ino"}), "run": check_embedded},
    "c": {"detect": lambda: has_files(".", {".c", ".h"}), "run": check_embedded},
}


def check_project_memory_yaml():
    """Every project_memory/*.yaml must parse and carry no duplicate keys (safe_load keeps only the
    last duplicate silently). A real run shipped invalid decisions.yaml that the dashboard generator
    swallowed; the write-time hook (guard_yaml_valid) catches this immediately — this stage is the
    merge/CI backstop."""
    d = os.path.join(ROOT, "project_memory")
    if not os.path.isdir(d):
        return
    try:
        import yaml  # type: ignore[import-untyped]
    except ImportError:
        warn("yaml-lint (project_memory)", "pyyaml not installed; runs + hard-fails in CI")
        return

    def dup_keys(text):
        found = []
        try:
            root = yaml.compose(text, Loader=yaml.SafeLoader)
        except Exception:
            return found
        stack = [root] if root is not None else []
        visited = set()  # anchors/aliases make the node graph cyclic — never walk a node twice
        while stack:
            node = stack.pop()
            if id(node) in visited:
                continue
            visited.add(id(node))
            if isinstance(node, yaml.MappingNode):
                seen = set()
                for k, v in node.value:
                    if isinstance(k, yaml.ScalarNode):
                        if k.value in seen:
                            found.append("duplicate key %r line %d" % (k.value, k.start_mark.line + 1))
                        seen.add(k.value)
                    stack.append(k)
                    stack.append(v)
            elif isinstance(node, yaml.SequenceNode):
                stack.extend(node.value)
        return found

    bad = []
    for fn in sorted(os.listdir(d)):
        if not fn.endswith((".yaml", ".yml")):
            continue
        try:
            text = open(os.path.join(d, fn), encoding="utf-8", errors="ignore").read()
        except Exception:
            continue
        try:
            data = yaml.safe_load(text)
        except yaml.YAMLError as e:
            bad.append("%s: %s" % (fn, str(e).splitlines()[0]))
            continue
        for msg in dup_keys(text):
            bad.append("%s: %s" % (fn, msg))
        # progress.yaml contract (same thresholds as the write-time guard_yaml_valid): the guard only
        # sees Edit/Write tool calls — a status blob written via a SHELL heredoc/script bypasses it
        # (a real PM grew a 42k-char "one-liner" exactly that way). This stage catches it at every
        # pipeline run and at merge, whatever wrote the file.
        if fn == "progress.yaml" and isinstance(data, dict):
            status = data.get("status")
            if isinstance(status, str):
                nlines = len([ln for ln in status.splitlines() if ln.strip()])
                if nlines > 3 or len(status) > 700:
                    bad.append("progress.yaml: status is %d non-empty lines / %d chars — it MUST stay "
                               "ONE line (state + concrete next action); history belongs in the "
                               "append-only log: list" % (nlines, len(status)))
            if "log" not in data:
                bad.append("progress.yaml: the append-only log: list is missing (keep `log: []` even "
                           "when empty; history goes there, never into status)")
    ok("yaml-lint (project_memory)") if not bad else fail("yaml-lint (project_memory)", "; ".join(bad[:6]))


# Browser APIs that need a SECURE CONTEXT (https / localhost) — raw use is silently dead on a
# plain-http LAN origin, and jsdom/unit tests stay green (a real run shipped a browser-dead send
# button exactly this way). Route them through ONE helper with a fallback; mark the reviewed helper
# line with a `secure-context` comment to satisfy this check.
SECURE_CONTEXT_APIS = ("crypto.randomUUID", "navigator.clipboard")
_LOCAL_HOSTS = ("localhost", "127.0.0.1", "0.0.0.0", "[::1]")


def _local_first_declared():
    p = os.path.join(ROOT, "project_memory", "project_config.yaml")
    try:
        return bool(re.search(r"(?m)^\s*local_first:\s*true\b",
                              open(p, encoding="utf-8", errors="ignore").read()))
    except Exception:
        return False


def _frontend_sources():
    """Browser-facing sources: everything under frontend/static/public, plus .html anywhere in src/
    and js/css under a static|public|www subdir of src/ (vanilla apps served by the backend). Plain
    backend .js under src/ is deliberately excluded — Node has no secure-context restriction."""
    exts = {".js", ".mjs", ".ts", ".jsx", ".tsx", ".html", ".css", ".svelte", ".vue"}
    # vendored/generated code is not ours to fix — a `.next/` chunk or a vendored lib containing
    # crypto.randomUUID must not turn the gate red (dot-dirs, vendor dirs, *.min.* are skipped below).
    skip = ("node_modules", "dist", "build", "__pycache__", ".venv", "venv", "coverage", "target",
            "vendor", "third_party")
    for rel, browser_only in (("frontend", False), ("static", False), ("public", False), ("src", True)):
        d = os.path.join(ROOT, rel)
        if not os.path.isdir(d):
            continue
        for dp, dn, fn in os.walk(d):
            dn[:] = [x for x in dn if x not in skip and not x.startswith(".")]
            for f in fn:
                ext = os.path.splitext(f)[1].lower()
                if ext not in exts:
                    continue
                if browser_only and ext != ".html":
                    parts = os.path.relpath(dp, ROOT).replace("\\", "/").split("/")
                    if not {"static", "public", "www"} & set(parts):
                        continue
                yield os.path.join(dp, f)


def check_frontend_pitfalls():
    """Greps for what jsdom-green tests cannot catch: (a) raw secure-context-only APIs (see
    SECURE_CONTEXT_APIS above); (b) with project_config `local_first: true`, frontend RESOURCES
    loaded from an external origin (CDN fonts/scripts — a real local-first run shipped a Google-CDN
    font no gate caught). Only resource loads count (link/script/img src, css url()/@import) — a
    plain <a href> link to an external site stays legal."""
    api_hits, cdn_hits, scanned = [], [], False
    local_first = _local_first_declared()
    # (?:https?:)?// also catches protocol-relative loads like href="//fonts.googleapis.com/…"
    res_html = re.compile(r"<(?:link|script|img)\b[^>]*?(?:href|src)\s*=\s*[\"']((?:https?:)?//[^\"']+)", re.I)
    res_css = re.compile(r"(?:url\(\s*[\"']?|@import\s+[\"'])((?:https?:)?//[^\"')]+)", re.I)
    for path in _frontend_sources():
        scanned = True
        rel = os.path.relpath(path, ROOT)
        minified = os.path.basename(path).lower().endswith((".min.js", ".min.css"))
        try:
            lines = open(path, encoding="utf-8", errors="ignore").read().splitlines()
        except Exception:
            continue
        prev = ""
        for i, line in enumerate(lines, 1):
            # minified bundles keep API names but are vendored — only OUR code gets the API grep;
            # the local-first RESOURCE grep still applies (an external font in a .min.css is a violation)
            if not minified and any(api in line for api in SECURE_CONTEXT_APIS):
                if "secure-context" not in line and "secure-context" not in prev:
                    api_hits.append("%s:%d" % (rel, i))
            if local_first and os.path.splitext(path)[1].lower() in (".html", ".css"):
                for rx in (res_html, res_css):
                    for m in rx.finditer(line):
                        if not any(h in m.group(1) for h in _LOCAL_HOSTS):
                            cdn_hits.append("%s:%d %s" % (rel, i, m.group(1)[:80]))
            prev = line
    if api_hits:
        fail("secure-context APIs", "raw %s used (%s%s) — silently dead on a non-secure origin "
             "(http:// over LAN); use ONE helper with a fallback and mark it `secure-context`"
             % ("/".join(SECURE_CONTEXT_APIS), "; ".join(api_hits[:5]), " …" if len(api_hits) > 5 else ""))
    if cdn_hits:
        fail("local-first assets", "external asset load(s) in a local_first project: %s%s — bundle "
             "them locally (fonts/scripts/styles must not leave the machine)"
             % ("; ".join(cdn_hits[:5]), " …" if len(cdn_hits) > 5 else ""))
    if scanned and not api_hits and not cdn_hits:
        ok("frontend pitfalls (secure-context%s)" % (", local-first assets" if local_first else ""))


def secret_scan():
    if have("gitleaks"):
        rc, out = run(["gitleaks", "detect", "--no-banner", "-r", os.devnull])
        ok("gitleaks (secrets)") if rc == 0 else fail("gitleaks (secrets)", "potential secret" + _tail(out))
    else:
        warn("gitleaks (secrets)", "not installed; runs + hard-fails in CI")


def sbom():
    if have("cyclonedx-py"):
        run(["cyclonedx-py", "environment", "-o", "sbom.json"])
        ok("SBOM (sbom.json)")
    else:
        warn("SBOM", "cyclonedx-py not installed; generated in CI")


def main():
    active = declared_stacks()
    ran = set()
    if active:
        for s in active:
            if s not in STACKS:
                fail("stack '%s'" % s, "no quality checks defined — DevOps must add them to scripts/quality.py")
                continue
            fn = STACKS[s]["run"]
            if fn in ran:
                continue  # e.g. node + typescript share one runner
            ran.add(fn)
            try:
                fn()
            except Exception as e:
                fail("stack '%s'" % s, "runner errored: %s" % e)
    else:
        detected = []
        for s, spec in STACKS.items():
            fn = spec["run"]
            if fn in ran:
                continue
            try:
                if spec["detect"]():
                    ran.add(fn)
                    detected.append(s)
                    fn()
            except Exception as e:
                fail("stack '%s'" % s, "runner errored: %s" % e)
        if detected:
            fail("stacks not declared",
                 "code detected (%s) but project_config.yaml `stacks:` is empty/TODO. The architect MUST "
                 "declare the project's stacks + domain so the gate enforces the right toolchain — "
                 "auto-detect is not a substitute (this is exactly how a critical tool gets forgotten)."
                 % ", ".join(sorted(set(detected))))
    check_project_memory_yaml()
    check_frontend_pitfalls()
    secret_scan()
    sbom()

    print("[quality] pipeline report")
    for o in OKS:
        print("  PASS  " + o)
    for w in WARNS:
        print("  warn  " + w)
    for f in FAILS:
        print("  FAIL  " + f)
    if not (OKS or FAILS):
        print("  (no source detected — nothing to check)")
    if FAILS:
        print("[quality] %d hard failure(s) — pipeline is RED." % len(FAILS))
        sys.exit(1)
    print("[quality] pipeline GREEN.")
    sys.exit(0)


if __name__ == "__main__":
    main()
