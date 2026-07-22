@echo off
REM LLM Wiki インストーラのダブルクリック導線。
REM 引数はそのまま install.ps1 に渡す（例: install.bat -VaultRoot "D:\資料\LLM-Wiki"）
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1" %*
pause
