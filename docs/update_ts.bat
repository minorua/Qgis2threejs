@echo off
rem update.bat
rem begin: 2015-09-22

set PATH=%PATH%;C:\Python38\Scripts

echo updating translation files...
call make gettext
sphinx-intl update -p build/locale
pause
