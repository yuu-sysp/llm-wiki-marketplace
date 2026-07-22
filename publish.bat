@echo off
REM Publish this plugin/marketplace to the GitHub remote.
REM One-time first: git remote add origin https://github.com/<you>/llm-wiki-marketplace.git
setlocal
cd /d "%~dp0"

git rev-parse --is-inside-work-tree >nul 2>&1
if errorlevel 1 (
  echo [NG] Not a git repository. Run "git init" first.
  exit /b 1
)

set MSG=%*
if "%MSG%"=="" set MSG=update llm-wiki plugin

git add -A
git commit -m %MSG%
REM -u origin HEAD: set upstream on first push; works on later pushes too
git push -u origin HEAD
echo.
echo === Published ===
echo On a new PC, install with:
echo   /plugin marketplace add ^<you^>/llm-wiki-marketplace
echo   /plugin install llm-wiki@llm-wiki-marketplace
endlocal
