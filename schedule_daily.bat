@echo off
setlocal

cd /d "%~dp0"

set "TASK_NAME=LeetLoop Daily"
set "RUN_SCRIPT=%~dp0run_now.bat"
set "RUN_TIME=%~1"

if "%RUN_TIME%"=="" set "RUN_TIME=08:00"

if not exist "%RUN_SCRIPT%" (
  echo Could not find run_now.bat.
  exit /b 1
)

echo Creating or updating scheduled task "%TASK_NAME%" at %RUN_TIME%...
schtasks /Create /F /SC DAILY /TN "%TASK_NAME%" /TR "\"%RUN_SCRIPT%\"" /ST %RUN_TIME%
if errorlevel 1 (
  echo Failed to create scheduled task.
  exit /b 1
)

echo.
echo Scheduled task created successfully.
echo Task name: %TASK_NAME%
echo Time: %RUN_TIME%
echo.
echo To change the time, run:
echo   schedule_daily.bat HH:MM
exit /b 0
