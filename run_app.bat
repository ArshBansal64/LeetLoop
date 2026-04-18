@echo off

setlocal



cd /d "%~dp0"



if not exist .venv\Scripts\python.exe (

  echo Missing virtual environment. Run setup_windows.bat first.

  exit /b 1

)



if not exist .env (

  echo Missing .env. Run setup_windows.bat first.

  exit /b 1

)



call .venv\Scripts\python.exe src\run_service.py --ui

exit /b %errorlevel%

