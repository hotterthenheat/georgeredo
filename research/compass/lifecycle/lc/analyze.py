"""Statistics over the lifecycle runs (lifecycle protocol §6-§8): cell tables, day-clustered bootstrap, paired tests,
walk-forward selection. Every function excludes the hold-out unless asked (`holdout=True`), and clusters days across
roots (one New York date is one cluster: SPY, QQQ and SPX move together).

Daily aggregates (WORK/runs/grid/<root>/daily.parquet) give n, wins, sums of P&L, wins, losses, cost and capital per
(session, setup, structure, policy, real/control). Expectancy is the ratio estimator sum(pnl)/sum(n); the bootstrap draws
days with Poisson(1) weights shared by every cell, so cells and policies are compared on the same resamples (paired)."""
from __future__ import annotations
import datetime as dt, json, os
import numpy as np
import polars as pl
from . import paths, policies as pol, runner

DEV_END = dt.date(2024, 12, 31)
VAL_START, VAL_END = dt.date(2025, 1, 2), dt.date(2025, 9, 30)
ROOTS = ('SPY', 'QQQ', 'IWM', 'SPXW')

def split_of(d: dt.date) -> str:
    if d <= DEV_END: return 'dev'
    if d <= VAL_END: return 'val'
    return 'holdout'

def _policy_table(policy_set) -> pl.DataFrame:
    return pl.DataFrame({'policy': pl.Series(list(range(len(policy_set))), dtype=pl.Int16), 'pname': [n for n, _, _ in policy_set],
                         'family': [f for _, f, _ in policy_set]})

def load_daily(stage: str = 'grid', roots=ROOTS, holdout: bool = False, policy_set=None) -> pl.DataFrame:
    fr = []
    for r in roots:
        f = f'{paths.WORK}/runs/{stage}/{r}/daily.parquet'
        if os.path.exists(f):
            x = pl.scan_parquet(f)
            if not holdout: x = x.filter(pl.col('session') < runner.HOLDOUT_START)
            fr.append(x.with_columns(pl.lit(r).alias('root')).collect())
    df = pl.concat(fr)
    return df.join(_policy_table(policy_set or pol.grid()), on='policy', how='left')

OUT_COLS = ['pos_id', 'policy', 'filled', 'pnl', 'fees', 'cost0', 'capital_peak', 'hold_min', 'exit_m', 'final_reason']
POS_COLS = ['pos_id', 'session', 'event_i', 'ctrl', 'setup', 'structure', 'direction', 'm', 'rel_spread', 'mfe_liq', 't_mfe', 'mae_liq', 't_mae', 'mfe_mark', 'd1', 'iv1']

def load_rows(stage: str = 'stage1', roots=ROOTS, holdout: bool = False, policy_set=None) -> pl.DataFrame:
    """Outcome rows joined to their positions, the columns the analysis reads only (all of them ran 11.5 M rows past 12 GB)."""
    fr = []
    ps_ = policy_set or (pol.stage1() if stage == 'stage1' or stage.startswith('entry_') else pol.grid())
    for r in roots:
        d = f'{paths.WORK}/runs/{stage}/{r}'
        if not os.path.exists(f'{d}/outcomes.parquet'): continue
        o = pl.scan_parquet(f'{d}/outcomes.parquet').select(OUT_COLS)
        p = pl.scan_parquet(f'{d}/positions.parquet')
        pc = [c for c in POS_COLS if c in p.collect_schema().names()]
        p = p.select(pc)
        if not holdout: p = p.filter(pl.col('session') < runner.HOLDOUT_START)
        j = o.join(p, on='pos_id', how='inner').with_columns(pl.lit(r).alias('root')).collect()
        fr.append(j)
    df = pl.concat(fr, how='diagonal_relaxed')
    return df.join(_policy_table(ps_).select(['policy', 'pname']), on='policy', how='left')

class Boot:
    """Poisson(1) day weights shared across every cell: W [B, D]."""
    def __init__(self, days: list[dt.date], B: int = 2000, seed: int = 7):
        self.days = sorted(set(days)); self.ix = {d: i for i, d in enumerate(self.days)}
        self.W = np.random.default_rng(seed).poisson(1.0, size=(B, len(self.days))).astype(np.float32)

    def mat(self, df: pl.DataFrame, keys: list[str], cols: list[str]) -> tuple[pl.DataFrame, dict[str, np.ndarray]]:
        """Pivot day sums into [D, cells] matrices, one per column."""
        cell = df.select(keys).unique().sort(keys).with_row_index('cell')
        j = df.join(cell, on=keys)
        di = np.array([self.ix[d] for d in j['session'].to_list()], dtype=np.int64)
        ci = j['cell'].to_numpy().astype(np.int64)
        out = {}
        for c in cols:
            M = np.zeros((len(self.days), cell.height), np.float32)
            np.add.at(M, (di, ci), j[c].to_numpy().astype(np.float32))
            out[c] = M
        return cell, out

    def ratio_ci(self, num: np.ndarray, den: np.ndarray, alpha: float = 0.05):
        est = num.sum(0) / np.maximum(den.sum(0), 1e-9)
        bn = self.W @ num; bd = self.W @ den
        with np.errstate(invalid='ignore', divide='ignore'): b = bn / bd
        lo = np.nanquantile(b, alpha / 2, axis=0); hi = np.nanquantile(b, 1 - alpha / 2, axis=0)
        return est, lo, hi, b

def cell_table(df: pl.DataFrame, keys: list[str], boot: Boot) -> pl.DataFrame:
    """Per cell: trades, days, win rate, average winner/loser, expectancy with a day-clustered 95 % CI, profit factor,
    return on premium (sum P&L / sum |cost|), return on capital at risk, holding time."""
    g = df.group_by(keys + ['session']).agg([pl.col(c).sum() for c in ('n', 'wins', 'pnl', 'win_pnl', 'loss_pnl', 'cost', 'capital', 'hold', 'fees')])
    cell, M = boot.mat(g, keys, ['n', 'pnl', 'cost', 'capital'])
    est, lo, hi, _ = boot.ratio_ci(M['pnl'], M['n'])
    tot = g.group_by(keys).agg([pl.col(c).sum() for c in ('n', 'wins', 'pnl', 'win_pnl', 'loss_pnl', 'cost', 'capital', 'hold', 'fees')] + [pl.col('session').n_unique().alias('days')])
    t = cell.join(tot, on=keys, how='left').sort('cell')
    t = t.with_columns(pl.Series('exp_lo', lo), pl.Series('exp_hi', hi))
    return t.with_columns([
        (pl.col('pnl') / pl.col('n')).alias('exp'),
        (pl.col('wins') / pl.col('n')).alias('win_rate'),
        (pl.col('win_pnl') / pl.col('wins')).alias('avg_win'),
        (pl.col('loss_pnl') / (pl.col('n') - pl.col('wins'))).alias('avg_loss'),
        (pl.col('win_pnl') / (-pl.col('loss_pnl'))).alias('profit_factor'),
        (pl.col('pnl') / pl.col('cost')).alias('ret_on_premium'),
        (pl.col('pnl') / pl.col('capital')).alias('ret_on_capital'),
        (pl.col('hold') / pl.col('n')).alias('hold_min'),
        (pl.col('fees') / pl.col('n')).alias('fees_per_trade'),
    ]).drop('cell')

def paired(df: pl.DataFrame, keys: list[str], a: dict, b: dict, boot: Boot) -> pl.DataFrame:
    """Expectancy difference between two slices (e.g. policy X minus M0, or real minus control) for every cell of `keys`,
    each side its own ratio estimator, the difference bootstrapped on the shared day weights."""
    def side(sel):
        f = df
        for k, v in sel.items(): f = f.filter(pl.col(k) == v)
        g = f.group_by(keys + ['session']).agg(pl.col('n').sum(), pl.col('pnl').sum())
        return g
    ga, gb = side(a), side(b)
    allc = pl.concat([ga.select(keys), gb.select(keys)]).unique().sort(keys).with_row_index('cell')
    def mats(g):
        j = g.join(allc, on=keys)
        di = np.array([boot.ix[d] for d in j['session'].to_list()], dtype=np.int64); ci = j['cell'].to_numpy().astype(np.int64)
        N = np.zeros((len(boot.days), allc.height), np.float32); P = np.zeros_like(N)
        np.add.at(N, (di, ci), j['n'].to_numpy()); np.add.at(P, (di, ci), j['pnl'].to_numpy())
        return N, P
    Na, Pa = mats(ga); Nb, Pb = mats(gb)
    ea = Pa.sum(0) / np.maximum(Na.sum(0), 1e-9); eb = Pb.sum(0) / np.maximum(Nb.sum(0), 1e-9)
    with np.errstate(invalid='ignore', divide='ignore'):
        da = (boot.W @ Pa) / (boot.W @ Na); db = (boot.W @ Pb) / (boot.W @ Nb)
    d = da - db
    return allc.with_columns(pl.Series('exp_a', ea), pl.Series('exp_b', eb), pl.Series('diff', ea - eb),
                             pl.Series('diff_lo', np.nanquantile(d, 0.025, axis=0)), pl.Series('diff_hi', np.nanquantile(d, 0.975, axis=0)),
                             pl.Series('n_a', Na.sum(0)), pl.Series('n_b', Nb.sum(0))).drop('cell')

def quarter(d: dt.date) -> str:
    return f'{d.year}Q{(d.month - 1) // 3 + 1}'

def walk_forward(df: pl.DataFrame, cell_keys: list[str], choice_key: str = 'pname', start: dt.date = dt.date(2024, 1, 1),
                 end: dt.date = VAL_END, min_trades: int = 150, embargo_sessions: int = 5, B: int = 500, seed: int = 11) -> tuple[pl.DataFrame, pl.DataFrame]:
    """Each calendar quarter from `start`: for every cell, pick the `choice_key` value (a policy) with the highest
    day-clustered 95 % lower bound of expectancy on all data before the quarter (minus an embargo), among those with at
    least `min_trades`; apply it to the quarter. Returns (choices, stitched out-of-sample day sums)."""
    df = df.with_columns((pl.col('session').dt.year().cast(pl.Utf8) + pl.lit('Q') + ((pl.col('session').dt.month() - 1) // 3 + 1).cast(pl.Utf8)).alias('q'))
    qs = sorted({quarter(d) for d in df['session'].unique().to_list() if start <= d <= end})
    sessions = sorted(df['session'].unique().to_list())
    choices, oos = [], []
    for q in qs:
        q_days = [d for d in sessions if quarter(d) == q]
        first = q_days[0]; cut = sessions[max(0, sessions.index(first) - embargo_sessions)]
        tr = df.filter(pl.col('session') < cut)
        if tr.height == 0: continue
        boot = Boot(tr['session'].to_list(), B=B, seed=seed)
        t = cell_table(tr, cell_keys + [choice_key], boot).filter(pl.col('n') >= min_trades)
        best = t.sort('exp_lo', descending=True).group_by(cell_keys, maintain_order=True).first()
        for r in best.iter_rows(named=True):
            choices.append({**{k: r[k] for k in cell_keys}, 'quarter': q, choice_key: r[choice_key], 'train_exp': r['exp'], 'train_lo': r['exp_lo'], 'train_n': r['n']})
        if best.height:
            te = df.filter(pl.col('q') == q).join(best.select(cell_keys + [choice_key]), on=cell_keys + [choice_key], how='inner')
            oos.append(te.group_by(cell_keys + ['session']).agg([pl.col(c).sum() for c in ('n', 'wins', 'pnl', 'win_pnl', 'loss_pnl', 'cost', 'capital', 'hold', 'fees')]).with_columns(pl.lit(q).alias('quarter')))
    return pl.DataFrame(choices), (pl.concat(oos) if oos else pl.DataFrame())
