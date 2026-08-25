# -*- coding: utf-8 -*-
# (C) 2026 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later

from qgis.PyQt.QtCore import QObject, QSize, QTimer, QUrl, pyqtSignal

from .utils import logger
from .webviewcommon import Q3DWebViewCommon
from .webviewproxy import Q3DWebPageProxy
from ..ipc.ipc_const import Command, Event, Request
from ..ipc.websocketserver import WebSocketServer
from ...utils.basic import pluginDir
from ...utils.gui import openUrl


# grace period to wait for a reconnection (e.g. browser page reload) before treating the preview as closed
RECONNECT_GRACE_MS = 3000


class Q3DWebBrowserProxy(Q3DWebViewCommon, QObject):
    """External web browser preview"""

    def __init__(self, parent):
        QObject.__init__(self, parent)
        Q3DWebViewCommon.__init__(self, parent)

        self._reconnectTimer = QTimer(self)
        self._reconnectTimer.setSingleShot(True)
        self._reconnectTimer.timeout.connect(self.closed)

        self.socketServer = WebSocketServer(self, pluginDir("web"))
        self.socketServer.connected.connect(self._reconnectTimer.stop)
        self.socketServer.disconnected.connect(self._disconnected)

        self._page = Q3DWebPageProxy(self)
        self._page.setObjectName("WebPageProxy")
        self._page.setSocketServer(self.socketServer)

    def teardown(self):
        logger.debug("Preview HTTP/WebSocket server is going to shut down.")
        self._reconnectTimer.stop()
        self.stopPreview()
        self.socketServer.teardown()

        Q3DWebViewCommon.teardown(self)

    def size(self):
        return QSize()

    def getSizeAsync(self, callback):
        self.socketServer.sendRequest(Request.SIZE, callback=callback)

    def startPreview(self):
        url = self.socketServer.url("/preview.html")
        logger.info(f"Opening preview in web browser: {url}")

        if not openUrl(QUrl(url)):
            logger.error("Failed to open a web browser for the preview.")

    def stopPreview(self):
        self.socketServer.closeActiveWebSocket()

    def showDevTools(self):
        self._page.showStatusMessage("Please open the developer tools in the external browser.", 5000)

    def _disconnected(self):
        logger.debug("Preview browser disconnected.")
        self._reconnectTimer.start(RECONNECT_GRACE_MS)
