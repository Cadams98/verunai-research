@echo off
setlocal
cd /d "%~dp0"
echo ===============================================
echo  VERUNAI - Founded by Christian Adams
 echo  Local setup, tests and disposable TEST demo
 echo ===============================================
where py >nul 2>nul
if not errorlevel 1 (
  set "PYRUN=py -3"
) else (
  where python >nul 2>nul
  if errorlevel 1 (
    echo ERROR: Python 3.10+ not found. Install from https://www.python.org/downloads/windows/
    goto :failed
  )
  set "PYRUN=python"
)
%PYRUN% -c "import sys; assert sys.version_info >= (3,10), 'Python 3.10+ required'"
if errorlevel 1 goto :failed
 echo.
 echo [1/5] Install local Python project dependencies...
%PYRUN% -m pip install -e .
if errorlevel 1 goto :failed
 echo.
 echo [2/5] Verify engineering and safety standards files...
%PYRUN% scripts\check_project_standards.py
if errorlevel 1 goto :failed
 echo.
 echo [3/5] Verify repository structure...
%PYRUN% scripts\check_repository_layout.py
if errorlevel 1 goto :failed
 echo.
 echo [4/5] Run automated tests...
%PYRUN% -m unittest discover -s tests -v
if errorlevel 1 goto :failed
 echo.
 echo [5/5] Run local signed-transfer testnet demo...
%PYRUN% -m verunai demo-ledger-process
if errorlevel 1 goto :failed
 echo.
 echo Setup and local demonstration finished successfully.
 echo No cryptocurrency or public miner was launched.
pause
exit /b 0
:failed
 echo.
 echo A setup or test step failed. Read the error above.
 echo See docs\START_HERE_WINDOWS.md for help.
pause
exit /b 1
