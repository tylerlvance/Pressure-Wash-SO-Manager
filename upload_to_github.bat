@echo off
setlocal enableextensions enabledelayedexpansion

REM Path: C:\Users\tyler\Desktop\FoundersSOManager\upload_to_github.bat
REM Description: Add, commit, and push changes to the current branch.
REM Usage: Double click to auto commit with a timestamp message.
REM        Or run from terminal with a custom message:
REM        upload_to_github.bat "Fix invoice rounding"

cd /d "%~dp0"

REM Sanity checks
where git >nul 2>nul || (
  echo Git is not installed or not in PATH.
  echo Install Git from https://git-scm.com/downloads
  pause
  exit /b 1
)

git rev-parse --is-inside-work-tree >nul 2>nul || (
  echo This folder is not a Git repository.
  pause
  exit /b 1
)

REM Determine branch
for /f "delims=" %%B in ('git rev-parse --abbrev-ref HEAD') do set BRANCH=%%B

REM Create a timestamp for the default message
for /f "usebackq delims=" %%T in (`powershell -NoProfile -Command "(Get-Date).ToString('yyyy-MM-dd_HH-mm-ss')"`) do set TS=%%T

REM Commit message
if "%~1"=="" (
  set MSG=Auto commit %TS%
) else (
  set MSG=%*
)

echo Staging changes...
git add -A

REM If nothing staged, skip commit gracefully
git diff --cached --quiet
if %errorlevel%==0 (
  echo No changes to commit.
) else (
  echo Committing...
  git commit -m "%MSG%"
)

REM Push and set upstream if missing
echo Pushing to origin/%BRANCH%...
git push -u origin %BRANCH%
set PUSH_RC=%ERRORLEVEL%

if %PUSH_RC% NEQ 0 (
  echo Push failed. Trying to show more info...
  git status
  echo If this is the first push, make sure the remote exists and you have access:
  git remote -v
  echo Tip: If you renamed your branch, run: git branch -M main
  echo Then re-run this script.
  pause
  exit /b %PUSH_RC%
)

echo Done. Changes are on origin/%BRANCH%.
pause
endlocal
