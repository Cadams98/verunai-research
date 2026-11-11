@echo off
cd /d "%~dp0"
where codex >nul 2>nul
if errorlevel 1 (
  echo Codex CLI is not installed. You can also use https://chatgpt.com/codex
  echo See docs\AGENT_SETUP_WINDOWS.md for instructions.
  pause
  exit /b 1
)
codex
