#!/usr/bin/env python3
"""check_cents.py — Compass core spec v2, module 15: one price unit at the vendor boundary.

Usage:
    python3 check_cents.py <code_root> [--boundary GLOB ...] [--allow FILE] [--ext .ts,.tsx,.py,...] [--selftest] [--json]

What it does
  1. Walks <code_root> and finds every line that converts a unit: /100, *100, /1000, *1000, Math.round(x*100),
     and the words "cents" / "mils". Each hit is classed by the words on its line:
        price-unit          : the line names a price field (bid, ask, mid, strike, premium, price, spot, stop,
                              target, straddle, open/high/low/close ...) — a finding when the file is outside the boundary
        percent             : a percent / rate / share / bps figure — percent arithmetic, not a price unit
        cent-rounding       : Math.round(x * 100) / 100 — a figure rounded to the cent (a tick), not a unit change
        contract-multiplier : OI, contracts or a premium x 100 shares — the contract's multiplier in exposure or
                              P&L arithmetic (dollars a share -> dollars a contract); read each once: a bot that
                              stores mils would hide a unit change under the same shape
        lot-rounding        : a size rounded to a round lot
        vol-points          : an implied vol between a decimal and vol points
        cents-keyed-map     : an integer-cents key for a map (dollars in, dollars out)
        time-ms             : epoch milliseconds <-> seconds — the x1000 / /1000 feeds a clock function (the ny* and
                              viewer* of core/nyTime.ts, readerClock, sessionSpan, new Date, Date.) or a `time:`
                              field, or its operand is a span's / bar's instant (span.close, s.open, x.time, ms, at,
                              stamp, now, ...Ms / ...At / ...End); a bare `t` or `m` is not enough on its own
        greek-per-point     : rho or vega over 100 — a greek per 1% of rate or per vol point, not a price
        svg-width           : a `width={... / 100}` — an SVG bar's length out of a 0–100 figure
        thousands-label     : `/ 1000}K` — a dollar floor printed in thousands
        allowed             : a line the --allow file names, with its reason (reviewed by hand; listed, not a finding)
        comment             : the hit sits in a comment
        other               : none of the above — listed for a human to read
     A continuation line (one that opens with "(", ")", ".", an operator or a ternary's "?" / ":") is read with the
     line before it, so `const rho = Number(` on one line names the figure on the next.
     --boundary names the module(s) allowed to convert (the vendor boundary of spec 15.1); a hit inside them is
     reported as "boundary" and is not a finding.
     --allow FILE is a JSON list of {"path", "line-pattern", "reason"}: a hit the text alone cannot settle, reviewed by
     a human and passed with its reason. An entry is narrow (one path, a regex on the line) and only ever turns a
     price-unit hit into "allowed"; an entry that matches no price-unit hit is STALE and fails the run, so the
     list never outlives the code it describes. The rules are never loosened to make a finding go away: a hit either
     is classed by what its text says, or it is listed here with a reason, or it stands.
  2. --selftest runs the round-trip harness on the one known contract the audit names:
        SPY 20261030 808 C, bid 0.55 / ask 0.56 on 2026-10-09 (ThetaData bulk file)
     through a reference engine (the spec's own numbers), checking every figure to the cent, and shows the
     float32 case behind spec 0.1 (1.05 stored as float32 reads back 1.0499999523; round(x, 4) restores it).

Plugging a target engine in
  Implement an object with these methods and pass it to run_round_trip(engine):
      load_price(x) -> float                       # spec 0.1
      pick(chain, spot, side) -> contract | None   # spec 2.4; chain = list of dicts with strike, right, bid, ask
      backstop(entry_ask) -> float                 # spec 3.1: 0.68 * entry_ask
      t1(entry_ask) -> float                       # spec 3.5: 1.25 * entry_ask
      lock_level(entry_ask) -> float               # spec 3.3: entry_ask
      trail_level(peak_prior) -> float             # spec 3.4: 0.90 * peak_prior
      pnl(entry_ask, exit_px, contracts, sold=True) -> float   # dollars, fees $0.65 a contract each way
  Every method takes and returns DOLLARS (a premium is dollars a share; the contract is x100 in pnl only).

Exit code: 0 when no price-unit hit stands outside the boundary, no --allow entry is stale (and the selftest passes),
1 otherwise.
Standard library only.
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import math
import os
import re
import struct
import sys

HIT = re.compile(r"(?<![\w.])/\s*100(?:\.0+)?(?![\d.])|(?<![\w.])\*\s*100(?:\.0+)?(?![\d.])|"
                 r"(?<![\w.])/\s*1000(?:\.0+)?(?![\d.])|(?<![\w.])\*\s*1000(?:\.0+)?(?![\d.])|"
                 r"Math\.round\([^()]*\*\s*100\)|\b(?:cents|mils)\b", re.I)
PRICE = re.compile(r"\b(bid|ask|mid|strike|premium|price|spot|stop|target|straddle|move|open|high|low|close|"
                   r"settle|intrinsic|fill|debit|credit|last)\w*\b", re.I)
PERCENT = re.compile(r"(pct|percent|%|\brate\b|share|ratio|bps|basis|quantile|percentile|prob|odds)", re.I)
TIME_MS = re.compile(r"(\bms\b|millis|\btime\b|\bat\b|\bts\b|epoch|Date|sec\b|seconds|barTime|\bt\s*/\s*1000|\bnow\b|stamp)", re.I)
# a x1000 / /1000 whose result is handed to a time function, or sits in a `time:` field, or whose operand is an instant
TIME_FN = re.compile(r"\b(ny[A-Z]\w*|viewer[A-Z]\w*|readerClock|sessionSpan|Date)\s*\(|"  # the terminal's clock module is core/nyTime.ts: ny*, viewer*
                     r"\bnew\s+Date\b|\bDate\.|\btime\s*:\s*[\w.()]+\s*[*/]\s*1000\b")
TIME_OPERAND = re.compile(r"(\b(span|s|m|bar|b)\.(open|close|first|last|time|at|ms|end|start)|\b(ms|at|time|stamp|now)\b)\s*[*/]\s*1000\b|"
                          r"\b[\w.]*\.time\b\s*[*/]\s*1000\b|\b[\w.]*(Ms|_ms|End|Start|At)\s*[*/]\s*1000\b")
THOUSAND = re.compile(r"(?<![\w.])[/*]\s*1000\b")
CENT_ROUND = re.compile(r"(Math\.)?(round|floor|ceil)\(.*\*\s*100\)\s*/\s*100(?![\d])")
LOT_ROUND = re.compile(r"/\s*100\)\s*\*\s*100\b")
RATIO_PCT = re.compile(r"\)\s*/\s*[\w.\[\]]+\)?\s*\*\s*100\b|/\s*[\w.]+\s*\*\s*100\s*(:|<=|>=|<|>|;|,|\))")
# (a / b - 1) * 100 — a change in percent; a score or a move named on its line, x 100 — a 0–100 figure or a move in percent
CHANGE_PCT = re.compile(r"/\s*[\w.\[\]]+\s*-\s*1\)\s*\*\s*100\b|\b\w*(score|Score)\w*\s*[:=][^;]*\*\s*100\b|\b\w*(move|Move)\w*\s*\*\s*100\b")
VOL_POINTS = re.compile(r"\b(iv|vol|implied|im|sigma)\w*[^;]*?/\s*100\b|\b(iv|implied)\w*\s*\*\s*100\b|\b(iv|iv[A-Z]\w*|impliedVol\w*|vol)\s*=[^;]*\*\s*100\b")
GREEK_PER_POINT = re.compile(r"\b(rho|vega)\b[^;]*/\s*100\b", re.I)
SVG_WIDTH = re.compile(r"\b(width|height|x|y|r)=\{[^}]*/\s*100\b")
THOUSANDS_LABEL = re.compile(r"/\s*1000\s*\}\s*K\b")
CONTRACT_MULT = re.compile(r"\b\w*(oi|OI|openInterest|contracts?|qty|size|volume|vol)\w*\s*\*\s*100\b|\*\s*100\s*\*\s*[\w.]*(gamma|delta|vega|vanna|charm|greeks)|"
                           r"\b(mid|ask|bid|price|last|fill|premium|avg|cost|intrinsic|itm|close|spot)\w*(\([^)]*\))?\)?\s*\*\s*100\b|\*\s*100\s*\*\s*\w*n\b|"
                           r"\b(past|intrinsic)\([^)]*\)\s*\*\s*100\b|\*\s*100\s*\*\s*[\w.]*(contracts?|qty|size|lots?)\b", re.I)
CENTS_KEY = re.compile(r"\bcents\s*\(|const cents\b|cents\s*=")
COMMENT = re.compile(r"^\s*(//|#|\*|/\*|\{/\*)")
CONTINUATION = re.compile(r"^\s*([()\].+\-*/?:]|&&|\|\|)")
SKIP_DIRS = {"node_modules", ".git", "dist", "build", "out", "__pycache__", ".feed-cache", "graphify-out"}


def walk(root: str, exts: tuple[str, ...]):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for f in filenames:
            if f.endswith(exts):
                yield os.path.join(dirpath, f)


def classify(line: str, prev: str = "") -> str:
    """The class of one hit. Only 'price-unit' is a finding; the others are listed apart for a human to read.
    `prev` is the line before: a continuation line is read with it (the name of the figure often stands there)."""
    if COMMENT.match(line):
        return "comment"
    text = (prev.rstrip() + " " + line) if (prev and CONTINUATION.match(line) and not COMMENT.match(prev)) else line
    if CENT_ROUND.search(line):
        return "cent-rounding"          # x rounded to the cent: a tick, not a unit change
    if LOT_ROUND.search(line):
        return "lot-rounding"           # a size rounded to a round lot
    if THOUSANDS_LABEL.search(line):
        return "thousands-label"        # `$${FLOOR / 1000}K`: a dollar floor printed in thousands
    if SVG_WIDTH.search(line):
        return "svg-width"              # an SVG bar's length out of a 0–100 figure
    if THOUSAND.search(line) and (TIME_FN.search(line) or TIME_OPERAND.search(line)) and not re.search(r"strike\b\s*[*/]\s*1000|mils", line, re.I):
        return "time-ms"                # epoch milliseconds <-> seconds: the result feeds a time function, or the operand is an instant
    if (RATIO_PCT.search(line) or CHANGE_PCT.search(line)) and not re.search(r"strike\b\s*[*/]\s*1000|mils", line, re.I):
        return "percent"                # (a - b) / b * 100, (a / b - 1) * 100, a score or a move x 100: percent, not a price unit
    if VOL_POINTS.search(line) and not re.search(r"strike\b.*(/|\*)\s*1000", line, re.I):
        return "vol-points"             # an implied vol between a decimal and vol points
    if GREEK_PER_POINT.search(text):
        return "greek-per-point"        # rho per 1% of rate, vega per vol point: the greek over 100
    if CONTRACT_MULT.search(line):
        return "contract-multiplier"    # OI or contracts x 100 shares, intrinsic x 100: the contract's multiplier, not a unit change
    if CENTS_KEY.search(line):
        return "cents-keyed-map"        # an integer cents key for a map lookup (still dollars in and out)
    if THOUSAND.search(line) and TIME_MS.search(line) and not re.search(r"strike|mils", line, re.I):
        return "time-ms"                # epoch milliseconds <-> seconds
    if PRICE.search(line) and not PERCENT.search(line):
        return "price-unit"
    if PERCENT.search(line):
        return "percent"
    return "other"


def load_allow(path: str | None) -> list[dict]:
    """The --allow file: a list of {"path", "line-pattern", "reason"}; every field required, the pattern a regex."""
    if not path:
        return []
    with open(path, encoding="utf-8") as fh:
        entries = json.load(fh)
    if not isinstance(entries, list):
        raise SystemExit(f"--allow {path}: expected a JSON list")
    out = []
    for i, e in enumerate(entries):
        for k in ("path", "line-pattern", "reason"):
            if not isinstance(e.get(k), str) or not e[k].strip():
                raise SystemExit(f"--allow {path}: entry {i} needs a non-empty string {k!r}")
        out.append({"path": e["path"].replace("\\", "/"), "pattern": re.compile(e["line-pattern"]),
                    "line-pattern": e["line-pattern"], "reason": e["reason"].strip(), "used": 0})
    return out


def scan(root: str, boundary: list[str], exts: tuple[str, ...], allow: list[dict] | None = None):
    hits = []
    allow = allow or []
    for path in walk(root, exts):
        rel = os.path.relpath(path, root).replace("\\", "/")
        in_boundary = any(fnmatch.fnmatch(rel, g) or fnmatch.fnmatch(path, g) for g in boundary)
        try:
            with open(path, encoding="utf-8", errors="replace") as fh:
                prev = ""
                for n, line in enumerate(fh, 1):
                    if HIT.search(line):
                        cls = "boundary" if in_boundary else classify(line, prev)
                        hit = {"file": rel, "line": n, "class": cls, "text": line.rstrip()[:200]}
                        if cls == "price-unit":  # an allow entry only ever turns a finding into "allowed"
                            for e in allow:
                                if e["path"] == rel and e["pattern"].search(line):
                                    hit["class"] = "allowed"; hit["reason"] = e["reason"]; e["used"] += 1
                                    break
                        hits.append(hit)
                    if line.strip():
                        prev = line
        except OSError:
            continue
    return hits


# ----------------------------------------------------------------------------------------------- the harness
KNOWN = {"name": "SPY", "expiry": "20261030", "strike": 808.0, "right": "C", "bid": 0.55, "ask": 0.56,
         "date": "2026-10-09", "source": "ThetaData bulk file"}
FEE = 0.65  # $ a contract each way


class ReferenceEngine:
    """The spec's own arithmetic, in dollars. A target engine replaces this class."""

    def load_price(self, x):                      # spec 0.1
        return round(float(x), 4)

    def pick(self, chain, spot, side):            # spec 2.4: nearest strike at or beyond spot on the side, clean quote
        def ok(c):
            if not (c["ask"] > 0 and c["bid"] > 0 and c["bid"] <= c["ask"]):
                return False
            mid = (c["ask"] + c["bid"]) / 2
            return (c["ask"] - c["bid"]) / mid <= 0.05 + 1e-9
        cands = [c for c in chain if c["right"] == side and ok(c)
                 and ((c["strike"] >= spot) if side == "C" else (c["strike"] <= spot))]
        return min(cands, key=lambda c: abs(c["strike"] - spot)) if cands else None

    def backstop(self, entry_ask):                return 0.68 * entry_ask
    def t1(self, entry_ask):                      return 1.25 * entry_ask
    def lock_level(self, entry_ask):              return entry_ask
    def trail_level(self, peak_prior):            return 0.90 * peak_prior

    def pnl(self, entry_ask, exit_px, contracts=1, sold=True):
        per = (exit_px - entry_ask) * 100 - FEE - (FEE if sold else 0.0)
        return per * contracts


def cents(x: float) -> int:
    """A dollar figure to the cent, half away from zero (the comparison unit of the harness)."""
    return int(math.floor(abs(x) * 100 + 0.5)) * (1 if x >= 0 else -1)


def run_round_trip(engine, verbose=True):
    """Feed the known contract through the engine; every figure is checked to the cent. Returns (ok, rows)."""
    rows, ok = [], True

    def check(label, got, want, unit="$"):
        nonlocal ok
        good = cents(got) == cents(want)
        ok &= good
        rows.append({"check": label, "got": round(got, 4), "want": round(want, 4), "unit": unit, "ok": good})

    bid, ask = engine.load_price(KNOWN["bid"]), engine.load_price(KNOWN["ask"])
    check("load bid (dollars a share)", bid, 0.55)
    check("load ask (dollars a share)", ask, 0.56)
    # a chain with the known contract and a few neighbours (strike in dollars — never 808000 mils)
    chain = [{"strike": 807.0, "right": "C", "bid": 0.98, "ask": 1.00},
             {"strike": 808.0, "right": "C", "bid": bid, "ask": ask},
             {"strike": 809.0, "right": "C", "bid": 0.30, "ask": 0.31},
             {"strike": 808.0, "right": "P", "bid": 0.70, "ask": 0.72}]
    spot = 807.40
    c = engine.pick(chain, spot, "C")
    check("pick: strike (dollars)", c["strike"] if c else float("nan"), 808.0)
    check("pick: ask (dollars a share)", c["ask"] if c else float("nan"), 0.56)
    entry = c["ask"]
    check("entry debit, one contract ($)", entry * 100, 56.00)
    check("backstop 0.68 x ask (dollars a share)", engine.backstop(entry), 0.3808)
    check("T1 1.25 x ask", engine.t1(entry), 0.70)
    check("lock level = ask", engine.lock_level(entry), 0.56)
    check("trail from a 0.80 peak (0.90 x)", engine.trail_level(0.80), 0.72)
    check("P&L: T1 fill at 0.70, 1 contract, fees in ($)", engine.pnl(entry, 0.70, 1), 12.70)
    check("P&L: backstop bid 0.38, 1 contract ($)", engine.pnl(entry, 0.38, 1), -19.30)
    check("P&L: lock exit at the ask 0.56 ($)", engine.pnl(entry, 0.56, 1), -1.30)
    check("P&L: worthless expiry, no sale fee ($)", engine.pnl(entry, 0.0, 1, sold=False), -56.65)
    check("P&L: 3 contracts at T1 ($)", engine.pnl(entry, 0.70, 3), 38.10)
    # spec 0.1 — the float32 case
    f32 = struct.unpack("f", struct.pack("f", 1.05))[0]
    rows.append({"check": "float32 of 1.05 reads back", "got": f32, "want": 1.05, "unit": "raw",
                 "ok": f32 != 1.05})  # the defect: it is 1.0499999523, so 'bid >= 1.05' misses
    check("round(float32(1.05), 4) restores the threshold", engine.load_price(f32), 1.05)
    if verbose:
        for r in rows:
            print(f"  [{'ok ' if r['ok'] else 'BAD'}] {r['check']}: got {r['got']} want {r['want']} ({r['unit']})")
    return ok, rows


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("root", nargs="?", help="the code root to scan (omit with --selftest alone)")
    ap.add_argument("--boundary", action="append", default=[],
                    help="glob (relative to root) of a module allowed to convert units; repeatable")
    ap.add_argument("--ext", default=".ts,.tsx,.js,.mjs,.py", help="comma list of extensions")
    ap.add_argument("--selftest", action="store_true", help="run the round-trip harness on the reference engine")
    ap.add_argument("--json", action="store_true", help="print JSON instead of text")
    ap.add_argument("--list-max", type=int, default=60, help="how many price-unit findings to list in text mode")
    ap.add_argument("--allow", help="JSON list of {path, line-pattern, reason}: reviewed hits the text alone cannot settle")
    a = ap.parse_args(argv)

    out = {"root": a.root, "boundary": a.boundary, "allow": a.allow, "hits": [], "allowed": [], "stale_allow": [], "selftest": None}
    status = 0
    if a.root:
        exts = tuple(e.strip() for e in a.ext.split(",") if e.strip())
        allow = load_allow(a.allow)
        out["hits"] = scan(os.path.abspath(a.root), a.boundary, exts, allow)
        findings = [h for h in out["hits"] if h["class"] == "price-unit"]
        allowed = [h for h in out["hits"] if h["class"] == "allowed"]
        stale = [{"path": e["path"], "line-pattern": e["line-pattern"], "reason": e["reason"]} for e in allow if e["used"] == 0]
        out["allowed"], out["stale_allow"] = allowed, stale
        if findings or stale:
            status = 1
        if not a.json:
            counts = {}
            for h in out["hits"]:
                counts[h["class"]] = counts.get(h["class"], 0) + 1
            print(f"check_cents: {a.root}")
            print(f"  boundary globs: {a.boundary or '(none declared — every price-unit hit is outside)'}")
            print("  hits by class: " + ", ".join(f"{k} {v}" for k, v in sorted(counts.items())) if counts else "  no hits")
            print(f"  FINDINGS (price-unit conversions outside the boundary): {len(findings)}")
            for h in findings[:a.list_max]:
                print(f"    {h['file']}:{h['line']}: {h['text'].strip()}")
            if len(findings) > a.list_max:
                print(f"    ... {len(findings) - a.list_max} more (use --json)")
            if a.allow:
                print(f"  ALLOWED (reviewed by hand in {a.allow}, a reason each; not findings): {len(allowed)}")
                for h in allowed:
                    print(f"    {h['file']}:{h['line']}: {h['text'].strip()[:110]}")
                    print(f"      reason: {h['reason']}")
                print(f"  STALE allow entries (match no price-unit hit — remove them): {len(stale)}")
                for e in stale:
                    print(f"    {e['path']} /{e['line-pattern']}/")
    if a.selftest or not a.root:
        if not a.json:
            print("round trip — " + f"{KNOWN['name']} {KNOWN['expiry']} {KNOWN['strike']:.0f} {KNOWN['right']} at "
                  f"{KNOWN['bid']} / {KNOWN['ask']} on {KNOWN['date']} ({KNOWN['source']}):")
        ok, rows = run_round_trip(ReferenceEngine(), verbose=not a.json)
        out["selftest"] = {"ok": ok, "rows": rows}
        if not ok:
            status = 1
        if not a.json:
            print(f"  round trip: {'PASS' if ok else 'FAIL'}")
    if a.json:
        print(json.dumps(out, indent=1))
    return status


if __name__ == "__main__":
    sys.exit(main())
