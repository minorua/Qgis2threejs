# -*- coding: utf-8 -*-
# (C) 2026 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later

from qgis.PyQt.QtCore import QObject, QSize, QUrl

from .const import PreviewState
from .utils import logger
from .webviewcommon import Q3DWebViewCommon
from .webviewproxy import Q3DWebPageProxy
from ..ipc.ipc_const import Command, Event, Request
from ..ipc.websocketserver import WebSocketServer
from ...utils.basic import pluginDir
from ...utils.gui import openUrl


class Q3DWebBrowserProxy(Q3DWebViewCommon, QObject):
    """External web browser preview"""

    def __init__(self, parent):
        QObject.__init__(self, parent)
        Q3DWebViewCommon.__init__(self, parent)

        self.previewEnabled = True

        self.socketServer = WebSocketServer(self, pluginDir("web"))
        self.socketServer.disconnected.connect(self.disconnected)

        self._page = Q3DWebPageProxy(self)
        self._page.setObjectName("WebPageProxy")
        self._page.setSocketServer(self.socketServer)

    def setup(self, webViewMode=None, enabledAtStart=True):
        Q3DWebViewCommon.setup(self, webViewMode, enabledAtStart)

        self.previewEnabled = enabledAtStart
        if enabledAtStart:
            self.startPreview()

    def teardown(self):
        logger.debug("Preview HTTP/WebSocket server is going to shut down.")
        self.stopPreview()
        self.socketServer.teardown()

        Q3DWebViewCommon.teardown(self)

    def size(self):
        return QSize()

    def getSizeAsync(self, callback):
        self.socketServer.sendRequest(Request.SIZE, callback=callback)

    def startPreview(self):
        self.previewStateChanged.emit(PreviewState.Loading)

        url = self.socketServer.url("/preview.html")
        logger.info(f"Opening preview in web browser: {url}")

        if not openUrl(QUrl(url)):
            logger.error("Failed to open a web browser for the preview.")

    def stopPreview(self):
        self.previewStateChanged.emit(PreviewState.Disabled)
        self.socketServer.closeActiveWebSocket()

    def setPreviewEnabled(self, enabled):
        self.previewEnabled = enabled
        if enabled:
            self.startPreview()
        else:
            self.stopPreview()

    def triggerTestClick(self, pos):
        self.socketServer.sendCommand(Command.CLICK, params={"x": pos.x(), "y": pos.y()})

    def disconnected(self):
        logger.debug("Preview browser disconnected.")
