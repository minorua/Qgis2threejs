# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Qgis2threejs Live Exporter Application

                              -------------------
        begin                : 2016-02-10
        copyright            : (C) 2016 Minoru Akagi
        email                : akaginch@gmail.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
import sys

from PyQt5.Qt import Qt, QApplication

from q3dwindow import Q3DWindow

isViewer = True
serverName = ""
pid = ""
title = None

i = 1
argv = sys.argv
while i < len(argv):
  arg = argv[i]
  # Live Exporter
  if arg == "-p":
    i += 1
    pid = argv[i]

  # Qgis2threejs Renderer
  elif arg == "-r":
    isViewer = False
  elif arg == "-n":
    i += 1
    serverName = argv[i]
  i += 1

if isViewer:
  serverName = "Qgis2threejsLive" + pid
  if pid:
    print("Process ID specified: {0}".format(pid))
  else:
    print("Process ID not specified. Please specify QGIS process ID (-p argument). Enter 'ps -A' to know the process ID.")

  print("Starting Live Exporter...")

else:
  if serverName:
    print("Server name specified: {0}".format(serverName))
  else:
    print("Server name not specified.")
  print("Starting Qgis2threejs Renderer...")
  title = "Qgis2threejs Renderer"

app = QApplication([])
wnd = Q3DWindow(serverName, isViewer)
if title:
  wnd.setWindowTitle(title)
wnd.show()
if not isViewer:
  wnd.setWindowState(wnd.windowState() | Qt.WindowMinimized)
app.exec_()
