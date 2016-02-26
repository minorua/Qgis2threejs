# -*- coding: utf-8 -*-
"""
/***************************************************************************
 SocketClient

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
from PyQt5.QtNetwork import QLocalSocket

from socketinterface import SocketInterface


class SocketClient(SocketInterface):

  def __init__(self, serverName, parent=None):
    SocketInterface.__init__(self, serverName, parent=parent)

    socket = QLocalSocket(parent)
    socket.readyRead.connect(self.receiveMessage)
    socket.connectToServer(serverName)
    if socket.waitForConnected(1000):
      socket.write(b"Hello Qgis2threejs!")
      socket.flush()
      socket.waitForBytesWritten(1000)
      self.conn = socket
    else:
      self.log("Could not connect to SocketServer. Please specify the correct QGIS process ID (-p argument). Enter 'ps -A' to know the process ID.")

  def nextMemoryKey(self):
    return SocketInterface.nextMemoryKey(self) + "C"

  def log(self, msg):
    print(msg)
