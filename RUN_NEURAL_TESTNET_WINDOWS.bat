@echo off
setlocal
cd /d "%~dp0"
echo ==========================================================
echo VERUNAI v0.5 RESEARCH TESTNET - 2 REAL LOCAL PROCESSES
echo ==========================================================
echo Requires Python 3.10+ - all research rewards are fictional.
echo Not safe for live money or Internet-facing mining.
echo.
py -3 -m verunai demo-testnet --protocol neural-v2 --blocks 5 --difficulty 1 --timeout 45
if errorlevel 1 (
  echo.
  echo Python Launcher failed. Trying python...
  python -m verunai demo-testnet --protocol neural-v2 --blocks 5 --difficulty 1 --timeout 45
)
echo.
echo If successful, both nodes had matching chain heads and model state.
echo.
pause
