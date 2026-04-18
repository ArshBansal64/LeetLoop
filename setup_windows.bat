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

where python >nul 2>nul
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH
    echo Please download and install Python 3.10+ from https://www.python.org
    echo Make sure to check "Add Python to PATH" during installation
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo Detected Python %PYTHON_VERSION%
echo.

python -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)"
if errorlevel 1 (
    echo ERROR: LeetLoop requires Python 3.10 or newer.
    pause
    exit /b 1
)

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

python src\env_file_utils.py needs-config .env
if errorlevel 1 (
    echo [OK] .env already configured
) else (
    echo.
    echo ======================================
    echo Configuration Required
    echo ======================================
    echo.

    if not exist ".env" (
        if exist ".env.example" (
            copy /Y ".env.example" ".env" >nul
            echo [OK] Created .env from .env.example
        ) else (
            echo ERROR: .env.example was not found
            pause
            exit /b 1
        )
    ) else (
        echo [OK] Existing .env is missing required values and will be updated
    )

    echo.
    echo You need three values to use LeetLoop:
    echo   1. OPENAI_API_KEY
    echo   2. LEETCODE_SESSION
    echo   3. LEETCODE_CSRFTOKEN
    echo.
    echo OpenAI API key:
    echo   https://platform.openai.com/api-keys
    echo.
    echo LeetCode cookie values:
    echo   1. Sign in to https://leetcode.com in your browser
    echo   2. Open Developer Tools ^(F12^)
    echo   3. Go to Application/Storage ^> Cookies ^> https://leetcode.com
    echo   4. Copy the values for LEETCODE_SESSION and csrftoken
    echo.

    set /p OPENAI_KEY=Enter your OpenAI API key: 
    set /p LEETCODE_SESSION_VALUE=Enter your LEETCODE_SESSION value: 
    set /p LEETCODE_CSRF_VALUE=Enter your LEETCODE_CSRFTOKEN value: 

    if "!OPENAI_KEY!"=="" (
        echo ERROR: OPENAI_API_KEY is required
        pause
        exit /b 1
    )
    if "!LEETCODE_SESSION_VALUE!"=="" (
        echo ERROR: LEETCODE_SESSION is required
        pause
        exit /b 1
    )
    if "!LEETCODE_CSRF_VALUE!"=="" (
        echo ERROR: LEETCODE_CSRFTOKEN is required
        pause
        exit /b 1
    )

    set "LEETLOOP_SETUP_OPENAI_API_KEY=!OPENAI_KEY!"
    set "LEETLOOP_SETUP_LEETCODE_SESSION=!LEETCODE_SESSION_VALUE!"
    set "LEETLOOP_SETUP_LEETCODE_CSRFTOKEN=!LEETCODE_CSRF_VALUE!"
    python src\env_file_utils.py update .env
    if errorlevel 1 (
        echo ERROR: Failed to update .env with the required values
        pause
        exit /b 1
    )

    echo [OK] Configuration saved to .env
)

echo.
echo ======================================
echo Setup Complete!
echo ======================================
echo.
echo Next steps:
echo   1. Review .env if you want to confirm the saved values
echo   2. Run .\run_app.bat
echo.
echo Or double-click run_app.bat in File Explorer to start LeetLoop.
echo.

pause
