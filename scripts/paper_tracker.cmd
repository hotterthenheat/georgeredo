@echo off
rem The forward paper confirmation tracker, kept running on this Windows machine beside eod_recorder.cmd: a second
rem Task Scheduler entry (run at startup, whether or not anyone is logged on) that starts the tracker's daemon again
rem whenever it stops. It reads the SAME env file as the recorder — %USERPROFILE%\.eod_recorder\env, or RECORDER_ENV —
rem lines of the form NAME=value, # a comment: UW_API_TOKEN=… (required); PAPER_DATA=… (the data root, data_recorder\paper
rem in the repo by default); PAPER_BUDGET=… (90 calls a session by default — leave it unset or at least 90: a lower
rem value starves candidate 3 and the SPXW flies); PAPER_SPXW=0 (turns the SPXW flies off; on by default); MACRO_EVENTS=… (the macro calendar, data\macro_events_2022_2027.json by default);
rem THETA_BASE=… (the Theta Terminal for VIX, http://127.0.0.1:25503/v3 by default). Nothing is read from a file inside the
rem repo, and the token is never written to the log.
rem
rem Python 3.11+ with polars; on Windows the zoneinfo database needs:  pip install tzdata
cd /d "%~dp0.."
if "%RECORDER_ENV%"=="" set "RECORDER_ENV=%USERPROFILE%\.eod_recorder\env"
if not exist "%RECORDER_ENV%" (
  echo %date% %time% no env file at "%RECORDER_ENV%" — put UW_API_TOKEN=... there and start again
  exit /b 2
)
for /f "usebackq eol=# tokens=1,* delims==" %%a in ("%RECORDER_ENV%") do set "%%a=%%b"
if "%PAPER_DATA%"=="" set "PAPER_DATA=%cd%\data_recorder\paper"
if not exist "%PAPER_DATA%" mkdir "%PAPER_DATA%"
:loop
echo %date% %time% starting the paper tracker >> "%PAPER_DATA%\tracker.cmd.log"
python -I scripts\paper_tracker.py --daemon >> "%PAPER_DATA%\tracker.cmd.log" 2>&1
echo %date% %time% the paper tracker stopped, starting again in 10 s >> "%PAPER_DATA%\tracker.cmd.log"
timeout /t 10 /nobreak > nul
goto loop
