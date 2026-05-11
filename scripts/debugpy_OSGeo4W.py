""" This is a script to enable debugging a QGIS plugin with VS Code. """

import debugpy    # https://github.com/microsoft/debugpy

debugpy.configure(python="C:/OSGeo4W/bin/python3.exe")

port = 5678
debugpy.listen(port)
