@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
    set "PY=py -3"
) else (
    set "PY=python"
)
%PY% -m pip install -e .
if errorlevel 1 exit /b 1
%PY% -m unittest discover -s tests -v
pause
