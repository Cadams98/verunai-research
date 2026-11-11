@echo off
setlocal
cd /d "%~dp0"
echo VERUNAI agent setup check
where python >nul 2>nul
if errorlevel 1 (echo Python: NOT FOUND) else (python --version)
where git >nul 2>nul
if errorlevel 1 (echo Git: NOT FOUND) else (git --version)
where claude >nul 2>nul
if errorlevel 1 (echo Claude Code: NOT INSTALLED) else (echo Claude Code: installed)
where codex >nul 2>nul
if errorlevel 1 (echo Codex CLI: NOT INSTALLED - web or desktop Codex also works) else (echo Codex CLI: installed)
if exist ".claude\agents\security-auditor.md" (echo Claude agents: present) else (echo Claude agents: missing)
where python >nul 2>nul
if not errorlevel 1 python scripts\verify_agent_config.py
pause
