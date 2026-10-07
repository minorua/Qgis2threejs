@echo off
rem Usage: inspector.bat <page.html> [--timeout SEC] [--port PORT]

rem Chromium's sandbox may not work in some environments (e.g. when the parent process is in a job object).
if "%QTWEBENGINE_CHROMIUM_FLAGS%" == "" set QTWEBENGINE_CHROMIUM_FLAGS=--no-sandbox

call "%~dp0..\..\scripts\env.bat"

python "%~dp0inspector.py" %*
exit /b %ERRORLEVEL%
