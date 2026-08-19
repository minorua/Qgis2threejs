# -*- coding: utf-8 -*-
# (C) 2016 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later
# begin: 2016-02-10

import logging

from PyQt6.QtNetwork import QLocalSocket

from .localsocketinterface import LocalSocketInterface
from ...conf import PLUGIN_NAME

logger = logging.getLogger(PLUGIN_NAME)


class SocketClient(LocalSocketInterface):

    def __init__(self, parent, serverName):
        LocalSocketInterface.__init__(self, parent, serverName)

        self.sock = QLocalSocket(parent)
        self.sock.readyRead.connect(self.handleIncomingMessage)
        self.sock.disconnected.connect(self.disconnected)

    def connect(self):
        self.sock.connectToServer(self.serverName)

        logger.info(f"Connecting to {self.serverName}...")
        if self.sock.waitForConnected(1000):
            logger.info("Connected.")
            self.sock.write(f"Hello {self.serverName}!".encode("utf-8"))
            self.sock.flush()
            self.sock.waitForBytesWritten(1000)
            self.connected.emit()
            return True

        logger.error("Could not connect to SocketServer.")
        return False
