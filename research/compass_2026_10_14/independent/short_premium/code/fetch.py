"""Paced ThetaData fetcher for the short-premium study (shared Terminal at 127.0.0.1:25503; no key handled here).
One request per root per expiry: the 5-min NBBO for that expiry over [previous session, expiry day] (0DTE + 1DTE entries).
Raw CSVs are gzipped under raw/ (git-ignored) and indexed with SHA-256 in results/raw_index.jsonl.
Retries on 'Invalid session' / 571 / timeouts with backoff; never starts or restarts a Terminal."""
import csv, gzip, hashlib, json, os, sys, time, urllib.request, urllib.parse
from concurrent.futures import ThreadPoolExecutor
B = "http://127.0.0.1:25503/v3"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "raw"); os.makedirs(RAW, exist_ok=True)
START, END = "2025-01-02", "2026-10-09"
SRANGE = {"SPY": 12, "QQQ": 12, "IWM": 10, "SPXW": 24, "XSP": 12}
CONC = int(os.environ.get("CONC", "2"))

def get(path, params, timeout=180):
    url = f"{B}/{path}?" + urllib.parse.urlencode(params, safe="*")
    for attempt in range(8):
        try:
            with urllib.request.urlopen(url, timeout=timeout) as r:
                body = r.read().decode()
        except urllib.error.HTTPError as e:
            body = e.read().decode(errors="replace")
            if e.code == 472 or "NO_DATA" in body or "No data" in body: return ""
        except Exception as e:
            body = f"EXC {e}"
        if body.startswith(("symbol", "timestamp", "created")): return body
        if "No data" in body: return ""
        time.sleep(min(120, 10 * 2 ** attempt))
    raise RuntimeError(f"failed {url}: {body[:120]}")

def expiries(sym):
    t = get("option/list/expirations", {"symbol": sym})
    return sorted(r["expiration"] for r in csv.DictReader(t.splitlines()) if START <= r["expiration"] <= END)

def save(name, text, meta):
    p = os.path.join(RAW, name + ".csv.gz")
    data = text.encode()
    with open(p, "wb") as fh, gzip.GzipFile(fileobj=fh, mode="wb", mtime=0) as f: f.write(data)
    meta.update(file=name + ".csv.gz", sha256=hashlib.sha256(data).hexdigest(), bytes=len(data))
    with open(os.path.join(ROOT, "results", "raw_index.jsonl"), "a") as f: f.write(json.dumps(meta, sort_keys=True) + "\n")

def main():
    # trading sessions = SPY daily expirations in window (SPY lists every session in 2025-26); checked against SPY OHLC later
    sessions = expiries("SPY")
    prev = {d: sessions[i - 1] for i, d in enumerate(sessions) if i}
    jobs = []
    for sym in SRANGE:
        exps = set(expiries(sym)); time.sleep(1)
        for d in sessions:
            if d in exps and d in prev: jobs.append((d, sym))
    jobs.sort()  # by date, interleaving roots
    with open(os.path.join(ROOT, "results", "contract_days.csv"), "w") as f:
        f.write("expiry,prev_session,root\n" + "".join(f"{d},{prev[d]},{s}\n" for d, s in jobs))
    print(len(sessions), "sessions", len(jobs), "root-expiries", flush=True)
    def one(job):
        d, sym = job; name = f"q_{sym}_{d}"
        if os.path.exists(os.path.join(RAW, name + ".csv.gz")): return
        t = get("option/history/quote", {"symbol": sym, "expiration": d.replace("-", ""), "start_date": prev[d].replace("-", ""),
                "end_date": d.replace("-", ""), "strike": "*", "right": "both", "interval": "5m", "strike_range": SRANGE[sym]})
        save(name, t, {"kind": "option_quote_5m", "root": sym, "expiry": d, "start": prev[d]})
    # underlying: SPX 1-min per expiry day (fast), ETF 1-min OHLC per month
    for d in sessions:
        name = f"spx_{d}"
        if not os.path.exists(os.path.join(RAW, name + ".csv.gz")):
            save(name, get("index/history/price", {"symbol": "SPX", "date": d.replace("-", ""), "interval": "1m"}), {"kind": "spx_1m", "date": d})
    months = sorted({d[:7] for d in sessions})
    for sym in ("SPY", "QQQ", "IWM"):
        for m in months:
            name = f"ohlc_{sym}_{m}"
            if os.path.exists(os.path.join(RAW, name + ".csv.gz")): continue
            ds = [d for d in sessions if d.startswith(m)]
            save(name, get("stock/history/ohlc", {"symbol": sym, "start_date": ds[0].replace("-", ""), "end_date": ds[-1].replace("-", ""), "interval": "1m"}),
                 {"kind": "ohlc_1m", "root": sym, "month": m})
    print("underlyings done", flush=True)
    done = 0
    with ThreadPoolExecutor(CONC) as ex:
        for _ in ex.map(one, jobs):
            done += 1
            if done % 50 == 0: print(time.strftime("%H:%M:%S"), done, "/", len(jobs), flush=True)
    print("ALL DONE", flush=True)

if __name__ == "__main__": main()
