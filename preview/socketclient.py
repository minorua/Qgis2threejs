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
from PyQt6.QtCore import qDebug
from PyQt6.QtNetwork import QLocalSocket

from .socketinterface import SocketInterface
from .utils import logger


class SocketClient(SocketInterface):

    def __init__(self, serverName, parent=None):
        SocketInterface.__init__(self, serverName, parent=parent)

        socket = QLocalSocket(parent)
        socket.readyRead.connect(self.receiveMessage)
        socket.connectToServer(serverName)
        logger.info(f"Connecting to {serverName}...")
        if socket.waitForConnected(1000):
            logger.info("Connected.")
            socket.write(f"Hello {serverName}!".encode("utf-8"))
            socket.flush()
            socket.waitForBytesWritten(1000)
            logger.debug("A greeting sent.")
            self.conn = socket
        else:
            logger.error("Could not connect to SocketServer.")

    def nextMemoryKey(self):
        return SocketInterface.nextMemoryKey(self) + "C"
