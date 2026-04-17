@echo off
REM LeetLoop Windows Setup Script
REM This script sets up LeetLoop from source on Windows

setlocal enabledelayedexpansion

cd /d "%~dp0"

echo.
echo ======================================
echo LeetLoop - Setup
echo ======================================
echo.

REM Check if Python is installed
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH
    echo Please download and install Python 3.8+ from https://www.python.org
    echo Make sure to check "Add Python to PATH" during installation
    pause
    exit /b 1
)

REM Get Python version
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo Detected Python %PYTHON_VERSION%
echo.

REM Create virtual environment if it doesn't exist
if not exist ".venv" (
    echo Creating virtual environment...
    python -m venv .venv
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment
        pause
        exit /b 1
    )
    echo [OK] Virtual environment created
) else (
    echo [OK] Virtual environment already exists
)

echo.
echo Activating virtual environment...
call .venv\Scripts\activate.bat

echo Upgrading pip...
python -m pip install --upgrade pip -q

echo Installing dependencies...
pip install -r requirements.txt -q

if errorlevel 1 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)

echo [OK] Dependencies installed
echo.

REM Check for .env file
if not exist ".env" (
    echo.
    echo ======================================
    echo Configuration Required
    echo ======================================
    echo.

    if exist ".env.example" (
        copy /Y ".env.example" ".env" >nul
        echo [OK] Created .env from .env.example
    ) else (
        echo ERROR: .env.example was not found
        pause
        exit /b 1
    )

    echo.
    echo You need an OpenAI API key to use LeetLoop
    echo Get one at: https://platform.openai.com/api-keys
    echo.

    set /p OPENAI_KEY=Enter your OpenAI API key: 

    if "!OPENAI_KEY!"=="" (
        echo ERROR: API key is required
        pause
        exit /b 1
    )

    > .tmp_openai_key.txt echo(!OPENAI_KEY!
    python -c "from pathlib import Path; p = Path('.env'); key = Path('.tmp_openai_key.txt').read_text(encoding='utf-8').strip(); content = p.read_text(encoding='utf-8'); content = content.replace('OPENAI_API_KEY=your_openai_api_key_here', 'OPENAI_API_KEY=' + key); p.write_text(content, encoding='utf-8')"
    del /q .tmp_openai_key.txt >nul 2>nul
    if errorlevel 1 (
        echo ERROR: Failed to update .env with the OpenAI API key
        pause
        exit /b 1
    )

    echo [OK] Configuration saved to .env
    echo.
    echo Remaining required fields are still in .env with placeholder values:
    echo   - LEETCODE_SESSION
    echo   - LEETCODE_CSRFTOKEN
    echo Fill those in before starting the app.
) else (
    echo [OK] .env already configured
)

echo.
echo ======================================
echo Setup Complete!
echo ======================================
echo.
echo Next steps:
echo   1. Open .env and fill in any remaining placeholder values
echo   2. Run .\run_app.bat
echo.
echo Or double-click run_app.bat in File Explorer to start LeetLoop.
echo.

pause
