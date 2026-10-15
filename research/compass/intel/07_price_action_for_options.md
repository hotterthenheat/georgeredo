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
- **One lead remains: month-end afternoons.** They move about 1.6× an ordinary afternoon while the 13:00 straddle is priced at about 1.05×. It did not pass its registered test on the data that suggested it. It is being tested on 2017–2022 month-ends whose option prices no study here has read (V8).

## 2. Angle by angle

| Angle | What was measured | What it means for options | Evidence |
|---|---|---|---|
| **Size of the move** | HAR forecasts: out of sample R² 0.50–0.66 for the session's realised variance (log), median 0.21 for the day's range | The one forecastable part. Whether it beats the option's own price is V4 (pending). The index version (the lifecycle's VOLC) failed | atlas §1–2; V4 |
| **How far it still moves** | From 10:00, a median 0.66–0.72 % to the close across names, 90th percentile 1.9–2.1 %; from 13:00, 0.38–0.41 % | Strike distance for same-day trades | atlas §2 |
| **Touch against finish** | Touched / finished beyond = 2.0 at ½σ to 2σ, both periods, 43 names; against the chain's own price, touches ran 0.91–1.02 × twice the price on SPXW (0.91–1.16 on SPY and QQQ, 1.18–1.33 on IWM) | A touch-stop on a short option exits about twice as often as the option would have expired in the money. About half the touched options still expire worthless | atlas §3; V5 curve |
| **When the extremes form** | The day's high or low is set in the first 30 minutes on 74–78 % of sessions; the opening range holds all day on 3–4 % | Most of a day's range is already spent by 10:00 | atlas §4 |
| **Prior-day high and low** | Hold after a touch 48.9 % against 49.8 % for distance-matched placebos (dev + val) | Not support or resistance; do not place strikes against them | V6 |
| **Round numbers** | Hold +0.4 points more often than placebos (dev + val), the same sign in every window | Real-looking, far too small to matter | V6 |
| **VWAP** | The close is on the same side of VWAP as at 10:00 53–54 % of the time | A coin flip with a small tilt | atlas §5 |
| **Gaps** | Small gaps (< ¼ daily SD) fill 86 % of the time, 1–2 SD gaps 19–22 % | Descriptive; the option-level gap test (S16) found nothing | atlas §6 |
| **Event afternoons (FOMC)** | The 13:00 straddle is priced at 2.33× an ordinary afternoon's; the afternoon moves 2.37× | Priced | V7 |
| **Event afternoons (month-end)** | Priced at 1.05×, moves 1.61× | The one lead (V8) | V7, V8 |
| **The chain's prices by distance** | Out-of-the-money one-strike verticals: realised minus price within ±3 % of width (SPXW, 10:00 and 13:00) | Calibrated; neither side earns after the bid/ask. ETF out-of-the-money puts at 13:00 realise a little less than priced (a forward-only lead) | V5 |
| **Direction** | First half hour against last ≈ 0; day against next −0.06; every entry trigger tested (S06, S07) without a forward move | Do not trade direction with options on these signals | atlas §8; S06, S07 |
| **Volatility through the day** | 16–17 % of the day's movement in the first half hour, 6 % in each midday half hour, 7 % in the last | Premium decays on the clock while movement clusters at the open and close | atlas §9 |

## 3. Still running

- **V3:** same-day premium on the eleven Monday/Wednesday/Friday single names (5,753 sessions, 2017–2026).
- **V4:** does the size forecast beat those names' same-day straddles?
- **V8:** the month-end afternoon straddle on 2017–2022 chains no study here has read.

Their results are added here when they finish.
