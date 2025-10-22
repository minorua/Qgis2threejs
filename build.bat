@echo off
REM Build documents

pushd %~dp0

call .venv\Scripts\activate.bat

call make.bat html

call .venv\Scripts\deactivate.bat

popd
