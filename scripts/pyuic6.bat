@echo off
call C:\OSGeo4W\bin\o4w_env.bat
path C:\OSGeo4W\apps\qt6\bin;%PATH%

cd /d %~dp1

@echo on
pyuic6.exe -o %~n1.py %~n1.ui

pause
