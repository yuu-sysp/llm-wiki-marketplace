@echo off
REM Publish this plugin/marketplace to the GitHub remote.
REM
REM   publish.bat "what you changed"      <- ALWAYS quote the whole message
REM
REM One-time first: git remote add origin https://github.com/yuu-sysp/llm-wiki-marketplace.git
REM Before publishing, bump "version" in BOTH of these (clients cache per version):
REM   plugins/llm-wiki/.claude-plugin/plugin.json
REM   .claude-plugin/marketplace.json
setlocal
cd /d "%~dp0"

git rev-parse --is-inside-work-tree >nul 2>&1
if errorlevel 1 (
  echo [NG] Not a git repository. Run "git init" first.
  exit /b 1
)

REM Unquoted multi-word messages would be parsed as pathspecs by git commit.
if not "%~2"=="" (
  echo [NG] Quote the whole message:  publish.bat "your message"
  exit /b 1
)
set "MSG=%~1"
if "%MSG%"=="" set "MSG=update llm-wiki plugin"

REM Version gate: same version in both manifests, and bumped when plugins/ changed.
where python >nul 2>&1
if errorlevel 1 (
  echo [!!] python not found - skipping the version check.
) else (
  python "%~dp0tools\check_version.py" "%~dp0."
  if errorlevel 1 (
    echo [NG] Aborted. Fix the version and run again.
    exit /b 1
  )
)

git add -A
git commit -m "%MSG%"
REM -u origin HEAD: set upstream on first push; works on later pushes too
git push -u origin HEAD
if errorlevel 1 (
  echo [NG] push failed.
  exit /b 1
)
echo.
echo === Published ===
echo On a new PC, install with:
echo   /plugin marketplace add yuu-sysp/llm-wiki-marketplace
echo   /plugin install llm-wiki@llm-wiki-marketplace
echo On PCs that already have it, update with:
echo   /plugin marketplace update llm-wiki-marketplace
endlocal
