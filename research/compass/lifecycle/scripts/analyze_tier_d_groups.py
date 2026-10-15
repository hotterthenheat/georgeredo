"""Run analyze_tier_d.py once per group (index ETFs; single names), each with its own bootstrap, and concatenate the
tables into results/tier_d/. One shared bootstrap over every root's days let a group's extra days (FB traded on 4 days
the index ETFs' rows do not hold) shift the day weights of every other group and move borderline intervals; per group,
adding names never changes the index ETFs' results.
Usage: analyze_tier_d_groups.py SPY,QQQ,IWM FB[,AAPL,...]"""
import os, sys, json, glob, subprocess, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import polars as pl
from lc import paths

OUT = f'{paths.RESULTS}/tier_d'
groups = [g for g in sys.argv[1:] if g]
here = os.path.dirname(os.path.abspath(__file__))
with tempfile.TemporaryDirectory() as tmp:
    dirs = []
    for i, roots in enumerate(groups):
        d = f'{tmp}/g{i}'; os.makedirs(d)
        subprocess.run([sys.executable, f'{here}/analyze_tier_d.py', roots], check=True, env={**os.environ, 'TIERD_OUT': d})
        dirs.append(d)
    names = sorted({os.path.basename(f) for d in dirs for f in glob.glob(f'{d}/*.csv')})
    for n in names:
        parts = [pl.read_csv(f'{d}/{n}', infer_schema_length=None) for d in dirs if os.path.exists(f'{d}/{n}')]
        pl.concat(parts, how='diagonal_relaxed').write_csv(f'{OUT}/{n}')
    counts = [json.load(open(f'{d}/counts.json')) for d in dirs]
    json.dump({'groups': [c['roots'] for c in counts], 'daily_rows': sum(c['daily_rows'] for c in counts),
               'cells': sum(c['cells'] for c in counts), 'configurations': sum(c['configurations'] for c in counts),
               'bootstrap': 'one per group'}, open(f'{OUT}/counts.json', 'w'), indent=1)
print('written', OUT, names)
