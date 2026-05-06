# -*- coding: utf-8 -*-
# (C) 2016 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later
# begin: 2016-02-10

import logging as logger

from PyQt6.QtNetwork import QLocalSocket

from .socketinterface import SocketInterface


class SocketClient(SocketInterface):

    def __init__(self, parent, serverName):
        SocketInterface.__init__(self, parent, serverName)

        self.conn = QLocalSocket(parent)
        self.conn.readyRead.connect(self.handleIncomingMessage)
        self.conn.disconnected.connect(self.disconnected)

    def connect(self):
        self.conn.connectToServer(self.serverName)

        logger.info(f"Connecting to {self.serverName}...")
        if self.conn.waitForConnected(1000):
            logger.info("Connected.")
            self.conn.write(f"Hello {self.serverName}!".encode("utf-8"))
            self.conn.flush()
            self.conn.waitForBytesWritten(1000)
            self.connected.emit()
            return True

        logger.error("Could not connect to SocketServer.")
        return False
