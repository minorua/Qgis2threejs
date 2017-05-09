@echo off
set PYTHONHOME=
if "%1"=="-p" (
  set PROCESSID=%2
) else (
  tasklist /fi "imagename eq qgis*"
  set /p PROCESSID="Input the process ID of QGIS to associate with..."
)

cd /d C:\Python34
python.exe %~dp0q3dapplication.py -p %PROCESSID%
pause
