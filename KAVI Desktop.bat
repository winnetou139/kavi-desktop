@echo off
REM KAVI Desktop launcher.
REM Double-click this file to open KAVI in its own application window.

cd /d "%~dp0"

REM Prefer pythonw so no console window appears behind the app.
where pythonw >nul 2>&1
if %errorlevel%==0 (
    start "" pythonw "kavi_app.py" %*
    exit /b 0
)

where python >nul 2>&1
if %errorlevel%==0 (
    start "" python "kavi_app.py" %*
    exit /b 0
)

echo Python was not found on PATH.
echo Install Python 3.11 or newer, then run this file again.
pause
exit /b 1
