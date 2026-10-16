# Market-intelligence brief — 5. Expiration calendars, and three data corrections (2026-10-15)

**Why this file exists:**
- I told the owner that single names' same-day (0DTE) options were "their Friday expirations". That was wrong.
- The owner corrected it: "they dont have only friday expirations they have m w f".
- This file:
  - replaces the assumption with each name's listed expirations, read from two vendors;
  - checks which finished work the assumption touched;
  - records two more data errors found while checking.

## 1. Which names list which weekdays (OBSERVED)

**Source:**
- ThetaData's list of every expiration a root has had (`option_list_expirations`): `../studies/expiry_calendar_theta.py` → `../results/expiry_calendar/theta_expirations.parquet`, 27 roots, 2012 → 2029.
- Checked date by date against Unusual Whales' historical chains (`../studies/expiry_calendar.py`): for each name, every Monday–Thursday of one week a month, 2023-11-15 → 2026-10-14, with SPY as the control.

**Single names with Monday and Wednesday expirations:**

| Names | First Monday expiration | First Wednesday expiration | Mondays / Wednesdays listed to 2026-10-14 |
|---|---|---|---|
| AAPL, AMZN, AVGO, META, MSFT, NVDA, TSLA | 2026-02-02 | 2026-02-04 | 34 / 35–37 |
| GOOGL | 2026-02-02 | 2026-02-11 | 34 / 35 |
| AMD, INTC, MU | 2026-07-13 | 2026-07-15 | 13 / 13–14 |

- **Before those dates** these names listed **Friday weeklies only**, with the Thursday when the Friday was a holiday (Good Friday, Juneteenth, July 4th, Christmas).
- **Holiday Monday:** on the Tuesday after Memorial Day 2026, the Monday expiration moved to the Tuesday.
- **No other single name** lists a non-Friday expiration in the exchange's end-of-day file for the week of 2026-10-06.
- **Daily (every weekday):** SPY, QQQ and IWM. GLD, SMH and XLF also list every weekday as of September 2026.
- **Monday/Wednesday/Friday:** TLT, SLV, XLE, TQQQ, SOXL and EEM.
- **Wednesday/Friday:** UNG and USO.
- **IBIT:** Monday/Wednesday/Friday, with some Tuesdays.

**The two vendors agree** on 3,616 of 3,618 sampled name-dates. The two disagreements:
- AVGO on 2026-03-04 and UNG on 2024-02-07: ThetaData lists the expiration, and Unusual Whales has no contract on that expiry even on the session before.
- AVGO 2026-03-04 is in V3's pull. Whether ThetaData has quotes for it settles which vendor is right (§5).

**What this means for 0DTE on single names:**
- Same-day sessions three times a week exist on these eleven names only since February (eight names) or July (three) of 2026.
- That is about 70 Monday/Wednesday sessions per name for the eight, and about 26 for the three.
- Any single-name 0DTE history before 2026 is Fridays.

## 2. What the Friday-only assumption touched

| Work | How it picks expirations | Affected? |
|---|---|---|
| V1 (single-name monthlies) | Third-Friday monthlies | No |
| V2 (earnings straddles) | "The first **Friday** expiration on or after the event session whose chain at P−5 is non-empty" (A9). It probed Fridays only | **One trade of 11,802:** AMD 2026-08-05, a Wednesday event session in the hold-out, where a same-day Wednesday expiration existed and V2 held the Friday instead. Checked on all 1,578 of V2's names (§5) |
| S03, S16b (index weeklies) | "Nearest Friday" chosen from the listed candidates: a stated rule, not an assumption | No |
| S17 (SPY/QQQ monthlies) | Listed monthlies | No |
| Lifecycle tiers (index products, Tier D) | Every listed expiration pulled | No |
| `01_audit_and_gaps.md` §2 | Said past expirations "are found by requesting candidate Fridays" | Corrected there |

## 3. Correction: the split rule missed AAPL's 4:1 split

- A10's split rule matched a day-over-day close ratio within 2 % of a standard split ratio.
- AAPL's 4:1 split on 2020-08-31 has a close-to-close ratio of 0.2585, 3.4 % from 1/4 (the open was 2.3 % up on the adjusted prior close). The rule missed it.
- **Fix:** 10 % around ratios of 2:1 or larger, with 3:2 left out so a genuine one-third move is never taken for a split (A10.2).
- **Every split it finds on V3's names is a real one:**
  - AAPL 2020-08-31;
  - TSLA 2020-08-31 and 2022-08-25;
  - NVDA 2021-07-20 and 2024-06-10;
  - AMZN 2022-06-06;
  - GOOGL 2022-07-18;
  - AVGO 2024-07-15.
- It also found one more "split": the next section.

## 4. Correction: "META" before 2022-06-09 is not Facebook

**What the data shows:**
- ThetaData's history under the symbol META closes at $11.95–16.90 from 2021-06-30 to 2022-01-28, then has nothing until 2022-06-09 (close 184.00).
- The earlier series is another security: an ETF that held the ticker before Facebook took it.
- Its option "expirations" from 2021-07-16 are that ETF's options.
- Facebook's own history before 2022-06-09 is under FB.

**Where it mattered:**
- **The lifecycle work** already knew (`../lifecycle/lc/daily.py`: META's root starts 2022-06-09).
- **S06 on Tier A did not.** Its META cells ran on the ETF's one-minute bars (about 148 sessions, 2021-06-30 → 2022-01-28) and had no Facebook before June 2022.
  - **Re-run for META from 2022-06-09** (`../results/v1/s06_signal_screen_META_facebook/`):
    - 28 cells, 20 well-sampled, none clearing the absolute hurdle;
    - the best 30-minute lower bound is −0.04 bp;
    - the original META cells read 22 well-sampled, none clearing, best −0.10 bp.
  - The verdict is unchanged.
  - **Run on Facebook's own bars too**, under FB, 2017-06-01 → 2022-06-08 (`../results/v1/s06_signal_screen_FB/`):
    - 28 cells, 23 well-sampled, none clearing the absolute hurdle;
    - the best lower bound is −0.23 bp at 30 minutes and −0.10 bp at 60.
  - With both, S06 has Facebook's whole history, and no cell on it clears.
- **V3 and the price-action atlas** use FB before 2022-06-09 and META after (A10.3).
- **V1 and V2** start in 2023 and are unaffected.

## 5. Settled after the first pass

### V2 on all of its names

**What was checked:**
- ThetaData's list of every expiration, for all 1,578 of V2's names (`../studies/expiry_calendar_v2names.py` → `../results/expiry_calendar/v2_names_expirations.parquet`).
- Then every V2 trade where a listed expiration fell on or after the event session and before the Friday V2 held: **21 of 11,802** (`../results/expiry_calendar/v2_affected_all_names.csv`).

**What they are:**
- **One is the Wednesday case already known:** AMD 2026-08-05.
- **The other 20 are Friday weeklies** that V2 did probe at P−5, and Unusual Whales returned no contract for them.
- **They did not exist yet at P−5** (`../results/expiry_calendar/v2_affected_listing_check.csv`):
  - ThetaData has no open interest for any of the 20 at P−5, and none for 18 of them at P0 (PONY and CDE have it at P0).
  - 19 of the 20 have open interest on their own expiration day: real weeklies, listed after V2 looked (after P0 for 18 of them). WOLF 2025-10-31 has none even then, so it may never have traded.
- **A9's rule** ("the first Friday whose chain at P−5 is non-empty") skipped them correctly. **V2's result stands; one trade of 11,802 is affected.**

**A coverage gap in Unusual Whales:**
- Its historical chains have none of these 20 weeklies on any session, including their expiration day.
- A study that needs late-listed weeklies cannot take them from Unusual Whales' history. ThetaData carries their open interest.

### AVGO 2026-03-04, and expirations ThetaData lists but never quoted

- ThetaData has no quotes for AVGO's 2026-03-04 expiration. Unusual Whales was right: no such expiration traded.
- V3's pull found five such dates on its eleven names: AMD 2022-12-01 and 2022-12-28, NVDA 2026-02-25, AVGO 2026-03-04, TSLA 2026-04-22. Each is excluded from V3 and counted (`../results/v1/v3_single_name_0dte/exclusions.parquet`).
- **ThetaData's expiration list therefore says what might have been listed, not what traded.** A study takes a session only where the chain has quotes.

### Monday and Wednesday expirations on report days

- **What was counted:** a Monday or Wednesday that was a name's report date, or the session after a post-market report. Only sessions after that name's Monday/Wednesday listings began are counted. That gives 17 sessions to 2026-10-09; every one of these reports was post-market (Unusual Whales' calendar).
- A same-day expiration with quotes existed on only four:
  - AMZN 2026-04-29;
  - GOOGL 2026-07-22;
  - AMD 2026-08-05;
  - AVGO 2026-09-02.
- On the other 13:
  - 10 were never listed;
  - three are the never-quoted dates above.
- So on a report day the Monday/Wednesday expiration is usually absent.

### S06 on Facebook's own bars

Done (§4): no cell clears.
