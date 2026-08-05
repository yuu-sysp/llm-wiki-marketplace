@echo off
REM Double-click launcher for the LLM Wiki installer.
REM Double-click with no args: a folder picker asks where to put the vault.
REM Args pass through to install.ps1  (e.g. install.bat -VaultRoot "D:\shiryo\LLM-Wiki")
REM Auto-install Python if missing: install.bat -VaultRoot "D:\shiryo\LLM-Wiki" -InstallPython
REM Unattended (no dialog, default path): install.bat -NoPrompt
REM Switch console to UTF-8 so Japanese output from install.ps1 is not garbled.
chcp 65001 >nul
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1" %*
pause
