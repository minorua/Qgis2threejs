@echo off
rem update.bat
rem begin: 2015-09-22

call make gettext
sphinx-intl update -p build/locale -c source/conf.py
