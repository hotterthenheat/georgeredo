"""Post-hoc checks run after the train-selected results were seen: the FOMC-or-month-end pair on both scales with CIs and by year,
and FOMC-day afternoon statistics. Not part of the pre-registered selection; flagged as post-hoc in the note. Local files only."""
import os, numpy as np, pandas as pd
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out')
S = pd.read_csv(f'{OUT}/sample.csv'); D = pd.read_csv(f'{OUT}/daily.csv')[['date', 'base20_log_range_pm']]; S = S.merge(D, on='date'); S['train'] = S['train'].astype(bool)
rng = np.random.default_rng(20251013); B = 2000; L = 20
def block_idx(n):
    nb = int(np.ceil(n / L)); st = rng.integers(0, n - L + 1, size=(B, nb)); return (st[:, :, None] + np.arange(L)[None, None, :]).reshape(B, -1)[:, :n]
def ci(a): return np.percentile(a, 2.5), np.percentile(a, 97.5)
S['ratio_alt'] = S['absmove_pm'] / np.exp(S['base20_log_range_pm'])
RS = pd.read_csv(f'{OUT}/rules_single.csv'); k_fair = float(RS.loc[RS['k_name'] == 'k_fair_train', 'k'].iloc[0]); k_alt = float(S[S['train']]['ratio_alt'].mean())
PR = pd.read_csv(f'{OUT}/rules_pairs_all.csv')
for rn in ('skip_fomc | skip_month_end', 'skip_fomc | skip_vix_gt_train_p80', 'skip_fomc | skip_vix_rise_gt10pct', 'skip_fomc | skip_vix_gt_60d_p80'):
    s = PR[(PR['rule'] == rn) & (PR['k_name'] == 'k_fair_train')]
    print(rn, ' '.join(f"{r['sample']}: share {r['share_traded']:.3f} hit {r['hit_rate']:.3f} (d {r['hit_rate_delta']:+.4f}) delta {r['delta_per_trading_day']:+.4f}" for _, r in s.iterrows()))
skip = (S['fomc'] == 1) | (S['month_end'] == 1)
for name, m in (('train', S['train']), ('test', ~S['train'])):
    for scale, col, k in (('primary', 'ratio', k_fair), ('alt', 'ratio_alt', k_alt)):
        sub = S[m & S[col].notna()]; r = sub[col].values; f = skip.values[sub.index]; o_all = k - r; o = np.where(f, 0, o_all); d = o - o_all; lo, hi = ci(d[block_idx(len(r))].mean(1))
        print(f'FOMC|month_end {name} {scale}: share {1-f.mean():.3f} hit {(r[~f] < k).mean():.3f} (d {(r[~f] < k).mean() - (r < k).mean():+.4f}) delta {d.mean():+.4f} CI [{lo:+.4f}, {hi:+.4f}]')
S['yr'] = S['date'].str[:4]
for y, g in S.groupby('yr'):
    r = g['ratio'].values; f = skip.values[g.index]; o_all = k_fair - r; o = np.where(f, 0, o_all)
    print(y, f'delta {(o - o_all).mean():+.4f} hit {(r[~f] < k_fair).mean():.3f} vs {(r < k_fair).mean():.3f} share {1-f.mean():.3f}')
f = S[S['fomc'] == 1]; c = S[(S['fomc'] == 0) & (S['cpi'] == 0) & (S['nfp'] == 0) & (S['opex'] == 0)]
print(f"FOMC days n={len(f)}: median |pm move| {f['absmove_pm'].median()*100:.3f}% vs clean {c['absmove_pm'].median()*100:.3f}%; p90 {f['absmove_pm'].quantile(.9)*100:.3f}% vs {c['absmove_pm'].quantile(.9)*100:.3f}%; hit(k_fair) {(f['ratio'] < k_fair).mean():.3f} vs {(c['ratio'] < k_fair).mean():.3f}; mean outcome FOMC {(k_fair - f['ratio']).mean():+.3f} vs clean {(k_fair - c['ratio']).mean():+.3f}")
print(f"FOMC days on a Wednesday: {int((f['dow'] == 2).sum())} of {len(f)}; Wednesdays in sample {int((S['dow'] == 2).sum())}")
print(f"trade-all test: n={int((~S['train']).sum())}, k_fair={k_fair:.4f}, k_alt={k_alt:.4f}; worst test day ratio {S[~S['train']]['ratio'].max():.2f} on {S.loc[S[~S['train']]['ratio'].idxmax(), 'date']}")
