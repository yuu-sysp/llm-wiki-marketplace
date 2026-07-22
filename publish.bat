@echo off
REM プラグインを GitHub リポジトリへ発行する。
REM 事前に一度だけ: git remote add origin https://github.com/<you>/llm-wiki-marketplace.git
setlocal
cd /d "%~dp0"

git rev-parse --is-inside-work-tree >nul 2>&1
if errorlevel 1 (
  echo [NG] git リポジトリではありません。先に `git init` してください。
  exit /b 1
)

set MSG=%*
if "%MSG%"=="" set MSG=update llm-wiki plugin

git add -A
git commit -m "%MSG%"
git push
echo.
echo === 発行完了（push まで） ===
echo 新規PCでは次で導入できます:
echo   /plugin marketplace add ^<you^>/llm-wiki-marketplace
echo   /plugin install llm-wiki@llm-wiki-marketplace
endlocal
