# -*- coding: utf-8 -*-
"""
/***************************************************************************
 SocketServer

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
from PyQt5.QtNetwork import QLocalServer

from .socketinterface import SocketInterface


class SocketServer(SocketInterface):

  def __init__(self, serverName, parent=None):
    SocketInterface.__init__(self, serverName, parent=parent)

    self.server = QLocalServer(parent)
    self.server.listen(serverName)
    self.server.newConnection.connect(self.newConnection)

  def nextMemoryKey(self):
    return SocketInterface.nextMemoryKey(self) + "S"

  def newConnection(self):
    conn = self.conn
    if not conn:
      conn = self.server.nextPendingConnection()
      conn.disconnected.connect(conn.deleteLater)

    conn.waitForReadyRead()
    data = conn.readAll().data().decode()
    if not self.conn and data == "Hello {0}!".format(self.serverName).encode("utf-8"):
        self.conn = conn
        self.conn.readyRead.connect(self.receiveMessage)
        self.conn.disconnected.connect(self.connDisconnected)
        self.log("Connection established.")
    else:
      conn.disconnectFromServer()
      self.log("Connection refused.")

  def connDisconnected(self):
    self.conn = None
