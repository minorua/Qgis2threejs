@echo off
rem env.bat

if "%OSGEO4W_ROOT%" == "" set OSGEO4W_ROOT=C:\OSGeo4W

call "%OSGEO4W_ROOT%\bin\python-qgis.bat" --version
