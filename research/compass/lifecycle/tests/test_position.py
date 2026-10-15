"""Hand-checked trades for the position engine (lifecycle protocol §2, §5). Every expected number below is worked out
by hand in the comment beside it, from the synthetic quotes, so the engine's arithmetic is checked against arithmetic,
not against itself."""
import datetime as dt, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from lc.chainmat import ChainDay
from lc import position as ps

N = 20
def day(contracts, spot=None):
    """contracts: list of (strike, is_call, [(m_from, bid, ask), ...]) — quotes hold from m_from until the next entry."""
    C = len(contracts)
    bid = np.full((C, N), np.nan); ask = np.full((C, N), np.nan)
    for i, (_, _, path) in enumerate(contracts):
        for j, (m0, b, a) in enumerate(path):
            m1 = path[j + 1][0] if j + 1 < len(path) else N
            bid[i, m0:m1] = b; ask[i, m0:m1] = a
    s = np.full(N, 100.0) if spot is None else np.asarray(spot, float)
    return ChainDay(root='SPY', session=dt.date(2024, 6, 4), expiration=dt.date(2024, 6, 4), n_min=N,
                    strike=np.array([c[0] for c in contracts], float), is_call=np.array([c[1] for c in contracts]),
                    bid=bid, ask=ask, bid_size=np.full((C, N), 100, np.int32), ask_size=np.full((C, N), 100, np.int32),
                    spot=s, spot_hi=s, spot_lo=s)

AUX = dict(ema5=np.full(N, np.nan), rsi=np.full(N, 60.0), atr5=np.full(N, 1.0), ativ=np.full(N, 0.2))
def legs(*idx): return np.array(list(idx) + [0] * (4 - len(idx)), np.int64)
def ratios(*r): return np.array(list(r) + [0] * (4 - len(r)), np.float64)

def test_hold_to_cutoff():
    # buy at the ask 1.10 at m=2: 110 + 0.70 fee = 110.70; sell at the bid 1.50 at the cutoff m=15: 150 - 0.70 = 149.30
    cd = day([(100.0, True, [(0, 1.00, 1.10), (15, 1.50, 1.60)])])
    o = ps.run_one(cd, AUX, legs(0), ratios(1), 1, 2, 1, np.nan, ps.params(CUTOFF=15))
    assert o['filled'] == 1 and o['entry_m'] == 2 and o['exit_m'] == 15
    assert abs(o['pnl'] - 38.60) < 1e-9 and abs(o['fees'] - 1.40) < 1e-9
    assert abs(o['pnl_cutoff'] - 38.60) < 1e-9 and o['final_reason'] == ps.R['cutoff']

def test_partial_then_trailed_runner():
    # m=5 mid 1.55 -> mark 155, gain (155-110.70)/110.70 = 0.40 >= 0.30: sell half at the bid 1.50:
    #   0.5 x (150 - 0.70) = 74.65 against half the basis 55.35 -> partial1 +19.30
    # m=6..8 mid 2.00 -> peak mark 200; m=9 mid 1.55 -> 155 <= 200 x 0.80: the runner sells at the bid 1.50 -> +19.30
    cd = day([(100.0, True, [(0, 1.00, 1.10), (3, 1.00, 1.10), (5, 1.50, 1.60), (6, 1.95, 2.05), (9, 1.50, 1.60)])])
    o = ps.run_one(cd, AUX, legs(0), ratios(1), 1, 2, 1, np.nan, ps.params(P1_FRAC=0.5, P1_AT=0.30, TRAIL_ARM=0.0, TRAIL_GIVE=0.20))
    assert abs(o['pnl_partial1'] - 19.30) < 1e-9, o
    assert abs(o['pnl_runner'] - 19.30) < 1e-9, o
    assert abs(o['pnl'] - 38.60) < 1e-9 and o['exit_m'] == 9

def test_credit_put_spread_take_profit():
    # short the 95 put at the bid 1.00, long the 94 put at the ask 0.50: -50 per unit, +1.40 fees -> basis -48.60 (credit 48.60)
    # m=6: mark -(0.35) + 0.125 = -0.225 -> buy-back 22.50 <= 50 % of 48.60 = 24.30: close at ask 0.40 / bid 0.10:
    #   -0.40 + 0.10 = -0.30 -> -30 - 1.40 = -31.40 -> P&L = -31.40 + 48.60 = +17.20
    cd = day([(95.0, False, [(0, 1.00, 1.10), (6, 0.30, 0.40)]), (94.0, False, [(0, 0.40, 0.50), (6, 0.10, 0.15)])])
    o = ps.run_one(cd, AUX, legs(0, 1), ratios(-1, 1), 2, 2, 1, np.nan, ps.params(CREDIT_TP=0.5), short_strike=95.0)
    assert o['credit'] == 1 and abs(o['cost0'] + 50.0) < 1e-9
    assert abs(o['pnl'] - 17.20) < 1e-9 and o['final_reason'] == ps.R['credit_tp'] and o['exit_m'] == 6
    assert abs(o['capital_peak'] - 100.0) < 1e-9        # width 1 x 100

def test_add_on_confirmation_lots():
    # entry m=2 at 1.10 (lot 1 cost 110.70); m=5 spot +1.0 = 1 x ATR5 and gain > 0: add one unit at the ask 1.50 (150.70)
    # cutoff m=15 bid 2.00: 199.30 a unit -> lot 1 +88.60, the add +48.60, total +137.20
    sp = np.full(N, 100.0); sp[5:] = 101.0
    cd = day([(100.0, True, [(0, 1.00, 1.10), (5, 1.40, 1.50), (15, 2.00, 2.10)])], spot=sp)
    o = ps.run_one(cd, AUX, legs(0), ratios(1), 1, 2, 1, np.nan, ps.params(CUTOFF=15, ADD_K=1.0, ADD_MAX=1))
    assert o['n_adds'] == 1 and abs(o['pnl_lot_initial'] - 88.60) < 1e-9 and abs(o['pnl_lot_add'] - 48.60) < 1e-9
    assert abs(o['pnl'] - 137.20) < 1e-9 and abs(o['units_peak'] - 2.0) < 1e-12

def test_expiry_physical_and_cash():
    # held to expiry: close 101.00 -> ITM; physical: shares sold at the next open 101.50 -> 150 - 0.70 exercise fee = 149.30
    #   P&L 149.30 - 110.70 = +38.60; cash-settled: intrinsic 1.00 at the close -> 100 - 0.70 = 99.30 -> -11.40
    sp = np.full(N, 100.0); sp[-1] = 101.0
    cd = day([(100.0, True, [(0, 1.00, 1.10)])], spot=sp)
    o = ps.run_one(cd, AUX, legs(0), ratios(1), 1, 2, 1, np.nan, ps.params(CUTOFF=-1), next_open=101.5, cash=False)
    assert abs(o['pnl'] - 38.60) < 1e-9 and o['final_reason'] == ps.R['expiry'], o
    o = ps.run_one(cd, AUX, legs(0), ratios(1), 1, 2, 1, np.nan, ps.params(CUTOFF=-1), next_open=101.5, cash=True)
    assert abs(o['pnl'] + 11.40) < 1e-9

def test_cash_secured_put_assigned():
    # short the 100 put at the bid 1.00: credit 100 - 0.70 = 99.30; close 99.00 -> assigned at 100, shares sold at the
    # next open 98.50: -(100 - 98.50) x 100 = -150, assignment fee 0.70 -> -150.70; P&L = 99.30 - 150.70 = -51.40
    sp = np.full(N, 100.0); sp[-1] = 99.0
    cd = day([(100.0, False, [(0, 1.00, 1.10)])], spot=sp)
    o = ps.run_one(cd, AUX, legs(0), ratios(-1), 1, 2, 1, np.nan, ps.params(CUTOFF=-1), next_open=98.5, cash=False, short_strike=100.0)
    assert abs(o['pnl'] + 51.40) < 1e-9 and abs(o['capital_peak'] - 10000.0) < 1e-9

def test_straddle_close_losing_leg_trail_winner():
    # buy the 100 call and 100 put at the ask 1.00 each: 200 + 1.40 = 201.40; the debit prices a 2.00 move, LEG_K 0.5 -> 1.00
    # m=5 spot 101.2: close the put at its bid 0.40: 40 - 0.70 = 39.30 against half the basis 100.70 -> leg -61.40
    # the call then trails 20 % of its peak: peak mark 245 (m=6), m=7 mark 185 <= 196 -> sell at the bid 1.80:
    #   180 - 0.70 = 179.30 - 100.70 = +78.60; total +17.20
    sp = np.full(N, 100.0); sp[5:] = 101.2
    cd = day([(100.0, True, [(0, 0.95, 1.00), (5, 1.80, 1.90), (6, 2.40, 2.50), (7, 1.80, 1.90)]),
              (100.0, False, [(0, 0.95, 1.00), (5, 0.40, 0.45)])], spot=sp)
    o = ps.run_one(cd, AUX, legs(0, 1), ratios(1, 1), 2, 2, 0, np.nan, ps.params(LEG_K=0.5, LEG_TRAIL=0.2))
    assert abs(o['pnl_leg'] + 61.40) < 1e-9, o
    assert abs(o['pnl_runner'] - 78.60) < 1e-9, o
    assert abs(o['pnl'] - 17.20) < 1e-9

def test_stop_and_double_down():
    # entry 1.10 (110.70). m=4 mid 0.80 -> mark 80, gain -27.7 % <= -25 %: double down, buy 1 more unit at the ask 0.85
    #   (85.70); basis 196.40 for 2 units, average 98.20. m=8 mid 0.60 -> mark 60, gain -38.9 % <= -35 % stop: sell both
    #   at the bid 0.55: 2 x (55 - 0.70) = 108.60 -> P&L -87.80; lot 1 54.30 - 110.70 = -56.40, the double-down 54.30 - 85.70 = -31.40
    cd = day([(100.0, True, [(0, 1.00, 1.10), (4, 0.75, 0.85), (8, 0.55, 0.65)])])
    o = ps.run_one(cd, AUX, legs(0), ratios(1), 1, 2, 1, 90.0, ps.params(STOP=0.35, DD_AT=0.25, DD_MAX=1))
    assert o['n_dd'] == 1 and abs(o['pnl'] + 87.80) < 1e-9, o
    assert abs(o['pnl_lot_initial'] + 56.40) < 1e-9 and abs(o['pnl_lot_dd'] + 31.40) < 1e-9
    assert o['final_reason'] == ps.R['stop'] and o['exit_m'] == 8

def test_thesis_exit_and_missing_quote_wait():
    # the 1m close below the invalidation 99.5 at m=6 closes the position at that minute's bid 0.90 -> 90 - 0.70 - 110.70 = -21.40
    # the entry minute m=2 has no quote: the fill waits to m=3 (QUOTE_WAIT 2)
    sp = np.full(N, 100.0); sp[6:] = 99.4
    cd = day([(100.0, True, [(0, 1.00, 1.10), (2, np.nan, np.nan), (3, 1.00, 1.10), (6, 0.90, 1.00)])], spot=sp)
    o = ps.run_one(cd, AUX, legs(0), ratios(1), 1, 2, 1, 99.5, ps.params(THESIS=1))
    assert o['entry_m'] == 3 and o['exit_m'] == 6 and abs(o['pnl'] + 21.40) < 1e-9 and o['final_reason'] == ps.R['thesis']

def test_scale_in_thirds():
    # 1/3 at m=2 (ask 1.10): 36.67 + 0.233 fee = 36.90; m=7 (+5 min, not invalidated) 1/3 at the ask 1.20: 40.233;
    # m=10 (a 5-minute close above the entry spot) 1/3 at the ask 1.30: 43.567; cutoff m=15 at the bid 1.50:
    # 3 x 1/3 x 149.30 = 149.30 against 120.70 paid -> +28.60; two scale tranches
    sp = np.full(N, 100.0); sp[8:] = 100.5
    cd = day([(100.0, True, [(0, 1.00, 1.10), (7, 1.10, 1.20), (10, 1.20, 1.30), (15, 1.50, 1.60)])], spot=sp)
    o = ps.run_one(cd, AUX, legs(0), ratios(1), 1, 2, 1, 99.0, ps.params(CUTOFF=15, SCALE=1))
    assert o['n_scale'] == 2 and abs(o['units_peak'] - 1.0) < 1e-9, o
    assert abs(o['pnl'] - 28.60) < 1e-9, o

def test_warning_reduce_and_latency():
    # W4 adverse 1 ATR (1.0): m=6 spot 98.9 -> reduce half at the bid 0.80 (LAT 0): 0.5 x 79.30 - 55.35 = -15.70;
    # the rest at the cutoff m=15 bid 0.60: 0.5 x 59.30 - 55.35 = -25.70; total -41.40.
    # With LAT=1 the warning's sale fills at m=7's bid 0.70: 0.5 x 69.30 - 55.35 = -20.70 -> total -46.40
    sp = np.full(N, 100.0); sp[6:] = 98.9
    cd = day([(100.0, True, [(0, 1.00, 1.10), (6, 0.80, 0.90), (7, 0.70, 0.80), (15, 0.60, 0.70)])], spot=sp)
    o = ps.run_one(cd, AUX, legs(0), ratios(1), 1, 2, 1, np.nan, ps.params(CUTOFF=15, WARN_MASK=8, WARN_ACTION=1))
    assert abs(o['pnl_warning'] + 15.70) < 1e-9 and abs(o['pnl'] + 41.40) < 1e-9, o
    o = ps.run_one(cd, AUX, legs(0), ratios(1), 1, 2, 1, np.nan, ps.params(CUTOFF=15, WARN_MASK=8, WARN_ACTION=1, LAT=1))
    assert abs(o['pnl'] + 46.40) < 1e-9, o
