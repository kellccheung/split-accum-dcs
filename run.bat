@echo off
setlocal EnableExtensions

cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo ERROR: Virtual environment not found.
    echo Run setup.bat first.
    pause
    exit /b 1
)

rem Support: drag-and-drop onto run.bat, or pass/paste a config path.
rem Use %* so unquoted paths with spaces still work from the command line.
set "CONFIG=%*"

if "%CONFIG%"=="" (
    echo.
    echo ============================================================
    echo  DCS Run Automation
    echo ============================================================
    echo.
    echo Drag an Excel config file onto this bat to start,
    echo or paste / type the full path below and press Enter.
    echo.
    set /p "CONFIG=Excel config path: "
)

rem Remove surrounding quotes if the user pasted / dropped a quoted path.
if defined CONFIG set "CONFIG=%CONFIG:"=%"

if not defined CONFIG (
    echo ERROR: No Excel config path provided.
    pause
    exit /b 1
)

if "%CONFIG%"=="" (
    echo ERROR: No Excel config path provided.
    pause
    exit /b 1
)

if not exist "%CONFIG%" (
    echo ERROR: Config file not found:
    echo   %CONFIG%
    pause
    exit /b 1
)

echo Using config: %CONFIG%
echo.
".venv\Scripts\python.exe" "src\main.py" --config "%CONFIG%"
set "EXITCODE=%ERRORLEVEL%"

echo.
if %EXITCODE% neq 0 (
    echo Finished with errors. Exit code: %EXITCODE%
) else (
    echo Finished successfully.
)
echo Log files are saved under: %~dp0logs
pause
exit /b %EXITCODE%
