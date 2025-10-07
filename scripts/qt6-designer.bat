@echo off
rem start Qt Designer without QGIS custom widgets
set OSGEO4W_ROOT=C:\OSGeo4W
call "%OSGEO4W_ROOT%\bin\o4w_env.bat"
call "%OSGEO4W_ROOT%\bin\qt6_env.bat"
set QT_PLUGIN_PATH=%OSGEO4W_ROOT%\apps\qt6\plugins
cd %USERPROFILE%
start "Qt Designer" /B "%OSGEO4W_ROOT%\apps\qt6\bin\designer.exe" %*
