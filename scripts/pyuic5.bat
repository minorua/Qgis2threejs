@echo off
call C:\OSGeo4W\bin\o4w_env.bat

cd /d %~dp1

@echo on
pyuic5.exe -o %~n1.py %~n1.ui

pause