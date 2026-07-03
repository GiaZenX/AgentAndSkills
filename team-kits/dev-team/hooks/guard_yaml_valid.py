#!/usr/bin/env python3
"""
PostToolUse(Edit|Write) — validate a project_memory/*.yaml IMMEDIATELY after it is written.

A real run shipped decisions.yaml/architecture.yaml as invalid YAML repeatedly: the architect (a
spec-writing role without Bash) could not parse-check its own artifacts, the dashboard generator
swallowed the error silently, and a pipeline lint only catches it at MERGE time — after which a
different role had to hot-fix another owner's file. This hook closes the loop at WRITE time: the
moment any role writes broken YAML (parse error OR duplicate key — safe_load silently keeps the
last duplicate), it gets the exact error back and fixes its OWN file on the spot.

Parsing uses yaml.safe_load only; duplicate keys are found by walking yaml.compose()'s node graph
(compose builds nodes, never constructs objects — no code-execution surface). PostToolUse exit 2
feeds stderr back to the writing agent. Defensive: not a project_memory yaml / no PyYAML /
internal error -> exit 0.
"""
import json
import os
import sys


def block(base, msg):
    if len(msg) > 600:
        msg = msg[:600] + " …"
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import _audit
        _audit.record("guard_yaml_valid", base)
    except Exception:
        pass
    sys.stderr.write(
        "[team-kit guard] project_memory/%s is INVALID YAML after your edit:\n%s\n"
        "Fix it NOW — you own this artifact. Tips: put prose containing ':' in a block scalar "
        "(key: |), quote strings with special characters, and never repeat a key at the same "
        "level. Do not hand the file to another role; do not leave it broken.\n" % (base, msg)
    )
    sys.exit(2)


def find_duplicate_keys(yaml_mod, text):
    """Walk the composed node graph (no object construction) and collect duplicate mapping keys."""
    dupes = []
    try:
        root = yaml_mod.compose(text, Loader=yaml_mod.SafeLoader)
    except Exception:
        return dupes  # parse problems are reported by safe_load already
    stack = [root] if root is not None else []
    visited = set()  # anchors/aliases make the node graph cyclic — never walk a node twice
    while stack:
        node = stack.pop()
        if id(node) in visited:
            continue
        visited.add(id(node))
        if isinstance(node, yaml_mod.MappingNode):
            seen = set()
            for k, v in node.value:
                if isinstance(k, yaml_mod.ScalarNode):
                    if k.value in seen:
                        dupes.append("duplicate key %r (line %d) — safe_load silently keeps only "
                                     "the last one" % (k.value, k.start_mark.line + 1))
                    seen.add(k.value)
                stack.append(k)
                stack.append(v)
        elif isinstance(node, yaml_mod.SequenceNode):
            stack.extend(node.value)
    return dupes


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)
    if data.get("tool_name") not in ("Edit", "Write", "MultiEdit"):
        sys.exit(0)
    path = ((data.get("tool_input") or {}).get("file_path")
            or (data.get("tool_input") or {}).get("path") or "")
    if not path:
        sys.exit(0)
    norm = path.replace("\\", "/")
    base = os.path.basename(norm)
    if "project_memory" not in norm.split("/") or not base.endswith((".yaml", ".yml")):
        sys.exit(0)
    if not os.path.isfile(path):
        sys.exit(0)

    try:
        import yaml  # type: ignore[import-untyped]
    except ImportError:
        sys.exit(0)  # no parser available here; the pipeline yaml-lint still catches it in CI

    try:
        with open(path, encoding="utf-8", errors="ignore") as fh:
            text = fh.read()
    except Exception:
        sys.exit(0)

    try:
        yaml.safe_load(text)
    except yaml.YAMLError as e:
        block(base, str(e))
    except Exception:
        sys.exit(0)  # internal edge case — never block on our own bug

    dupes = find_duplicate_keys(yaml, text)
    if dupes:
        block(base, "\n".join(dupes))
    sys.exit(0)


if __name__ == "__main__":
    main()
