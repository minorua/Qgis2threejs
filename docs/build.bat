@echo off
rem build.bat
rem begin: 2015-09-22
rem usage
rem 1. build English html pages
rem   build
rem 2. build Japanese html pages
rem   build ja

set PATH=%PATH%;C:\Python38\Scripts
set READTHEDOCS=Local

set BUILD_LANG=%1

if "%BUILD_LANG%"=="" set BUILD_LANG=en
if "%BUILD_LANG%"=="en" (
  set SPHINXOPTS=
) else (
  sphinx-intl build -c source\conf.py
  set SPHINXOPTS=-D language=%BUILD_LANG%
)

echo cleaning...
call make clean
echo building html files...
call make html

echo opening the index.html...
build\html\index.html

pause
