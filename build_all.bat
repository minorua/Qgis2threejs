@echo off
REM Build documents

pushd %~dp0

call .venv\Scripts\activate.bat

set SOURCEDIR=source/2.8
set BUILDDIR=docs/docs/2.8
call make.bat html

set SOURCEDIR=source/2.9
set BUILDDIR=docs/docs/2.9
call make.bat html

call .venv\Scripts\deactivate.bat

popd
