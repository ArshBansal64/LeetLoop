@echo off
setlocal

cd /d "%~dp0"

if not exist .venv\Scripts\python.exe (
  echo Missing virtual environment. Run setup.bat first.
  exit /b 1
)

if not exist .env (
  echo Missing .env. Run setup.bat and fill in your credentials first.
  exit /b 1
)

call .venv\Scripts\python.exe src\run_pipeline.py
exit /b %errorlevel%
