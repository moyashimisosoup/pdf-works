@echo off
setlocal
cd /d "%~dp0"

echo [PDF Works] Preparing a private Python environment...
if not exist ".venv\Scripts\python.exe" (
    where py >nul 2>&1
    if not errorlevel 1 (
        py -3 -m venv .venv
    ) else (
        where python >nul 2>&1
        if errorlevel 1 goto no_python
        python -m venv .venv
    )
)
if not exist ".venv\Scripts\python.exe" goto setup_failed

".venv\Scripts\python.exe" -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)"
if errorlevel 1 goto python_too_old

".venv\Scripts\python.exe" -m pip install -e ".[desktop]"
if errorlevel 1 goto setup_failed

echo.
echo [PDF Works] Setup completed. You can double-click start-pdf-works.cmd.
echo For optional Zen Maru fonts, run:
echo     .venv\Scripts\python.exe scripts\install_fonts.py
exit /b 0

:no_python
echo [PDF Works] Python 3.11 or newer was not found.
echo Install Python from python.org and run this script again.
exit /b 1

:python_too_old
echo [PDF Works] Python 3.11 or newer is required.
exit /b 1

:setup_failed
echo [PDF Works] Setup failed. Check Python, internet access, and pip messages.
exit /b 1
