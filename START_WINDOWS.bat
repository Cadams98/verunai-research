@echo off
setlocal
cd /d "%~dp0"
echo ====================================
echo VERUNAI local two-node research test
 echo ====================================
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 -m verunai demo-testnet --blocks 8 --difficulty 2
) else (
  python -m verunai demo-testnet --blocks 8 --difficulty 2
)
if errorlevel 1 (
  echo.
  echo Could not run the demo. Install Python 3.10+ and try again.
)
echo.
pause
