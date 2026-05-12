# -*- coding: utf-8 -*-
# (C) 2026 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later

import json
import os
import subprocess

from qgis.PyQt.QtCore import QObject, QSize, QUrl, pyqtSignal

from .conf import DEBUG_MODE
from .const import PreviewState, WebViewType, WebViewMode
from .utils import logger, web_logger
from .webbridge import WebIPCBridge
from .webviewcommon import Q3DWebPageCommon, Q3DWebViewCommon
from ..ipc.ipc_const import Event, Request
from ..ipc.socketserver import SocketServer
from ...utils.basic import createUid, pluginDir, NoopClass


class Q3DWebPageProxy(Q3DWebPageCommon, QObject):

    BridgeClass = WebIPCBridge

    # QWebEnginePage signals
    loadStarted = pyqtSignal()
    loadFinished = pyqtSignal(bool)

    def __init__(self, parent=None):
        QObject.__init__(self, parent)
        Q3DWebPageCommon.__init__(self, parent)

        self.isWebEnginePage = True

        url = pluginDir("web/viewer/webengine.html").replace("\\", "/")
        self.myUrl = QUrl.fromLocalFile(url)

    def setSocketServer(self, server):
        self.socketServer = server
        self.socketServer.notified.connect(self.notified)
        self.socketServer.requestReceived.connect(self.requestReceived)
        self.socketServer.responseReceived.connect(self.responseReceived)

    def notified(self, method, params, payload):
        if method == Event.METHOD_INVOKED:
            func = getattr(self.bridge, params["name"])
            func(*params["args"])

        elif method == Event.PAGE_LOAD_STARTED:
            self.loadStarted.emit()

        elif method == Event.PAGE_LOADED:
            self.loadFinished.emit(params.get("ok", False))

        elif method == Event.JS_ERROR_WARNING:
            self.jsErrorWarning.emit(params.get("is_error", False))

    def requestReceived(self, id, method, params, payload):
        pass

    def responseReceived(self, id, method, params, payload):
        pass

    def reload(self):
        self.showStatusMessage("Initializing preview in an external process...")
        self.socketServer.request(Request.RELOAD)

    def url(self):
        return self.myUrl

    def runJavaScript(self, string, callback=None):
        self.socketServer.request(Request.RUN_SCRIPT, params={"script": string}, callback=callback)

    def sendData(self, data, viaQueue=False):
        logger.debug("Sending {} data to web page...".format(data.get("type", "unknown")))

        params = {
            "data": data,
            "viaQueue": viaQueue
        }
        self.socketServer.request(Request.LOAD_DATA, params=params)

        return

        # use shared memory
        b = json.dumps(data).encode("utf-8")
        size = len(b)
        logger.debug(f"Data size: {size:,}")

        params = {"viaQueue": viaQueue}
        if size < 4000:
            params["data"] = data
            payload = None
        else:
            payload = b

        self.socketServer.request(Request.LOAD_DATA, params=params, payload=payload)


class Q3DWebViewProxy(Q3DWebViewCommon, QObject):

    WebViewType = WebViewType.WEBENGINE

    def __init__(self, parent):
        QObject.__init__(self, parent)
        Q3DWebViewCommon.__init__(self, parent)

        self.embeddedMode = True
        self.previewEnabled = True
        self.viewProcess = None
        self.viewContainer = NoopClass()

        self.serverName = "Q3D" + createUid()
        self.socketServer = SocketServer(self, self.serverName)
        self.socketServer.notified.connect(self.notified)
        self.socketServer.requestReceived.connect(self.requestReceived)
        self.socketServer.disconnected.connect(self.disconnected)

        self._page = Q3DWebPageProxy(self)
        self._page.setObjectName("WebPageProxy")
        self._page.setSocketServer(self.socketServer)

    def setup(self, webViewMode=None, enabledAtStart=True):
        self._page.setup()

        if webViewMode == WebViewMode.EMBEDDED:
            self.viewContainer = self.parent()
        else:   # webViewMode == WebViewMode.SEPARATE:
            self.embeddedMode = False

        self.setPreviewEnabled(enabledAtStart)

    def teardown(self):
        logger.info("Socket server is going to shut down.")
        self.stopPreview()
        self.viewContainer = None
        self._page = None

    def page(self):
        return self._page

    def size(self):
        return self.parent().size() if self.embeddedMode else QSize()

    def getSizeAsync(self, callback):
        self.socketServer.request(Request.SIZE, callback=callback)

    def startPreview(self):
        self.viewContainer.showPreviewState(PreviewState.State_Loading)

        if self.viewProcess:
            self.stopPreview()

        logger.info("Launching preview...")

        args = []
        if os.name == "nt":
            if DEBUG_MODE and self.embeddedMode:
                args += [
                    pluginDir("scripts", "pause_on_error.bat"),
                    "python"
                ]
            else:
                args.append("pythonw")

        if not args:
            args.append("python3")

        args += [
            "-m", "Qgis2threejs.gui.webview.app",
            "-s", self.serverName,
            "-p", str(os.getpid())
        ]

        if not self.embeddedMode:
            args.append("-f")

        cwd = os.path.dirname(pluginDir())

        # env = os.environ.copy()
        # env["PYTHONPATH"] = os.pathsep.join(sys.path)
        # del env["QT3D_RENDERER"]
        # env["QTWEBENGINE_CHROMIUM_FLAGS"] = "--enable-logging --v=1"

        if hasattr(subprocess, "STARTUPINFO"):
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

            if self.embeddedMode:
                startupinfo.wShowWindow = 6  # SW_MINIMIZE
            else:
                startupinfo.wShowWindow = 1  # SW_SHOWNORMAL
        else:
            startupinfo = None

        self.viewProcess = subprocess.Popen(args, cwd=cwd, startupinfo=startupinfo)        # env=env

    def stopPreview(self):
        if not self.viewProcess:
            return

        self.socketServer.notify(Event.QUIT)

        self.viewContainer.removeEmbeddedWnd()

        try:
            self.viewProcess.terminate()
            self.viewProcess.wait(timeout=3)

        # except ProcessLookupError:
        # except subprocess.TimeoutExpired:
        finally:
            self.viewProcess = None

    def setPreviewEnabled(self, enabled):
        self.previewEnabled = enabled
        if enabled:
            self.startPreview()
        else:
            self.viewContainer.showPreviewState(PreviewState.State_Disabled)
            self.stopPreview()

    def showDevTools(self):
        self.socketServer.notify(Event.DEV_TOOLS)

    def showGPUInfo(self):
        self.socketServer.notify(Event.GPU_INFO)

    def triggerTestClick(self, pos):
        self.socketServer.notify(Event.CLICK, params={"x": pos.x(), "y": pos.y()})

    def notified(self, method, params, payload):
        if method == Event.PY_ERROR:
            logger.error(params["msg"])

        elif method == Event.DEV_TOOLS_CLOSED:
            self.devToolsClosed.emit()

    def requestReceived(self, id, method, params, payload):
        if method == Request.EMBED_WND:
            self.viewContainer.embedWnd(int(params["winId"]))
        else:
            return

        self.socketServer.respond(id, method)

    def disconnected(self):
        logger.info("Disconnected from preview process.")
        if self.embeddedMode and self.previewEnabled:
            self.viewContainer.showPreviewState(PreviewState.State_Error)
