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

from PyQt5.Qt import QApplication

from q3dwindow import Q3DWindow

pid = ""

i = 1
argv = sys.argv
while i < len(argv):
  arg = argv[i]
  if arg == "-p":
    i += 1
    pid = argv[i]
  i += 1

if pid:
  print("Process ID {0} specified.".format(pid))
else:
  print("Process ID not specified. Please specify QGIS process ID (-p argument). Enter 'ps -A' to know the process ID.")


print("Launching Live Exporter...")

app = QApplication([])
wnd = Q3DWindow(pid)
wnd.show()
app.exec_()
