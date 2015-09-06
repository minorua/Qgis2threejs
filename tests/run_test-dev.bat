@echo off
rem run_test-dev.bat
rem begin: 2015-09-06

set QGIS_PACKAGE=qgis-dev

call C:\OSGeo4W\bin\o4w_env.bat
set PATH=%OSGEO4W_ROOT%\apps\%QGIS_PACKAGE%\bin;%PATH%
set QGIS_PREFIX_PATH=%OSGEO4W_ROOT:\=/%/apps/%QGIS_PACKAGE%
set PYTHONPATH=%OSGEO4W_ROOT%\apps\%QGIS_PACKAGE%\python

python run_test.py

pause
