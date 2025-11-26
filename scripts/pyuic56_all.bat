@echo off
call C:\OSGeo4W\bin\o4w_env.bat
path C:\OSGeo4W\apps\qt6\bin;%PATH%;"C:\Program Files\Git\usr\bin"

cd /d %~dp0\..\gui\ui

for %%f in (*.ui) do (
    @echo Processing %%f...
    pyuic6.exe -o %%~nf.py %%f
    sed -i "s/from PyQt6 import/from qgis.PyQt import/g" %%~nf.py
    sed -i "s/QtGui.QAction/QtWidgets.QAction/g" %%~nf.py
)

pause
