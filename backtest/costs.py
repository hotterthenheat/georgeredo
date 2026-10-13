"""Fill and cost models. Returns per-trade return fraction (on premium) and dollars for 1 contract."""
HALF_SPREAD = {'SPY': 0.01, 'QQQ': 0.01, 'IWM': 0.02, 'SPX': 0.015}
FEES = 0.70  # $ per contract per side (commission 0.65 + exchange/regulatory ~0.05)

def settle(ticker, entry_bar, entry_px, legs, model):
    """model: 'mid' (vwap fills, no costs), 'spread' (half-spread each side + fees), 'adverse' (buy bar high, sell bar low + fees)."""
    hs = HALF_SPREAD.get(ticker, 0.05)
    if model == 'adverse': buy = entry_bar['h']
    elif model == 'spread': buy = entry_px * (1 + hs)
    else: buy = entry_px
    buy = max(buy, 0.01)
    proceeds = 0.0
    for frac, px, t, reason in legs:
        sell = px
        if model == 'spread': sell = px * (1 - hs)
        elif model == 'adverse': sell = px * (1 - 2 * hs)  # exits at the bid side of a one-minute range proxy
        proceeds += frac * max(sell, 0.0)
    dollars = (proceeds - buy) * 100
    if model in ('spread', 'adverse'): dollars -= 2 * FEES
    return dict(ret=(proceeds - buy) / buy, dollars=dollars, buy=buy)
