@echo off
call C:\OSGeo4W\bin\o4w_env.bat
path C:\OSGeo4W\apps\qt6\bin;%PATH%;"C:\Program Files\Git\usr\bin"

cd /d %~dp1

@echo on
pyuic6.exe -o %~n1.py %~n1.ui

sed -i "s/from PyQt6 import/from qgis.PyQt import/g" %~n1.py
pause
