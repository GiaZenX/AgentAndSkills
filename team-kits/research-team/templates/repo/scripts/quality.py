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
        _core("pytest (+cov>=%d%%)" % thr, "pytest",
              ["pytest", "-q", "--cov=" + tgt, "--cov-fail-under=" + str(thr)],
              "tests failed or coverage below %d%%" % thr)
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
