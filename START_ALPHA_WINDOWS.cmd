@echo off
setlocal
cd /d "%~dp0"
echo pdf-works v5.0-alpha Native Qt Viewer
where py >nul 2>nul
if %errorlevel%==0 (
    py -3 -m pdf_works
) else (
    python -m pdf_works
)
if errorlevel 1 (
    echo.
    echo [ERROR] Could not start. Install Python 3.11+ and run:
    echo python -m pip install -e ".[desktop]"
    pause
)
