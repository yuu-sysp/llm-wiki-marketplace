@echo off
REM Double-click launcher for the LLM Wiki installer.
REM Args pass through to install.ps1  (e.g. install.bat -VaultRoot "D:\shiryo\LLM-Wiki")
REM Auto-install Python if missing: install.bat -VaultRoot "D:\shiryo\LLM-Wiki" -InstallPython
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1" %*
pause
