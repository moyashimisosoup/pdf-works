@echo off
setlocal
cd /d "%~dp0"

rem CI may supply a preinstalled Python, otherwise use a project-local venv.
if defined PDF_WORKS_PYTHON (
    set "PYEXE=%PDF_WORKS_PYTHON%"
) else (
    if not exist ".venv\Scripts\python.exe" (
        call "%~dp0setup-pdf-works.cmd"
        if errorlevel 1 goto failed
    )
    set "PYEXE=%~dp0.venv\Scripts\python.exe"
)

rem CI and troubleshooting can check the launcher without opening a GUI.
if /I "%~1"=="--check" (
    "%PYEXE%" -c "import PySide6, fitz, pdf_works"
    if errorlevel 1 goto failed
    echo [PDF Works] Python dependencies and launcher: OK
    exit /b 0
)

"%PYEXE%" -c "import PySide6, fitz, pdf_works" 1>nul 2>nul
if errorlevel 1 (
    if defined PDF_WORKS_PYTHON goto failed
    echo [PDF Works] Installing or repairing project dependencies...
    call "%~dp0setup-pdf-works.cmd"
    if errorlevel 1 goto failed
)

echo [PDF Works] Launching the Windows editor...
"%PYEXE%" -m pdf_works
if errorlevel 1 goto failed
exit /b 0

:failed
echo.
echo [PDF Works] Unable to start. For setup details run setup-pdf-works.cmd.
echo Nothing was written to an existing PDF by this launcher.
pause
exit /b 1
