#!/usr/bin/env python3
"""check_dead_code.py — Compass core spec v2, module 16.1: the dead-code quarantine.

Usage:
    python3 check_dead_code.py <code_root> [--names NAME,NAME,... | --names-file FILE] [--value NAME=LITERAL ...]
                               [--no-patterns] [--ext .ts,.tsx,.py,...] [--json]

What it does
  1. Proves, by a word-boundary grep over every source file under <code_root>, that none of the removed constants
     resolves anywhere: SWEEP_FLOOR, BONUS_CAP, CONFIDENCE_CAP by default (spec 2.3), plus every name in --names /
     --names-file. A hit in a comment is reported apart (a comment does not resolve, but the audit asks that the
     names be gone).
  2. Greps for each removed constant's LITERAL value where the owner gives one (--value SWEEP_FLOOR=0.35): a value
     re-typed inline is the quarantine's usual leak.
  3. Looks for the CLASSES of constant the audit named without naming them (spec 16.1): premium caps/floors on a
     contract's price, delta floors/ceilings the 0.35-0.50 / 0.40-0.55 / 0.60-0.80 bands replace, an old OI floor,
     min/max-DTE constants the 4-7 / 8-28 / 90-365+ windows replace, and any weight / score / confluence / grade
     constant. These are "names to review", not findings: a hit is a name the owner must either list in --names
     (removed) or keep knowingly. --no-patterns switches this off.
  4. Where a tsconfig.json exists under <code_root> or one directory above it, prints the tsc command for the
     static half of the proof (delete the exports, then `tsc --noEmit` must pass) — the check cannot run tsc for
     you without touching the code, and it never edits anything.

Exit code: 1 when a removed name (or a given literal) resolves outside comments, else 0.
Standard library only.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

DEFAULT_NAMES = ["SWEEP_FLOOR", "BONUS_CAP", "CONFIDENCE_CAP"]
CLASS_PATTERNS = {
    "premium cap/floor":    r"\b[A-Z0-9_]*(PREMIUM|PREM|PRICE)_(CAP|FLOOR|MIN|MAX)\b|\b(MIN|MAX)_(PREMIUM|PREM|PRICE)\b",
    "delta floor/ceiling":  r"\bDELTA_(FLOOR|CEIL|CEILING|MIN|MAX|LO|HI)\b|\b(MIN|MAX)_DELTA\b",
    "OI floor":             r"\bOI_(FLOOR|MIN)\b|\bMIN_OI\b|\bOPEN_INTEREST_(FLOOR|MIN)\b",
    "min/max DTE":          r"\b(MIN|MAX)_DTE\b|\bDTE_(MIN|MAX|FLOOR|CAP)\b",
    "weight/score/grade":   r"\b[A-Z0-9_]*(WEIGHT|SCORE|CONFLUENCE|GRADE)(_[A-Z0-9_]+)?\b",
}
COMMENT = re.compile(r"^\s*(//|#|\*|/\*|\{/\*)")
SKIP_DIRS = {"node_modules", ".git", "dist", "build", "out", "__pycache__", ".feed-cache", "graphify-out"}


def walk(root, exts):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for f in filenames:
            if f.endswith(exts):
                yield os.path.join(dirpath, f)


def grep(root, exts, regexes):
    """regexes: {label: compiled}. Returns {label: [hit, ...]}."""
    hits = {k: [] for k in regexes}
    for path in walk(root, exts):
        rel = os.path.relpath(path, root)
        try:
            with open(path, encoding="utf-8", errors="replace") as fh:
                lines = fh.readlines()
        except OSError:
            continue
        for n, line in enumerate(lines, 1):
            for label, rx in regexes.items():
                m = rx.search(line)
                if m:
                    hits[label].append({"file": rel, "line": n, "comment": bool(COMMENT.match(line)),
                                        "match": m.group(0), "text": line.rstrip()[:200]})
    return hits


def find_tsconfig(root):
    for d in (root, os.path.dirname(root)):
        p = os.path.join(d, "tsconfig.json")
        if os.path.isfile(p):
            return p
    return None


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("root")
    ap.add_argument("--names", default="", help="comma list of removed constant names (added to the three defaults)")
    ap.add_argument("--names-file", help="a file with one removed name a line (# comments allowed)")
    ap.add_argument("--value", action="append", default=[], help="NAME=LITERAL — also grep the literal value")
    ap.add_argument("--no-patterns", action="store_true", help="skip the class patterns (names to review)")
    ap.add_argument("--ext", default=".ts,.tsx,.js,.mjs,.py")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)

    root = os.path.abspath(a.root)
    exts = tuple(e.strip() for e in a.ext.split(",") if e.strip())
    names = list(DEFAULT_NAMES)
    names += [n.strip() for n in a.names.split(",") if n.strip()]
    if a.names_file:
        with open(a.names_file, encoding="utf-8") as fh:
            names += [ln.strip() for ln in fh if ln.strip() and not ln.lstrip().startswith("#")]
    names = list(dict.fromkeys(names))
    values = {}
    for v in a.value:
        if "=" in v:
            k, lit = v.split("=", 1)
            values[k.strip()] = lit.strip()

    rx = {f"name:{n}": re.compile(r"\b" + re.escape(n) + r"\b") for n in names}
    for k, lit in values.items():
        rx[f"value:{k}={lit}"] = re.compile(r"(?<![\w.])" + re.escape(lit) + r"(?![\w])")
    if not a.no_patterns:
        for label, pat in CLASS_PATTERNS.items():
            rx[f"class:{label}"] = re.compile(pat)
    hits = grep(root, exts, rx)

    findings = {k: [h for h in v if not h["comment"]] for k, v in hits.items() if k.startswith(("name:", "value:"))}
    in_comments = {k: [h for h in v if h["comment"]] for k, v in hits.items() if k.startswith(("name:", "value:"))}
    review = {k: v for k, v in hits.items() if k.startswith("class:")}
    status = 1 if any(findings.values()) else 0
    tsconfig = find_tsconfig(root)
    tsc_note = (f"static half: delete the exports of {', '.join(names)} and run  npx tsc -p {tsconfig} --noEmit  "
                f"(the project's typecheck); it must pass with nothing else changed. Then replay a fixed day and diff "
                f"the engine's output byte for byte: only a removed cap that used to bind may differ, each listed."
                if tsconfig else "no tsconfig.json found under the root or above it: a Python root takes a grep plus "
                                 "the fixed-day replay diff; no tsc step applies.")
    out = {"root": root, "names": names, "values": values, "findings": findings, "in_comments": in_comments,
           "names_to_review": review, "tsconfig": tsconfig, "tsc": tsc_note, "status": status}
    if a.json:
        print(json.dumps(out, indent=1))
        return status
    print(f"check_dead_code: {root}")
    print(f"  removed names checked: {', '.join(names)}")
    if values:
        print(f"  literal values checked: {values}")
    print(f"  RESOLVES (a finding): {sum(len(v) for v in findings.values())}")
    for k, v in findings.items():
        for h in v:
            print(f"    {k}  {h['file']}:{h['line']}: {h['text'].strip()}")
    nc = sum(len(v) for v in in_comments.values())
    if nc:
        print(f"  in comments only (not resolving; the audit asks the names be gone): {nc}")
        for k, v in in_comments.items():
            for h in v:
                print(f"    {k}  {h['file']}:{h['line']}: {h['text'].strip()}")
    if review:
        print("  names to review (the audit's classes; list a removed one in --names, keep the rest knowingly):")
        for k, v in review.items():
            seen = sorted({h["match"] for h in v})
            print(f"    {k}: {len(v)} hit(s) in {len({h['file'] for h in v})} file(s)"
                  + (f" — {', '.join(seen[:12])}{' ...' if len(seen) > 12 else ''}" if seen else ""))
    print(f"  {tsc_note}")
    print(f"  result: {'FAIL — a removed name resolves' if status else 'PASS — no removed name resolves'}")
    return status


if __name__ == "__main__":
    sys.exit(main())
