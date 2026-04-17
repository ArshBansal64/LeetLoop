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

    > .tmp_openai_key.txt echo(!OPENAI_KEY!
    > .tmp_leetcode_session.txt echo(!LEETCODE_SESSION_VALUE!
    > .tmp_leetcode_csrf.txt echo(!LEETCODE_CSRF_VALUE!
    python -c "from pathlib import Path; p = Path('.env'); content = p.read_text(encoding='utf-8'); openai_key = Path('.tmp_openai_key.txt').read_text(encoding='utf-8').strip(); leetcode_session = Path('.tmp_leetcode_session.txt').read_text(encoding='utf-8').strip(); leetcode_csrf = Path('.tmp_leetcode_csrf.txt').read_text(encoding='utf-8').strip(); content = content.replace('OPENAI_API_KEY=your_openai_api_key_here', 'OPENAI_API_KEY=' + openai_key); content = content.replace('LEETCODE_SESSION=your_leetcode_session_here', 'LEETCODE_SESSION=' + leetcode_session); content = content.replace('LEETCODE_CSRFTOKEN=your_leetcode_csrf_here', 'LEETCODE_CSRFTOKEN=' + leetcode_csrf); p.write_text(content, encoding='utf-8')"
    del /q .tmp_openai_key.txt >nul 2>nul
    del /q .tmp_leetcode_session.txt >nul 2>nul
    del /q .tmp_leetcode_csrf.txt >nul 2>nul
    if errorlevel 1 (
        echo ERROR: Failed to update .env with the required values
        pause
        exit /b 1
    )

    echo [OK] Configuration saved to .env
) else (
    echo [OK] .env already configured
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
