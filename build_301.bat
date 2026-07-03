@echo off
REM Build documents

pushd %~dp0

call .venv\Scripts\activate.bat

set SOURCEDIR=source/3.1
set BUILDDIR=docs/docs/3.1
call make.bat html

call .venv\Scripts\deactivate.bat

popd

pause
