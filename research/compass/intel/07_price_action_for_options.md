# Market-intelligence brief — 7. What price action tells an options trader, from every angle (2026-10-15)

**The owner's ask:** "we need to perfect price action so we can do options better, look from every single possible angle."

**How this was answered:**
- **The map.** Every angle was listed first: 62 of them, with the published evidence and what this repository had already tested (`04_price_action_angles.md`).
- **The atlas.** The underlying's behaviour was measured on 43 names from 2017 to 2026 without testing anything (`06_price_action_atlas.md`).
- **The tests.** The open angles that matter for options were registered before their data was read and then tested (V3–V8, `../04_protocol.md` A10–A15, `../05_results.md`).

**The rule throughout:** an angle helps an options trader only if it predicts something the option has not already priced, by more than the bid/ask spread.

## 1. The short answer

- **The size of the move is the forecastable part of price action; its direction is not.**
  - From one-minute bars, a simple model explains 50–66 % of the variance of the session's realised variance (log scale) out of sample, by name.
  - The day's range: a median 21 % out of sample.
  - Direction (first half hour against last, one day against the next, every entry trigger tested) is noise.
- **The index options already price the size, the event days and the distance.**
  - SPXW's same-day chain is priced within ±3 % of width of what then happens, at every distance tested (V5).
  - FOMC afternoons are priced at what they move (V7).
- **Price levels are not walls.** Prior-day highs and lows hold no better than random levels at the same distance. Round numbers hold under one point more often (V6).
- **Paths behave like a random walk.** A level is touched twice as often as the close finishes beyond it, so stops on short options exit about twice as often as the option would have finished in the money (atlas §3).
- **The forecastable size is already in the price, on single names too.** A forecast of the session's move picked slightly better days to sell same-day single-name straddles in development and validation, then reversed in the hold-out. No cell made money (V4).
- **Single-name same-day options lose on both sides after the bid/ask.** Selling the straddle at 10:00 returned −19.8 % of premium and buying it −23.4 % (development + validation). The median spread is 8.3 % of the mid, larger than what the price over-forecasts (V3).
- **The one lead, month-end afternoons, did not replicate.** On 2022–2026 they moved about 1.6× an ordinary afternoon while the 13:00 straddle priced about 1.05×. On 2017–2022 month-ends that no study here had read, buying that straddle lost: SPXW −6.6 % [−24.5, +12.6], SPY −8.4 % [−27.2, +11.3] (V8).
- **No angle tested here gives an edge after costs and out-of-sample checks.** What price action does give an options trader is description: how far a session still moves, how often a level is touched against finished beyond, and when the extremes form.

## 2. Angle by angle

| Angle | What was measured | What it means for options | Evidence |
|---|---|---|---|
| **Size of the move** | HAR forecasts: out of sample R² 0.50–0.66 for the session's realised variance (log), median 0.21 for the day's range | The one forecastable part, and already priced. On single names, adding the forecast to the straddle's implied move raised the R² for the realised move from 0.113 to 0.115; trading on it made nothing (V4). The index version (the lifecycle's VOLC) failed | atlas §1–2; V4 |
| **Single-name same-day premium** | Eleven names, 2017–2026: the 10:00 straddle over-forecasts the move (median realised ÷ implied 0.72), and its spread is a median 8.3 % of the mid | Both sides lose after the bid/ask, on every name; the new Monday and Wednesday sessions look the same | V3 |
| **How far it still moves** | From 10:00, a median 0.66–0.72 % to the close across names, 90th percentile 1.9–2.1 %; from 13:00, 0.38–0.41 % | Strike distance for same-day trades | atlas §2 |
| **Touch against finish** | Touched / finished beyond = 2.0 at ½σ to 2σ, both periods, 43 names; against the chain's own price, touches ran 0.91–1.02 × twice the price on SPXW (0.91–1.16 on SPY and QQQ, 1.18–1.33 on IWM) | A touch-stop on a short option exits about twice as often as the option would have expired in the money. About half the touched options still expire worthless | atlas §3; V5 curve |
| **When the extremes form** | The day's high or low is set in the first 30 minutes on 74–78 % of sessions; the opening range holds all day on 3–4 % | Most of a day's range is already spent by 10:00 | atlas §4 |
| **Prior-day high and low** | Hold after a touch 48.9 % against 49.8 % for distance-matched placebos (dev + val) | Not support or resistance; do not place strikes against them | V6 |
| **Round numbers** | Hold +0.4 points more often than placebos (dev + val), the same sign in every window | Real-looking, far too small to matter | V6 |
| **VWAP** | The close is on the same side of VWAP as at 10:00 53–54 % of the time | A coin flip with a small tilt | atlas §5 |
| **Gaps** | Small gaps (< ¼ daily SD) fill 86 % of the time, 1–2 SD gaps 19–22 % | Descriptive; the option-level gap test (S16) found nothing | atlas §6 |
| **Event afternoons (FOMC)** | The 13:00 straddle is priced at 2.33× an ordinary afternoon's; the afternoon moves 2.37× | Priced | V7 |
| **Event afternoons (month-end)** | 2022–2026: priced at 1.05×, moved 1.61×. 2017–2022: the long straddle lost (realised ÷ implied 0.81 SPXW, 0.74 SPY) | A feature of one window; not a lasting mispricing | V7, V8 |
| **The chain's prices by distance** | Out-of-the-money one-strike verticals: realised minus price within ±3 % of width (SPXW, 10:00 and 13:00) | Calibrated; neither side earns after the bid/ask. ETF out-of-the-money puts at 13:00 realise a little less than priced (a forward-only lead) | V5 |
| **Direction** | First half hour against last ≈ 0; day against next −0.07 and −0.06 (2017–22, 2023–26); every entry trigger tested (S06, S07) without a forward move | Do not trade direction with options on these signals | atlas §8; S06, S07 |
| **Volatility through the day** | 16–17 % of the day's movement in the first half hour, 6 % in each midday half hour, 7 % in the last | Premium decays on the clock while movement clusters at the open and close | atlas §9 |

## 3. The last three tests

| Test | Question | Result |
|---|---|---|
| V3 | Same-day premium on the eleven Monday/Wednesday/Friday single names (5,859 sessions, 2017–2026) | Rejected. Short straddle −19.8 % [−25.5, −14.7], long −23.4 % [−28.1, −18.3] of premium (development + validation); hold-out −7.4 % and −19.6 %. The put sale one implied move below is noise around zero |
| V4 | Does a price-action forecast of the session's move beat those straddles? | Rejected. Selling the richest third returned −10.4 %, 6.5 points better than selling every session (development + validation); in the hold-out −14.1 %, 6.5 points worse. The forecast's coefficient beside the implied move is +0.37 [−0.05, +0.77], then −0.18 in the hold-out |
| V8 | The month-end 13:00 long straddle on 2017–2022 chains no study here had read | Rejected. SPXW −6.6 % [−24.5, +12.6] over 56 month-ends, SPY −8.4 % [−27.2, +11.3] over 49. The 2022–2026 lead (+40.5 %) did not replicate |

Full tables: `../05_results.md` (V3, V4, V8) and each test's `REPORT.md` under `../results/v1/`.
