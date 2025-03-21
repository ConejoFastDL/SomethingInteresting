@echo off
echo ========================================
echo Hoesway GitHub Update Helper
echo ========================================
echo.

rem Check if Git is installed
where git >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Error: Git is not installed or not in your PATH.
    echo Please install Git from https://git-scm.com/downloads
    echo.
    pause
    exit /b 1
)

rem Get current date in YYYY-MM-DD format for default commit message
for /f "tokens=2-4 delims=/ " %%a in ('date /t') do (
    set mm=%%a
    set dd=%%b
    set yy=%%c
)
set today=%yy%-%mm%-%dd%

rem Ask for commit message
set /p commit_message=Enter commit message (or press Enter for default): 

rem Use default message if none provided
if "%commit_message%"=="" (
    set commit_message=Update Hoesway on %today%
)

echo.
echo Adding all files to Git...
git add .

echo.
echo Committing changes with message: "%commit_message%"
git commit -m "%commit_message%"

echo.
echo Pushing to GitHub...
git push origin master

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Error: Failed to push to GitHub. 
    echo Please make sure you have the correct permissions and internet connection.
) else (
    echo.
    echo Success! Your changes have been pushed to GitHub.
)

echo.
pause
