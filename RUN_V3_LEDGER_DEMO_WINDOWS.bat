@echo off
setlocal
cd /d "%~dp0"
echo VERUNAI v0.6 — independent-node signed TEST payment demonstration
echo Research only. No money or exchangeable cryptocurrency.
where py >nul 2>nul
if %errorlevel%==0 (
    set "PY=py -3"
) else (
    set "PY=python"
)
%PY% -m pip install -e .
if errorlevel 1 (
    echo Could not install project dependencies. Check Python 3.10+ and internet connection.
    pause
    exit /b 1
)
%PY% -m verunai demo-ledger-process
if errorlevel 1 (
    echo Demonstration failed. See the message above.
)
pause
