# -*- coding: utf-8 -*-
# (C) 2026 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later

import json
import os
import subprocess

from qgis.PyQt.QtCore import QObject, QSize, QProcess, QUrl, pyqtSignal
from qgis.PyQt.QtWidgets import QMessageBox

from .const import PreviewState, WebViewMode
from .utils import logger
from .webbridge import WebIPCBridge
from .webviewcommon import Q3DWebPageCommon, Q3DWebViewCommon
from ..ipc.ipc_const import Event, Request
from ..ipc.socketserver import SocketServer
from ...conf import DEBUG_MODE, PLUGIN_NAME
from ...utils.basic import createUid, pluginDir


USE_QPROCESS = True


class SendQueueProxy:

    def __init__(self, bridge):
        pass

    def setSocketServer(self, server):
        self.socketServer = server

    def append(self, data):
        self.socketServer.request(Request.LOAD_DATA, params={
            "data": data,
            "viaQueue": True
        })

    def removeLayer(self, jsLayerId):
        self.socketServer.request(Request.REMOVE_LAYER_DATA, params={"jsLayerId": jsLayerId})

    def clear(self):
        self.socketServer.request(Request.CLEAR_QUEUE)

    def dataLoaded(self):
        pass

    def __len__(self):
        return 0


class Q3DWebPageProxy(Q3DWebPageCommon, QObject):

    BridgeClass = WebIPCBridge
    SendQueueClass = SendQueueProxy

    # QWebEnginePage signals
    loadStarted = pyqtSignal()
    loadFinished = pyqtSignal(bool)

    def __init__(self, parent=None):
        QObject.__init__(self, parent)
        Q3DWebPageCommon.__init__(self, parent)

        url = pluginDir("web/viewer/webengine.html").replace("\\", "/")
        self.myUrl = QUrl.fromLocalFile(url)

    def setSocketServer(self, server):
        self.socketServer = server
        self.socketServer.notified.connect(self.notified)
        self.socketServer.requestReceived.connect(self.requestReceived)
        self.socketServer.responseReceived.connect(self.responseReceived)

        self.sendQueue.setSocketServer(server)

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
        if callback:
            def _callback(msg):
                callback(msg.get("params", {}).get("result"))
        else:
            _callback = None

        self.socketServer.request(Request.RUN_SCRIPT, params={"script": string}, callback=_callback)

    def sendData(self, data, viaQueue=False):
        logger.debug("Sending {} data to web page...".format(data.get("type")))

        self.socketServer.request(Request.LOAD_DATA, params={
            "data": data,
            "viaQueue": viaQueue
        })

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

    def __init__(self, parent):
        QObject.__init__(self, parent)
        Q3DWebViewCommon.__init__(self, parent)

        self.embeddedMode = True
        self.previewEnabled = True
        self.viewProcess = None
        self.previewWndGeometry = {}

        self.serverName = "Q3D" + createUid()
        self.socketServer = SocketServer(self, self.serverName)
        self.socketServer.notified.connect(self.notified)
        self.socketServer.disconnected.connect(self.disconnected)

        self._page = Q3DWebPageProxy(self)
        self._page.setObjectName("WebPageProxy")
        self._page.setSocketServer(self.socketServer)

    def setup(self, webViewMode=None, enabledAtStart=True):
        Q3DWebViewCommon.setup(self, webViewMode, enabledAtStart)

        self.embeddedMode = (webViewMode == WebViewMode.EMBEDDED)
        self.previewEnabled = enabledAtStart
        if enabledAtStart:
            self.startPreview()

    def teardown(self):
        logger.debug("Socket server is going to shut down.")
        self.stopPreview()

        Q3DWebViewCommon.teardown(self)

    def size(self):
        return self.parent().size() if self.embeddedMode else QSize()

    def getSizeAsync(self, callback):
        self.socketServer.request(Request.SIZE, callback=callback)

    def startPreview(self):
        self.previewStateChanged.emit(PreviewState.Loading)

        if self.viewProcess:
            self.stopPreview()

        logger.info("Launching preview...")

        args = []
        if os.name == "nt":
            if DEBUG_MODE and self.embeddedMode and not USE_QPROCESS:
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

        if self.previewWndGeometry:
            args += [
                "--x", str(self.previewWndGeometry["x"]),
                "--y", str(self.previewWndGeometry["y"]),
                "--width", str(self.previewWndGeometry["width"]),
                "--height", str(self.previewWndGeometry["height"])
            ]

        if not self.embeddedMode:
            args.append("-f")

        cwd = os.path.dirname(pluginDir())

        if USE_QPROCESS:
            self.viewProcess = QProcess(self)
            self.viewProcess.finished.connect(self.viewProcessFinished)

            self.viewProcess.setWorkingDirectory(cwd)
            self.viewProcess.start(args[0], args[1:])
            return

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

    def viewProcessFinished(self, exitCode, exitStatus):
        if exitCode not in (0, 15):
            msg = f"""Exit code: {exitCode}
Exit status: {exitStatus}

"""
            msg += bytes(self.viewProcess.readAllStandardError()).decode("utf-8", "replace")
            QMessageBox.critical(None, f"{PLUGIN_NAME} Preview Error", msg)

    def stopPreview(self):
        if not self.viewProcess:
            return

        self.previewStateChanged.emit(PreviewState.Disabled)

        self.socketServer.notify(Event.QUIT)

        self.terminateViewProcess()

    def terminateViewProcess(self):
        if not self.viewProcess:
            return

        try:
            if USE_QPROCESS:
                self.viewProcess.terminate()
                self.viewProcess.waitForFinished(3000)

                self.viewProcess.finished.disconnect()
            else:
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
            self.stopPreview()

    def showDevTools(self):
        self.socketServer.notify(Event.DEV_TOOLS)

    def showGPUInfo(self):
        self.socketServer.notify(Event.GPU_INFO)

    def triggerTestClick(self, pos):
        self.socketServer.notify(Event.CLICK, params={"x": pos.x(), "y": pos.y()})

    def notified(self, method, params, payload):
        if method == Event.WND_GEOM_CHANGED:
            self.previewWndGeometry = params

        elif method == Event.PY_ERROR:
            logger.error(params["msg"])

        elif method == Event.DEV_TOOLS_CLOSED:
            self.devToolsClosed.emit()

    def disconnected(self):
        logger.debug("Disconnected from preview process.")
        if self.embeddedMode and self.previewEnabled:
            self.previewStateChanged.emit(PreviewState.Error)
            self.terminateViewProcess()
