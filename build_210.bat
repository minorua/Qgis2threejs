@echo off
REM Build documents

pushd %~dp0

call .venv\Scripts\activate.bat

set SOURCEDIR=source/2.10
set BUILDDIR=docs/docs/2.10
call make.bat html

call .venv\Scripts\deactivate.bat

popd

pause
