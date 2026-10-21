@echo off
rem The Compass Phase 2 recorder, kept running on this Windows machine: starts the daemon again whenever it stops —
rem a crash, a network cut, a key refused. Register THIS file with Task Scheduler to run at startup, whether or not
rem anyone is logged on, and the recorder survives a reboot too (mirrors the terminal's scripts/recorder.cmd).
rem
rem THE TOKEN comes from a .env the owner keeps OUTSIDE the repository: %USERPROFILE%\.eod_recorder\env by default
rem (set RECORDER_ENV to another path). Lines of the form NAME=value; # starts a comment. It needs UW_API_TOKEN and
rem may set RECORDER_DATA (the data root; data_recorder\ in the repo by default) and RECORDER_BUDGET (20000).
rem Nothing is read from a file inside the repo, and the token is never written to the log.
rem
rem Python 3.11+ with polars; on Windows the zoneinfo database needs:  pip install tzdata
cd /d "%~dp0.."
if "%RECORDER_ENV%"=="" set "RECORDER_ENV=%USERPROFILE%\.eod_recorder\env"
if not exist "%RECORDER_ENV%" (
  echo %date% %time% no env file at "%RECORDER_ENV%" — put UW_API_TOKEN=... there and start again
  exit /b 2
)
for /f "usebackq eol=# tokens=1,* delims==" %%a in ("%RECORDER_ENV%") do set "%%a=%%b"
if "%RECORDER_DATA%"=="" set "RECORDER_DATA=%cd%\data_recorder"
if not exist "%RECORDER_DATA%" mkdir "%RECORDER_DATA%"
:loop
echo %date% %time% starting the recorder >> "%RECORDER_DATA%\recorder.cmd.log"
python -I scripts\eod_recorder.py --daemon >> "%RECORDER_DATA%\recorder.cmd.log" 2>&1
echo %date% %time% the recorder stopped, starting again in 10 s >> "%RECORDER_DATA%\recorder.cmd.log"
timeout /t 10 /nobreak > nul
goto loop
