@echo off
call env.bat
python3 run_test.py -d 0 > test.log 2>&1
type test.log
pause
