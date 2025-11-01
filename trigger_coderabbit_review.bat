@echo off
setlocal enabledelayedexpansion
title Trigger Full CodeRabbit Review
cd /d "C:\Users\tyler\Desktop\FoundersSOManager"

echo.
echo ===============================
echo  CodeRabbit Full Review Script
echo ===============================
echo.

REM Check if Git is available
where git >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Git is not available in PATH.
    echo Make sure Git is installed and you can run it from PowerShell or CMD.
    pause
    exit /b
)

REM Show current branch for confirmation
echo Current branch:
git branch
echo.

REM Create new branch
echo Creating branch: coderabbit_full_review ...
git checkout -b coderabbit_full_review || goto :error

echo.
echo Touching all Python files (adding harmless marker)...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
"Get-ChildItem -Recurse -Include *.py | Where-Object {
    $_.FullName -notmatch '\\.venv\\|__pycache__|data\\|attachments\\|invoices\\|dist\\'
} | ForEach-Object {
    try {
        Add-Content -Path $_.FullName -Value '# coderabbit-review-marker'
        Write-Host 'Touched:' $_.FullName
    } catch {
        Write-Host 'Skipped:' $_.FullName
    }
}"

echo.
echo Staging and committing changes...
git add .
git commit -m "Trigger full CodeRabbit review (Python files only)"
if errorlevel 1 (
    echo.
    echo [WARNING] No changes were committed (possibly already marked). Skipping commit.
)

echo.
echo Pushing branch to origin...
git push -u origin coderabbit_full_review || goto :error

echo.
echo -------------------------------------------------------------
echo ✅ Branch 'coderabbit_full_review' pushed successfully.
echo 👉 Open GitHub and create a Pull Request into main.
echo -------------------------------------------------------------
pause
exit /b

:error
echo.
echo ❌ An error occurred.
pause
exit /b
