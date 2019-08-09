@echo off
SET OSGEO4W_ROOT=C:\OSGeo4W64
SET PYTHONHOME=%OSGEO4W_ROOT%\apps\Python37
PATH %OSGEO4W_ROOT%\apps\Python37;%OSGEO4W_ROOT%\apps\Python37\Scripts;%PATH%

cd %~dp0..

echo [pyflakes]
call pyflakes .


echo;
set IGNORE=E501,E731
rem E501: line too long (82 > 79 characters)
rem E731: do not assign a lambda expression, use a def

echo [pycodestyle ignore=%IGNORE%]
call pycodestyle --ignore=%IGNORE% --exclude ui .

pause
