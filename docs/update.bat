@echo off
rem update.bat
rem begin: 2015-09-22

call C:\OSGeo4W\bin\o4w_env.bat

echo updating translation files...
call make gettext
sphinx-intl update -p build/locale -c source/conf.py
