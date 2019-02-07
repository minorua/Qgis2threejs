@echo off
rem run_test.bat
rem begin: 2015-09-06

if "%OSGEO4W_ROOT%" == "" set OSGEO4W_ROOT=C:\OSGeo4W64
if "%QGIS_PACKAGE%" == "" set QGIS_PACKAGE=qgis
if "%PY_VERSION%" == "" set PY_VERSION=37

call "%OSGEO4W_ROOT%\bin\o4w_env.bat"

set PATH=%OSGEO4W_ROOT%\apps\%QGIS_PACKAGE%\bin;%OSGEO4W_ROOT%\apps\Qt5\bin;%PATH%
set QT_PLUGIN_PATH=%OSGEO4W_ROOT%\apps\Qt5\plugins
set QGIS_PREFIX_PATH=%OSGEO4W_ROOT:\=/%/apps/%QGIS_PACKAGE%
set PYTHONHOME=%OSGEO4W_ROOT%\apps\Python%PY_VERSION%
set PYTHONPATH=%OSGEO4W_ROOT%\apps\%QGIS_PACKAGE%\python

python3 run_test.py > test.log 2>&1
type test.log
pause
