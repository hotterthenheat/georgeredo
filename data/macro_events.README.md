# US macro release calendar, 2022-01-01 to 2027-12-31

Built 2026-10-21. Files:

- `macro_events_2022_2027.json`: a JSON list of 231 rows, sorted by date, then time, then kind (NFP, CPI, FOMC_DECISION, FOMC_MINUTES).
- `macro_events_2022_2027.csv`: the same rows with the same columns.
- `check_macro_events.py`: the validator. Run it with `python3 data/check_macro_events.py`. It exits non-zero on any failure.

Each row is `{date, time_et, event, reference_period, status, source}`:

- `event` is one of four kinds:
  - `FOMC_DECISION`: the statement at 14:00 ET on the meeting's last day.
  - `FOMC_MINUTES`: released at 14:00 ET.
  - `CPI`: released at 08:30 ET.
  - `NFP`: the Employment Situation, released at 08:30 ET.
- `reference_period`:
  - For CPI and NFP, the month the data covers (`YYYY-MM`).
  - For FOMC decisions and minutes, the meeting's dates (`YYYY-MM-DD/YYYY-MM-DD`).
- `status`:
  - `released` means the date the data actually came out (on or before 2026-10-21).
  - `scheduled` means a later date, as the agency publishes it today.
- `source` is the primary page the row was checked against.

Every row is included or excluded by its **release date**, which must fall between 2022-01-01 and 2027-12-31. So the file includes:

- December 2021 CPI (2022-01-12)
- December 2021 NFP (2022-01-07)
- The minutes of the December 14-15, 2021 meeting (2022-01-05)

It leaves out the December 2027 CPI and NFP, which BLS releases in January 2028.

## Coverage (validator output)

```
rows: 231  (released 191, scheduled 40)

counts per year per kind (by release date):
year  FOMC_DECISION   FOMC_MINUTES            CPI            NFP
2022              8              8             12             12
2023              8              8             12             12
2024              8              8             12             12
2025              8              9             11             11
2026              8              8             12             12
2027              8              0             12             12
total            48             41             71             71

minutes lag after decision (days): min 19, max 21, Counter({21: 38, 20: 2, 19: 1})

NFP not on a Friday (each checked against BLS):
  2025-07-03 (Thursday) NFP for 2025-06 [released] - Independence Day on Friday Jul 4
  2025-11-20 (Thursday) NFP for 2025-09 [released] - 2025 lapse in appropriations
  2025-12-16 (Tuesday) NFP for 2025-11 [released] - 2025 lapse in appropriations
  2026-02-11 (Wednesday) NFP for 2026-01 [released] - 2026 lapse in appropriations (moved from Fri Feb 6)
  2026-07-02 (Thursday) NFP for 2026-06 [released] - Independence Day observed Friday Jul 3

cancelled releases (no row by design): CPI 2025-10, NFP 2025-10

ALL CHECKS PASSED
```

## Exceptions and gaps

**Cancelled releases.** These have no row by design:

- **October 2025 CPI.** BLS did not collect October 2025 survey data because of the 2025 lapse in appropriations, and published no October CPI release (originally due Thursday 2025-11-13). Where possible, it published October values with the November data.
- **October 2025 Employment Situation.** BLS published no release (originally due Friday 2025-11-07). October's establishment (payroll) estimates first appeared in the November report on 2025-12-16. That row carries `reference_period` 2025-11. No household-survey data were collected for October 2025.

**Releases moved by the lapses in appropriations.** Each date was checked against BLS's notice and the release's own embargo line:

| Release | Originally scheduled | Actually released |
|---|---|---|
| NFP Sep 2025 | Fri 2025-10-03 | Thu 2025-11-20 |
| CPI Sep 2025 | not shown in the fetched notice (the original date is not given here) | Fri 2025-10-24 |
| NFP Nov 2025 | Fri 2025-12-05 | Tue 2025-12-16 |
| CPI Nov 2025 | Wed 2025-12-10 | Thu 2025-12-18 |
| NFP Dec 2025 | Fri 2026-01-09 | no change |
| CPI Dec 2025 | Tue 2026-01-13 | no change |
| NFP Jan 2026 (the brief 2026 lapse) | Fri 2026-02-06 | Wed 2026-02-11 |
| CPI Jan 2026 (the brief 2026 lapse) | Wed 2026-02-11 | Fri 2026-02-13 |

Notes on the table:

- The original and revised dates come from https://www.bls.gov/bls/2025-lapse-revised-release-dates.htm, last modified 2026-02-12.
- The notice as fetched does not list the September 2025 CPI, so its original date is not given here. The 2025-10-24 release date was verified from the release's embargo line. The release notes that September collection was finished before the lapse.

**NFP not on a Friday.** These five are listed by the validator, with reasons:

- **2025-07-03 (Thursday):** Independence Day fell on Friday, July 4.
- **2026-07-02 (Thursday):** the holiday was observed on Friday, July 3.
- **2025-11-20, 2025-12-16 and 2026-02-11:** the lapses in appropriations.

There were no other exceptions in 2022 to 2027. The 2027 schedule has every release on a Friday, including 2027-07-02.

**FOMC.**

- **Decisions:**
  - There were 8 scheduled two-day meetings a year from 2022 to 2027.
  - The Fed's calendar lists **no unscheduled rate meetings** from 2022 to 2027.
  - The 2025-08-22 "notation vote" was on the Statement on Longer-Run Goals and Monetary Policy Strategy. It was not a rate decision, so it is left out.
  - The 2027 meetings are in the file as `scheduled`. The Fed has published them, but it notes that "each meeting date is tentative until confirmed at the meeting immediately preceding it."
- **Minutes:**
  - Past rows use the "(Released …)" date the Fed lists for each meeting.
  - The minutes for the October 27-28 and December 8-9, 2026 meetings are `scheduled` for 2026-11-18 and 2026-12-30. These dates come from the Fed's own monthly event calendars, which list them at 2:00 p.m.
  - **The 2027 minutes are left out.** The Fed has not yet listed their release dates: its 2027 monthly event calendars return 404, and the meetings page has no minutes dates for 2027. They were not extrapolated.
  - Minutes came out 21 days after the decision for 38 meetings. The exceptions:
    - 20 days: 2023-11-21 and 2025-12-30
    - 19 days: 2024-11-26
- **Per-year counts by release date:** 2025 has 9 minutes rows because both the December 2024 minutes (2025-01-08) and the December 2025 minutes (2025-12-30) came out in 2025. 2027 has 0.

## How each row was verified, and the sources

All rows come from primary sources. **No row rests on a secondary source.** A news search (Bloomberg Law, Newsquawk) was used only to learn why the January 2026 releases moved; BLS's own notice is the source for that.

**FOMC decisions and past minutes.**

- Source: https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm, last updated 2026-10-07. It covers 2021 to 2027 and is fetched directly.
- The meetings and the "Released" dates were parsed from that page by script (57 meetings), not typed in by hand.

**Future 2026 minutes.**

- https://www.federalreserve.gov/newsevents/2026-november.htm
- https://www.federalreserve.gov/newsevents/2026-december.htm
- The Fed's October 2026 calendar also confirms the 2026-10-28 meeting and the 2026-10-07 minutes.

**Released CPI and NFP.**

- Sources:
  - https://www.bls.gov/bls/news-release/cpi.htm
  - https://www.bls.gov/bls/news-release/empsit.htm
- These are BLS's news-release archives. Each archived release is filed under its release date (for example, `cpi_10142026` is the September 2026 CPI, released 2026-10-14). Each row's date was read from that file name, and its reference month from the link text.
- For 8 releases, the release itself was opened and its embargo line ("embargoed until 8:30 a.m. (ET) …") matched the date. Those rows cite the archived release as their source:
  - CPI: cpi_10242025, cpi_12182025, cpi_01132026, cpi_02132026
  - NFP: empsit_11202025, empsit_12162025, empsit_01092026, empsit_02112026
- The archives also show the October 2025 releases as "Not published because of 2025 lapse in federal government appropriations."

**Scheduled CPI and NFP (2026-11 to 2027-12).**

- Sources:
  - https://www.bls.gov/schedule/news_release/cpi.htm
  - https://www.bls.gov/schedule/news_release/empsit.htm
- These were cross-checked date by date against the year schedules, which agree:
  - https://www.bls.gov/schedule/2026/home.htm
  - https://www.bls.gov/schedule/2027/home.htm (last modified 2026-10-09)

**Release times.**

- The Fed's calendar gives 2:00 p.m. for statements and minutes.
- BLS's schedules give 8:30 AM ET for CPI and the Employment Situation, including every rescheduled release.
- The times of the other past releases were not opened one by one. They follow BLS's standard 8:30 a.m. ET embargo.

**Fetching.** bls.gov refuses plain scripted HTTP requests (403), so BLS pages were read through a web-fetch tool. federalreserve.gov was fetched directly.

## What could not be verified

- **2027 FOMC minutes:** no release dates have been published, so they are left out.
- **2027 FOMC meetings:** dates are tentative until each preceding meeting confirms them.
- **Scheduled rows** may change if BLS or the Fed revise their schedules, for example after another lapse in appropriations. Re-check them before relying on them.
- **CPI and NFP rows before 2025-10:** the release date of each one was not opened individually. Each rests on BLS's archive index, which files every release under its release date. The 8 shutdown-period releases were opened.

## Rebuilding

The scratch build script is not part of the repo. To rebuild, re-read the five pages above and run `check_macro_events.py`. The validator checks:

- the schema, and that the CSV equals the JSON
- sorting and duplicates
- that every date is Monday to Friday
- the documented NFP weekday exceptions
- that status matches the build date
- the 08:30 / 14:00 times
- that minutes come 19 to 23 days after the decision
- consecutive CPI and NFP reference months except the cancelled ones
- the counts per year per kind
