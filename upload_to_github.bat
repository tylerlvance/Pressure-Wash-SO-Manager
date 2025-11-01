@echo off
setlocal
cd /d "%~dp0"

REM Ensure main branch
git rev-parse --abbrev-ref HEAD | findstr /i "main" >nul || git branch -M main

REM Add and commit
git add -A
for /f "tokens=1-3 delims=/: " %%a in ('wmic os get LocalDateTime ^| find "."') do set ldt=%%a
set msg=Auto commit %ldt%
git commit -m "%msg%" 2>nul || echo Nothing to commit

REM Push
git push -u origin main
endlocal
pause
