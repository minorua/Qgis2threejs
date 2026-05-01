# -*- coding: utf-8 -*-
# (C) 2016 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later
# begin: 2016-02-10

try:
    from PyQt6.QtNetwork import QLocalServer
except ImportError:
    from PyQt5.QtNetwork import QLocalServer

from .socketinterface import SocketInterface
from ..utils import logger


class SocketServer(SocketInterface):

    def __init__(self, parent, serverName):
        SocketInterface.__init__(self, parent, serverName)

        self.server = QLocalServer(parent)
        self.server.newConnection.connect(self.onNewConnection)
        self.server.listen(serverName)

        logger.info(f'Server is listening on "{serverName}".')

    def teardown(self):
        self.server.close()

    def onNewConnection(self):
        logger.debug("New connection.")

        conn = self.server.nextPendingConnection()
        if not conn:
            return

        conn.disconnected.connect(conn.deleteLater)
        conn.waitForReadyRead()
        data = conn.readAll().data()

        if data.startswith(f"Hello {self.serverName}!".encode("utf-8")):
            self.conn = conn
            self.conn.readyRead.connect(self.handleIncomingMessage)
            self.conn.disconnected.connect(self.connDisconnected)
            self.connected.emit()
            logger.info("Connection established.")
        else:
            conn.disconnectFromServer()
            logger.error("Connection refused.")

    def connDisconnected(self):
        logger.info("Disconnected.")
        self.conn = None
        self.disconnected.emit()
