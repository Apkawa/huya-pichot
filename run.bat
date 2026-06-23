@echo off
setlocal

cd /d "%~dp0"

rem Check for uv
where uv >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: uv is not installed or not in PATH
    echo Install it from https://github.com/astral-sh/uv
    exit /b 1
)

rem Check for python availability (uv handles this, but warn if uv can't find one)
uv python list >nul 2>&1
if %errorlevel% neq 0 (
    echo Warning: uv python toolchain check failed
)

rem Check for LibreHardwareMonitor folder
if not exist "LibreHardwareMonitor" (
    echo Error: LibreHardwareMonitor folder not found
    echo Place it next to this script: %~dp0LibreHardwareMonitor\
    exit /b 1
)

rem Run the script
uv run ./hua_pichot.py

pause
