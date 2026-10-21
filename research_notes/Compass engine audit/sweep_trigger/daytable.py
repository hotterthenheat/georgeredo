"""Build the per-session table (open, high, low, close, prior day's high/low, prior week's high/low, ATR14, volume by
minute) for SPY, QQQ and IWM from their one-minute bars, 2012-06-01 on. Output: out/days_<SYM>.parquet.
  nice -n 10 env POLARS_MAX_THREADS=1 OMP_NUM_THREADS=1 python3 -I daytable.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sweeplib as S

if __name__ == '__main__':
    for u in (sys.argv[1].split(',') if len(sys.argv) > 1 else ['SPY', 'QQQ', 'IWM']):
        T = S.build_day_table(u)
        print(u, T.height, 'sessions', T['session'].min(), '->', T['session'].max(), 'half days', int(T['half'].sum()), flush=True)
