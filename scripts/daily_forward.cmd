@echo off
rem The daily post-close forward job (scripts\daily_forward.py) on the owner's Windows PC: fetch -> verify -> merge ->
rem replay -> append to the cumulative report, ONE run, then exit (Task Scheduler starts it each weekday). It uses the
rem Theta Terminal ALREADY RUNNING on this PC (--source terminal, 127.0.0.1:25503): no login, so it never signs the
rem terminal out. Register it (the PC's clock; 17:45 New York is 16:45 on a Central-time PC, 17:45 on an Eastern one):
rem   schtasks /Create /TN "Compass daily forward" /TR "\"%CD%\scripts\daily_forward.cmd\"" /SC WEEKLY /D MON,TUE,WED,THU,FRI /ST 16:45
rem The job itself skips holidays and half days (the recorder's calendar), waits for 17:30 New York for each session,
rem catches up any session a missed run left (oldest first), and does nothing on a run with nothing pending.
rem It reads the SAME env file as the recorder and the tracker — %USERPROFILE%\.eod_recorder\env, or RECORDER_ENV —
rem lines NAME=value: UW_API_TOKEN=... (one UW call a name for the official close, one for the 17:30 decision price);
rem PAPER_PARQUET_ROOT=... (the stored Parquet layout, required); optionally PAPER_FORWARD_DATA=... (the replay root,
rem data_recorder\paper_backtest_official by default), PAPER_CUMULATIVE=... (the report, research_notes\Compass phase
rem 3\forward_cumulative.md by default), THETA_BASE=... Nothing is read from a file inside the repo; no key is logged.
rem Step 7 (the Compass features forward test) runs too: one Cboe call for the official SPX close when it is not on disk.
rem Exit code: 0 done or nothing pending, 1 a failure (the log's DAILY-FORWARD FAIL line), 2 refused.
cd /d "%~dp0.."
if "%RECORDER_ENV%"=="" set "RECORDER_ENV=%USERPROFILE%\.eod_recorder\env"
if not exist "%RECORDER_ENV%" (
  echo %date% %time% no env file at "%RECORDER_ENV%" — put UW_API_TOKEN=... and PAPER_PARQUET_ROOT=... there
  exit /b 2
)
for /f "usebackq eol=# tokens=1,* delims==" %%a in ("%RECORDER_ENV%") do set "%%a=%%b"
if not exist "%cd%\data_recorder" mkdir "%cd%\data_recorder"
echo %date% %time% daily forward: start >> "%cd%\data_recorder\daily_forward.cmd.log"
python -I scripts\daily_forward.py --source terminal >> "%cd%\data_recorder\daily_forward.cmd.log" 2>&1
set RC=%ERRORLEVEL%
echo %date% %time% daily forward: exit %RC% >> "%cd%\data_recorder\daily_forward.cmd.log"
exit /b %RC%
