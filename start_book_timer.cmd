@echo off
setlocal

cd /d "%~dp0"

set "PYTHON_CMD="

if exist ".venv\Scripts\python.exe" (
    set "PYTHON_CMD=.venv\Scripts\python.exe"
) else (
    where py >nul 2>nul
    if %errorlevel%==0 (
        set "PYTHON_CMD=py -3"
    ) else (
        where python >nul 2>nul
        if %errorlevel%==0 (
            set "PYTHON_CMD=python"
        )
    )
)

if not defined PYTHON_CMD (
    echo Python 3 was not found.
    echo Install Python or create .venv first.
    pause
    exit /b 1
)

%PYTHON_CMD% book_timer.py
set "EXIT_CODE=%errorlevel%"

if not "%EXIT_CODE%"=="0" (
    echo.
    echo book_timer.py exited with code %EXIT_CODE%.
    pause
)

exit /b %EXIT_CODE%
