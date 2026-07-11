@echo off
setlocal

cd /d "%~dp0"

where uv >nul 2>nul
if errorlevel 1 (
    echo uv was not found.
    echo Install uv and run this file again.
    pause
    exit /b 1
)

where npm.cmd >nul 2>nul
if errorlevel 1 (
    echo Node.js and npm were not found.
    echo Install Node.js and run this file again.
    pause
    exit /b 1
)

echo Checking Python dependencies...
uv sync
if errorlevel 1 goto :error

echo Checking frontend dependencies...
pushd frontend
call npm.cmd install --no-audit --no-fund
if errorlevel 1 (
    popd
    goto :error
)

echo Building the frontend...
call npm.cmd run build
if errorlevel 1 (
    popd
    goto :error
)
popd

echo Starting Book Timer at http://127.0.0.1:8000
uv run python web_app.py
exit /b %errorlevel%

:error
echo.
echo Book Timer setup failed.
pause
exit /b 1
