"""Compact tables for the notes, read off the CSVs in out/. Writes out/summary.txt"""
import os, polars as pl
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'out')
pl.Config.set_tbl_cols(40); pl.Config.set_tbl_width_chars(320); pl.Config.set_tbl_rows(500); pl.Config.set_float_precision(3)
L = []
def show(title, df): L.append(f'\n## {title}\n{df}\n')
r = lambda f: pl.read_csv(os.path.join(OUT, f), infer_schema_length=10000)
C = r('em_contain.csv')
show('EM containment (|close-spot|/straddle): 68.3% quantile and root-mean-square, by product, period, scan',
     C.filter(pl.col('scan').is_in(['09:35', '10:00', '11:00', '12:00', '13:00', '14:00', '15:00', '15:30', '15:50'])).select('product', 'period', 'scan', 'sessions', 'q683_close_over_straddle', 'sd_close_over_straddle', 'share_within_1x', 'share_within_1p2533x').sort('product', 'period', 'scan'))
E = r('em_exceed.csv')
show('EM exceedance of spot +/- M before the close (minute closes; barHL = ETF bar highs/lows)',
     E.filter(pl.col('scan').is_in(['09:35', '10:00', '12:00', '14:00', '15:00', '15:50'])).select('product', 'period', 'scan', 'mult', 'sessions', 'exceed_either', 'exceed_up', 'exceed_down', 'close_outside', 'exceed_either_barHL').sort('product', 'period', 'scan', 'mult'))
F = r('em_fade.csv')
show('Fade at the first touch of spot +/- M, all scans pooled', F.filter(pl.col('cut') == 'all scans').select('product', 'period', 'mult', 'touches', 'sessions', 'p_close_back_inside', 'fade15_bps', 'fade30_bps', 'fade60_bps', 'fade_close_bps', 'median_mins_left', 'trades', 'entry_ask_median', 'ret_trail', 'pnl_trail_usd', 'win_trail', 'stopped', 'ret_hold', 'pnl_hold_usd').sort('product', 'period', 'mult'))
show('Fade by side', F.filter(pl.col('cut') == 'by side').select('product', 'period', 'mult', 'side', 'touches', 'p_close_back_inside', 'fade30_bps', 'fade_close_bps', 'trades', 'ret_trail', 'pnl_trail_usd', 'win_trail').sort('product', 'period', 'mult', 'side'))
show('Fade by scan time, SPY and SPXW', F.filter((pl.col('cut') == 'by scan') & pl.col('product').is_in(['SPY', 'SPXW'])).select('product', 'period', 'mult', 'scan', 'touches', 'p_close_back_inside', 'fade30_bps', 'fade_close_bps', 'median_mins_left', 'trades', 'ret_trail', 'pnl_trail_usd', 'win_trail').sort('product', 'period', 'mult', 'scan'))
show('Fade by scan time, QQQ and IWM', F.filter((pl.col('cut') == 'by scan') & pl.col('product').is_in(['QQQ', 'IWM'])).select('product', 'period', 'mult', 'scan', 'touches', 'p_close_back_inside', 'fade30_bps', 'fade_close_bps', 'median_mins_left', 'trades', 'ret_trail', 'pnl_trail_usd', 'win_trail').sort('product', 'period', 'mult', 'scan'))
show('Fade stress (day bootstrap, without best 5 days, by year)', r('em_fade_stress.csv').filter(pl.col('measure') != 'pnl_hold').sort('product', 'measure', 'period', 'mult'))
show('King proxy reachability', r('king_reach.csv'))
show('ATR: touch fades by extension bucket', r('atr_touch.csv').select('product', 'period', 'bucket', 'events', 'sessions', 'p_close_back_inside', 'fade30_bps', 'fade_close_bps', 'trades', 'ret_trail', 'pnl_trail_usd', 'win_trail', 'ret_hold').sort('product', 'period'))
show('ATR: sweep fades by extension bucket', r('atr_sweep.csv').select('product', 'period', 'bucket', 'events', 'sessions', 'p_close_back_inside', 'fade30_bps', 'fade_close_bps', 'trades', 'ret_trail', 'pnl_trail_usd', 'win_trail', 'ret_hold').sort('product', 'period'))
show('ATR x UW gamma regime (prior session net gamma), 2025-10-16 to 2026-10-09', r('atr_gamma.csv').select('product', 'event', 'regime', 'bucket', 'events', 'sessions', 'p_close_back_inside', 'fade30_bps', 'fade_close_bps', 'trades', 'ret_trail', 'pnl_trail_usd', 'win_trail').sort('product', 'event', 'bucket', 'regime'))
LD = r('flow_lead.csv')
show('Flow proxy lead: per-session slope (bps of underlying per 1 SD of signal) and t across sessions; partial = with the underlying\'s own last-5-min return as a control',
     LD.filter(pl.col('window') == 5).select('product', 'period', 'signal', 'horizon', 'obs', 'sessions', 'sign_agree', 'corr', 'slope_bps_per_sd', 't_by_session', 'partial_slope_bps_per_sd', 't_partial').sort('product', 'signal', 'period', 'horizon'))
show('Flow proxy lead, 1 and 15 minute windows (share)', LD.filter((pl.col('window') != 5) & pl.col('signal').str.starts_with('share')).select('product', 'period', 'signal', 'horizon', 'slope_bps_per_sd', 't_by_session', 'partial_slope_bps_per_sd', 't_partial').sort('product', 'signal', 'period', 'horizon'))
show('Flow quintiles (share_5, 30-min horizon)', r('flow_quintiles.csv').filter((pl.col('window') == 5) & (pl.col('horizon') == 30)).sort('product', 'period', 'quintile'))
show('Sweep entries with/without the trade-side premium condition (pnl $ a contract, 50% trail)', r('flow_sweep.csv').select('product', 'period', 'kind', 'condition', 'window', 'trades', 'days', 'mean', 'win', 'ci_lo', 'ci_hi', 'wo_best5').sort('product', 'kind', 'period', 'window', 'condition'))
S = r('swing_etf.csv')
show('Swing entries on daily bars (forward returns, bps)', S.filter(pl.col('horizon').is_in([5, 20])).sort('sym', 'event', 'period', 'horizon'))
show('Swing entries, UW cross-section (market-adjusted, by-date t)', r('swing_uw.csv'))
open(os.path.join(OUT, 'summary.txt'), 'w').write('\n'.join(L)); print('\n'.join(L))
