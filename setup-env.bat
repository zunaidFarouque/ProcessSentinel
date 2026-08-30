@echo off
echo ===================================================
echo Initializing ProcessSentinel Virtual Environment...
echo ===================================================

:: Check if Python is installed
python --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo Error: Python is not installed or not added to your PATH.
    pause
    exit /b
)

:: Create the virtual environment named .venv
echo [1/3] Creating virtual environment (.venv)...
python -m venv .venv

:: Activate the environment and install requirements
echo [2/3] Activating virtual environment and upgrading pip...
call .venv\Scripts\activate
python -m pip install --upgrade pip >nul 2>&1

echo [3/3] Installing dependencies from requirements.txt...
IF EXIST requirements.txt (
    pip install -r requirements.txt
) ELSE (
    echo Warning: requirements.txt not found. Skipping dependency installation.
)

echo ===================================================
echo Setup Complete! 
echo To activate this environment in the future, run:
echo .venv\Scripts\activate
echo ===================================================
pause