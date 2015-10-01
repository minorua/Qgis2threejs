@echo off
rem env.bat
rem begin: 2015-09-29

if "%OSGEO4W_ROOT%" == "" set OSGEO4W_ROOT=C:\OSGeo4W
if "%QGIS_PACKAGE%" == "" set QGIS_PACKAGE=qgis

call "%OSGEO4W_ROOT%\bin\o4w_env.bat"
set PATH=%OSGEO4W_ROOT%\apps\%QGIS_PACKAGE%\bin;%PATH%
set QGIS_PREFIX_PATH=%OSGEO4W_ROOT:\=/%/apps/%QGIS_PACKAGE%
set PYTHONPATH=%OSGEO4W_ROOT%\apps\%QGIS_PACKAGE%\python
