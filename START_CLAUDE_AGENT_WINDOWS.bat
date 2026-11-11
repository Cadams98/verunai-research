@echo off
cd /d "%~dp0"
where claude >nul 2>nul
if errorlevel 1 (
  echo Claude Code is not installed.
  echo Install from official docs: https://code.claude.com/docs/en/setup
  echo Then reopen this launcher.
  pause
  exit /b 1
)
claude
