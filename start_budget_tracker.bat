
@echo off
echo Starting the Budget Tracker web server...
echo You can close this window to stop the server at any time.

:: Navigate to the directory where this script is located
cd /d "%~dp0"

:: The 'start' command opens the URL in the default browser.

timeout /t 1 /nobreak > nul

venv\Scripts\python.exe app.py > budget_tracker_startup.log 2>&1


