%*

@echo off
if %errorlevel% NEQ 0 (
    echo Error occurred: %errorlevel%
    pause
) else (
    timeout /t 5
)
