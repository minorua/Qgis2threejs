@echo off
rem Launch a simple web browser built with PyQt6 and QWebEngineView.
pushd "%~dp0"

call env.bat
start pythonw web_browser.py %*

popd
