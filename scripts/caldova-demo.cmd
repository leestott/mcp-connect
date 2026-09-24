@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
set "CONTROLLER=%SCRIPT_DIR%present_caldova_demo.ps1"
set "SHOW_RUNNER=%SCRIPT_DIR%run_caldova_presentation.ps1"
set "LIVE_RUNNER=%SCRIPT_DIR%run_caldova_live_presentation.ps1"

if "%~1"=="" goto usage

if /I "%~1"=="show" (
    powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%SHOW_RUNNER%"
    exit /b %ERRORLEVEL%
)
if /I "%~1"=="live" (
    if "%~2"=="" (
        echo Supply the deployed HTTPS website URL.
        echo Example: caldova-demo live https://your-host.example
        exit /b 2
    )
    powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%LIVE_RUNNER%" -WebUrl "%~2"
    exit /b %ERRORLEVEL%
)

if /I "%~1"=="preflight" goto preflight
if /I "%~1"=="prepare" goto prepare
if /I "%~1"=="demo1" goto demo1
if /I "%~1"=="demo2" goto demo2
if /I "%~1"=="demo3" goto demo3
if /I "%~1"=="demo4" goto demo4
if /I "%~1"=="demo5" goto demo5
if /I "%~1"=="audit" goto audit
if /I "%~1"=="reset" goto reset
if /I "%~1"=="help" goto usage

echo Unknown command: %~1
echo.
goto usage_error

:preflight
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%CONTROLLER%" preflight
exit /b %ERRORLEVEL%

:prepare
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%CONTROLLER%" reset
exit /b %ERRORLEVEL%

:demo1
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%CONTROLLER%" inspect
exit /b %ERRORLEVEL%

:demo2
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%CONTROLLER%" analysis
exit /b %ERRORLEVEL%

:demo3
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%CONTROLLER%" deny
exit /b %ERRORLEVEL%

:demo4
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%CONTROLLER%" approve
exit /b %ERRORLEVEL%

:demo5
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%CONTROLLER%" replay
if errorlevel 1 exit /b %ERRORLEVEL%
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%CONTROLLER%" audit
exit /b %ERRORLEVEL%

:audit
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%CONTROLLER%" audit
exit /b %ERRORLEVEL%

:reset
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%CONTROLLER%" reset
exit /b %ERRORLEVEL%

:usage
echo Caldova presentation commands
echo.
echo   caldova-demo show        Guided deck-ordered presentation runner
echo   caldova-demo live URL    Live terminal/browser runner for an authenticated HTTPS site
echo   caldova-demo preflight   Validate Python, tests, server, and fixtures
echo   caldova-demo prepare     Reset the synthetic scenario before slide 1
echo   caldova-demo demo1       MCP stdio discovery, schema, call, and denial
echo   caldova-demo demo2       Run deterministic local analysis
echo   caldova-demo demo3       Show denied write and unchanged inventory
echo   caldova-demo demo4       Approve and quarantine with the synthetic name
echo   caldova-demo demo5       Replay, verify zero changes, and show audit
echo   caldova-demo audit       Show current local audit evidence
echo   caldova-demo reset       Restore the scenario after the presentation
exit /b 0

:usage_error
call :usage
exit /b 2
