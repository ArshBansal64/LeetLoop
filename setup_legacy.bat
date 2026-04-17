@echo off
setlocal

cd /d "%~dp0"

if not exist .venv (
  echo Creating virtual environment...
  py -3 -m venv .venv || goto :error
) else (
  echo Virtual environment already exists.
)

echo Upgrading pip...
call .venv\Scripts\python.exe -m pip install --upgrade pip || goto :error

echo Installing dependencies...
call .venv\Scripts\python.exe -m pip install -r requirements.txt || goto :error

if not exist .env (
  echo Creating .env from .env.example...
  copy .env.example .env >nul || goto :error
  echo.
  echo Open .env and fill in your credentials before running the planner.
) else (
  echo .env already exists.
)

if not exist history (
  mkdir history || goto :error
)

echo.
echo Setup complete.
echo Next steps:
echo   1. Fill in .env
echo   2. Run run_now.bat
echo   3. Optionally run schedule_daily.bat
exit /b 0

:error
echo.
echo Setup failed.
exit /b 1
