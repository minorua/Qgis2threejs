# -*- coding: utf-8 -*-
# (C) 2016 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later
# begin: 2016-02-10

from PyQt6.QtNetwork import QLocalServer

from .localsocketinterface import LocalSocketInterface
from ...utils.logging import logger


class SocketServer(LocalSocketInterface):

    def __init__(self, parent, serverName):
        LocalSocketInterface.__init__(self, parent, serverName)

        self.server = QLocalServer(parent)
        self.server.newConnection.connect(self._onNewConnection)
        if not self.server.listen(serverName):
            logger.error("Failed to start local socket server.")
            return

        logger.debug(f'Server is listening on "{serverName}".')

    def teardown(self):
        self.server.close()

    def _onNewConnection(self):
        logger.debug("New connection.")

        sock = self.server.nextPendingConnection()
        if not sock:
            return

        sock.disconnected.connect(sock.deleteLater)
        sock.waitForReadyRead()
        data = sock.readAll().data()

        if data.startswith(f"Hello {self.serverName}!".encode("utf-8")):
            self.sock = sock
            self.sock.readyRead.connect(self.handleIncomingMessage)
            self.sock.disconnected.connect(self._onDisconnected)
            self.connected.emit()
            logger.debug("Connection established.")
        else:
            sock.disconnectFromServer()
            logger.error("Connection refused.")

    def _onDisconnected(self):
        logger.debug("Disconnected.")
        self.sock = None
        self.disconnected.emit()
