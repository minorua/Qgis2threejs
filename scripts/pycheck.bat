@echo off
PATH C:\Python37;C:\Python37\Scripts;%PATH%
SET PYTHONHOME=C:\Python37

cd %~dp0..

echo [pyflakes]
pyflakes .


echo;
set IGNORE=E501,E731
rem E501: line too long (82 > 79 characters)
rem E731: do not assign a lambda expression, use a def

echo [pycodestyle ignore=%IGNORE%]
pycodestyle --ignore=%IGNORE% --exclude ui .

pause
