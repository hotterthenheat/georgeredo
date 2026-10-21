#!/usr/bin/env python3
"""check_helix_isolation.py — Compass core spec v2, module 16.2: telemetry is never read by a decision.

Usage:
    python3 check_helix_isolation.py <code_root> --decision GLOB [--decision GLOB ...]
                                     [--telemetry GLOB_OR_NAME ...] [--field REGEX ...] [--ext ...] [--json]

What it proves
  (b) the import graph: starting from every DECISION file (--decision globs, relative to the root: the gate's
      booleans, the picker, the stops, the scale-outs, the sizing, the governor) it walks every import edge over
      .ts / .tsx / .js / .mjs / .py files and reports any path that reaches a TELEMETRY module (--telemetry: a glob
      or a basename such as "helix", matched against the path without its extension, case-insensitive). The chain
      is printed so the owner sees which hop lets the telemetry in.
  (a)+(d) by a read-site grep: every occurrence of a telemetry FIELD (--field regexes; default: helix, physics,
      nerve, charm_pressure, moc_score, gex_regime / regime sign, the module-11 flow fields) inside a decision file
      is listed — a decision function with a telemetry argument shows up here.
  (c) is a replay test the owner runs on the engine (decisions identical with the telemetry fields null); the
      check prints the instruction and cannot run it on a static tree.

Import resolution
  Relative specifiers ('./x', '../y/z') are resolved against the importing file with the usual extensions and
  index files; bare specifiers (packages) are ignored; TypeScript path aliases are not resolved (a note is printed
  when any appear, so the owner can add their mapping with --alias PREFIX=DIR). Python: 'import a.b' and
  'from a.b import c' resolve against the root and the file's own directory.

Exit code: 1 when a decision file reaches a telemetry module or reads a telemetry field, else 0.
Standard library only.
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import sys
from collections import deque

SKIP_DIRS = {"node_modules", ".git", "dist", "build", "out", "__pycache__", ".feed-cache", "graphify-out"}
JS_EXTS = (".ts", ".tsx", ".js", ".mjs", ".jsx")
PY_EXTS = (".py",)
JS_IMPORT = re.compile(r"""(?:^|[^\w])(?:import|export)\s+(?:[\w*{}\s,$]+?\s+from\s+)?['"]([^'"]+)['"]|"""
                       r"""\brequire\(\s*['"]([^'"]+)['"]\s*\)|\bimport\(\s*['"]([^'"]+)['"]\s*\)""", re.M)
PY_IMPORT = re.compile(r"^\s*(?:from\s+([\w.]+)\s+import\b|import\s+([\w.]+(?:\s*,\s*[\w.]+)*))", re.M)
DEFAULT_FIELDS = [r"\bhelix\w*", r"\bphysics\w*", r"\bnerve\w*", r"\bcharm_?pressure\b", r"\bmoc_?score\b",
                  r"\bgex_?regime\b|\bregime_?sign\b", r"\bsweep_?premium_?balance\b|\bpremium_?balance\b",
                  r"\bwhale_?(flag|filter)\b", r"\brvol_?rotation\b", r"\bdark_?pool_?signature\b"]
COMMENT = re.compile(r"^\s*(//|#|\*|/\*|\{/\*)")


def walk(root, exts):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for f in filenames:
            if f.endswith(exts):
                yield os.path.join(dirpath, f)


def resolve_js(spec, from_file, root, aliases):
    for prefix, d in aliases.items():
        if spec.startswith(prefix):
            spec = os.path.join(d, spec[len(prefix):]); break
    else:
        if not spec.startswith("."):
            return None, False  # a package
    base = os.path.normpath(os.path.join(os.path.dirname(from_file), spec)) if spec.startswith(".") \
        else os.path.normpath(os.path.join(root, spec))
    cands = [base] + [base + e for e in JS_EXTS] + [os.path.join(base, "index" + e) for e in JS_EXTS]
    if base.endswith((".js", ".jsx")):  # TS projects import './x.js' meaning './x.ts'
        stem = base.rsplit(".", 1)[0]
        cands += [stem + e for e in JS_EXTS]
    for c in cands:
        if os.path.isfile(c):
            return c, True
    return None, True


def resolve_py(mod, from_file, root):
    parts = mod.strip().split(".")
    for basedir in (os.path.dirname(from_file), root):
        p = os.path.join(basedir, *parts)
        for c in (p + ".py", os.path.join(p, "__init__.py")):
            if os.path.isfile(c):
                return c
    return None


def edges_of(path, root, aliases, unresolved, alias_like):
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            src = fh.read()
    except OSError:
        return []
    out = []
    if path.endswith(JS_EXTS):
        for m in JS_IMPORT.finditer(src):
            spec = next(g for g in m.groups() if g)
            target, local = resolve_js(spec, path, root, aliases)
            if target:
                out.append(target)
            elif local:
                unresolved.append((os.path.relpath(path, root), spec))
            elif spec.startswith(("@/", "~/", "src/")):
                alias_like.add(spec.split("/")[0] + "/")
    else:
        for m in PY_IMPORT.finditer(src):
            mods = [m.group(1)] if m.group(1) else [x.strip() for x in m.group(2).split(",")]
            for mod in mods:
                t = resolve_py(mod, path, root)
                if t:
                    out.append(t)
    return out


def is_telemetry(path, root, pats):
    rel = os.path.relpath(path, root)
    stem = rel.rsplit(".", 1)[0]
    base = os.path.basename(stem)
    for p in pats:
        if fnmatch.fnmatch(rel, p) or fnmatch.fnmatch(stem, p) or fnmatch.fnmatch(base, p) \
                or fnmatch.fnmatch(rel.lower(), p.lower()) or fnmatch.fnmatch(base.lower(), p.lower()) \
                or p.lower() == base.lower():
            return True
    return False


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("root")
    ap.add_argument("--decision", action="append", required=True,
                    help="glob (relative to root) of decision files; repeatable, e.g. 'engine/decide/**/*.ts'")
    ap.add_argument("--telemetry", action="append", default=["helix", "*helix*", "*physics*", "*nerve*"],
                    help="telemetry module glob or basename; repeatable (defaults cover Helix/Physics/Nerve)")
    ap.add_argument("--field", action="append", default=[], help="a telemetry field regex; added to the defaults")
    ap.add_argument("--no-default-fields", action="store_true")
    ap.add_argument("--alias", action="append", default=[], help="PREFIX=DIR for a TS path alias, e.g. '@/=src'")
    ap.add_argument("--ext", default=".ts,.tsx,.js,.mjs,.jsx,.py")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)

    root = os.path.abspath(a.root)
    exts = tuple(e.strip() for e in a.ext.split(",") if e.strip())
    aliases = {}
    for s in a.alias:
        if "=" in s:
            k, d = s.split("=", 1); aliases[k] = os.path.join(root, d)
    fields = ([] if a.no_default_fields else list(DEFAULT_FIELDS)) + a.field
    field_rx = [re.compile(f, re.I) for f in fields]

    files = list(walk(root, exts))
    rel = {f: os.path.relpath(f, root) for f in files}
    decision = [f for f in files if any(fnmatch.fnmatch(rel[f], g) for g in a.decision)]
    telemetry = [f for f in files if is_telemetry(f, root, a.telemetry)]

    # the import graph, built lazily from the decision files outward
    unresolved, alias_like, graph = [], set(), {}
    violations, seen_chain = [], {}
    for d in decision:
        q = deque([(d, [d])]); seen = {d}
        while q:
            cur, chain = q.popleft()
            if cur not in graph:
                graph[cur] = edges_of(cur, root, aliases, unresolved, alias_like)
            for nxt in graph[cur]:
                if is_telemetry(nxt, root, a.telemetry):
                    key = (d, nxt)
                    if key not in seen_chain:            # one chain (the first found, the shortest) per pair
                        seen_chain[key] = True
                        violations.append({"decision": rel[d], "telemetry": os.path.relpath(nxt, root),
                                           "chain": [os.path.relpath(x, root) for x in chain + [nxt]]})
                if nxt not in seen:
                    seen.add(nxt); q.append((nxt, chain + [nxt]))

    # read sites of telemetry fields inside decision files
    reads = []
    for d in decision:
        try:
            with open(d, encoding="utf-8", errors="replace") as fh:
                for n, line in enumerate(fh, 1):
                    for rx in field_rx:
                        m = rx.search(line)
                        if m:
                            reads.append({"file": rel[d], "line": n, "field": m.group(0),
                                          "comment": bool(COMMENT.match(line)), "text": line.rstrip()[:200]})
                            break
        except OSError:
            pass
    read_findings = [r for r in reads if not r["comment"]]
    status = 1 if (violations or read_findings) else 0
    out = {"root": root, "decision_files": len(decision), "telemetry_modules": [os.path.relpath(t, root) for t in telemetry],
           "import_violations": violations, "field_reads": reads, "unresolved_relative_imports": unresolved[:50],
           "alias_specifiers_seen": sorted(alias_like), "fields": fields, "status": status,
           "replay_test": "(c) run the engine on one fixed replay day twice — once as is, once with every telemetry "
                          "field set to null — and diff the decisions byte for byte; they must be identical."}
    if a.json:
        print(json.dumps(out, indent=1)); return status
    print(f"check_helix_isolation: {root}")
    print(f"  decision files: {len(decision)} (globs {a.decision})")
    print(f"  telemetry modules present: {len(telemetry)}" + (f" — {', '.join(out['telemetry_modules'][:12])}" if telemetry else " (none match: the telemetry is absent from this root, so (b) holds trivially)"))
    print(f"  (b) import paths from a decision file to a telemetry module: {len(violations)}")
    for v in violations[:40]:
        print("    " + "  ->  ".join(v["chain"]))
    print(f"  (a)/(d) telemetry fields read inside decision files: {len(read_findings)}"
          + (f" (+{len(reads) - len(read_findings)} in comments)" if len(reads) != len(read_findings) else ""))
    for r in read_findings[:40]:
        print(f"    {r['file']}:{r['line']}: [{r['field']}] {r['text'].strip()}")
    if unresolved:
        print(f"  note: {len(unresolved)} relative import(s) could not be resolved (first: {unresolved[0]})")
    if alias_like:
        print(f"  note: alias-style specifiers seen ({', '.join(sorted(alias_like))}); pass --alias PREFIX=DIR to follow them")
    print(f"  {out['replay_test']}")
    print(f"  result: {'FAIL' if status else 'PASS'}")
    return status


if __name__ == "__main__":
    sys.exit(main())
