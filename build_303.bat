@echo off
REM Build documents

pushd %~dp0

call .venv\Scripts\activate.bat

set SOURCEDIR=source/3.3
set BUILDDIR=docs/docs/3.3
call make.bat html

call .venv\Scripts\deactivate.bat

popd

pause
