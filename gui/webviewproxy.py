# -*- coding: utf-8 -*-
# (C) 2026 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later

import json
import os
import subprocess

from qgis.PyQt.QtCore import Qt, QObject, QTimer, QUrl, pyqtSignal
from qgis.PyQt.QtGui import QPalette, QPixmap, QWindow
from qgis.PyQt.QtWidgets import QPushButton, QLabel, QStackedLayout, QVBoxLayout, QWidget

from .webbridge import WebIPCBridge
from .webenginecommon import Q3DWebEnginePageCommon, Q3DWebEngineViewCommon
from .webview import WVM_EXTERNAL_WINDOW
from ..conf import DEBUG_MODE
from ..preview.ipc_const import Event, Request
from ..preview.socketserver import SocketServer
from ..utils import createUid, pluginDir
from ..utils.logging import logger, web_logger

TIMEOUT_MS = 30000      # timeout (ms) for script execution and rendering


class Q3DWebPageProxy(Q3DWebEnginePageCommon, QObject):

    BridgeClass = WebIPCBridge

    jsErrorWarning = pyqtSignal(bool)       # is_error

    # QWebEnginePage signals
    loadStarted = pyqtSignal()
    loadFinished = pyqtSignal(bool)

    def __init__(self, parent=None):
        QObject.__init__(self, parent)
        Q3DWebEnginePageCommon.__init__(self)

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


class Q3DWebViewProxy(Q3DWebEngineViewCommon, QWidget):

    # TODO: fileDropped - IPC

    def __init__(self, parent):
        QWidget.__init__(self, parent)
        Q3DWebEngineViewCommon.__init__(self, parent)

        self.embeddedMode = True
        self.viewProcess = None
        self.previewWnd = None

        self.serverName = "Q3D" + createUid()
        self.socketServer = SocketServer(self, self.serverName)
        self.socketServer.notified.connect(self.notified)
        self.socketServer.requestReceived.connect(self.requestReceived)
        self.socketServer.disconnected.connect(self.disconnected)

        self._page = Q3DWebPageProxy(self)
        self._page.setSocketServer(self.socketServer)

        self.previewStateWidget = PreviewStateWidget(self)
        self.previewStateWidget.buttonRestart.clicked.connect(self.startPreview)

        self.stackedLayout = QStackedLayout(self)
        self.stackedLayout.addWidget(self.previewStateWidget)

    def page(self):
        return self._page

    def setup(self, webViewMode=None, enabledAtStart=True):
        Q3DWebEngineViewCommon.setup(self, webViewMode, enabledAtStart)

        if webViewMode == WVM_EXTERNAL_WINDOW:
            self.embeddedMode = False

        self.setPreviewEnabled(enabledAtStart)

    def teardown(self):
        logger.info("Socket server is going to shut down.")
        self.stopPreview()

    def startPreview(self):
        self.stackedLayout.setCurrentIndex(0)

        if self.viewProcess:
            self.stopPreview()

        logger.info("Launching preview...")
        self.previewStateWidget.setState(PreviewStateWidget.State_Loading)

        args = []
        if os.name == "nt":
            if DEBUG_MODE:
                args += [
                    pluginDir("scripts", "pause_on_error.bat"),
                    "python"
                ]
            else:
                args.append("pythonw")

        if not args:
            args.append("python3")

        args += [
            "-m", "Qgis2threejs.preview.view",
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
        self.socketServer.notify(Event.QUIT)

        if self.previewWnd:
            self.previewWnd.hide()
            self.previewWnd.setParent(None)
            self.previewWnd = None

        if self.viewProcess:
            try:
                self.viewProcess.terminate()
                self.viewProcess.wait(timeout=3)

            # except ProcessLookupError:
            # except subprocess.TimeoutExpired:
            finally:
                self.viewProcess = None

    def setPreviewEnabled(self, enabled):
        if enabled:
            self.startPreview()
        else:
            self.previewStateWidget.setState(PreviewStateWidget.State_Disabled)
            self.stackedLayout.setCurrentIndex(0)
            self.stopPreview()

    # TODO:
    def setAcceptDrops(self, _b):
        pass

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
            winId = int(params["winId"])
            self.previewWnd = QWindow.fromWinId(winId)
            container = QWidget.createWindowContainer(self.previewWnd)

            w = self.stackedLayout.widget(1)
            if w:
                w.hide()
                self.stackedLayout.removeWidget(w)

            self.stackedLayout.addWidget(container)
            self.stackedLayout.setCurrentIndex(1)

            logger.info(f"External window ({winId}) embedded.")
            self.previewStateWidget.setState(PreviewStateWidget.State_Idle)
        else:
            return

        self.socketServer.respond(id, method)

    def disconnected(self):
        logger.info("Disconnected from preview process.")
        if self.previewStateWidget.currentState != PreviewStateWidget.State_Disabled:
            self.previewStateWidget.setState(PreviewStateWidget.State_Error)
        self.stackedLayout.setCurrentIndex(0)


class PreviewStateWidget(QWidget):

    State_Idle = 0
    State_Loading = 1
    State_Error = 2
    State_Disabled = 3

    def __init__(self, parent):
        QWidget.__init__(self, parent)

        self.setAutoFillBackground(True)

        self.msg1 = QLabel(self)
        self.msg1.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.msg2 = QLabel(self)
        self.msg2.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.buttonRestart = QPushButton(self)
        self.buttonRestart.setText("RESTART PREVIEW")
        self.buttonRestart.setStyleSheet("padding: 6px 12px;")
        self.buttonRestart.hide()

        self.icon = QLabel(self)
        self.icon.setPixmap(QPixmap(pluginDir("Qgis2threejs.png")))
        self.icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon.setDisabled(True)
        self.icon.hide()

        layout = QVBoxLayout()
        layout.addStretch(1)
        layout.addWidget(self.msg1)
        layout.addWidget(self.msg2)
        layout.addStretch(1)
        layout.addWidget(self.buttonRestart, 0, Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(self.icon)
        layout.addStretch(3)

        self.setLayout(layout)

        self.timer = QTimer(self)
        self.timer.setInterval(100)
        self.timer.timeout.connect(self.timeout)

        self.currentMsg1 = self.currentMsg2 = ""
        self.currentState = PreviewStateWidget.State_Idle
        self.dots = 0

    def setState(self, state):
        self.timer.stop()
        self.buttonRestart.hide()
        self.icon.hide()

        msg1 = msg2 = ""
        bgcolor = None
        if state == PreviewStateWidget.State_Loading:
            msg1 = "PREPARING PREVIEW"
            bgcolor = Qt.GlobalColor.white

            self.dots = 0
            self.timer.start()

        elif state == PreviewStateWidget.State_Error:
            msg1 = "PREVIEW STOPPED UNEXPECTEDLY.\nTHE CONNECTION WAS LOST."
            self.buttonRestart.show()

        elif state == PreviewStateWidget.State_Disabled:
            self.icon.show()

        if bgcolor is None:
            bgcolor = self.palette().color(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Button)

        self.msg1.setText(msg1)
        self.msg2.setText(msg2)
        self.setBackgroundColor(bgcolor)

        self.currentState = state
        self.currentMsg1 = msg1
        self.currentMsg2 = msg2

    def timeout(self):
        self.dots = (self.dots + 1) % 4

        dots = "." * self.dots + " " * (3 - self.dots)
        self.msg1.setText(self.currentMsg1 + " " + dots)

    def setBackgroundColor(self, color):
        pal = self.palette()
        pal.setColor(QPalette.ColorRole.Window, color)
        self.setPalette(pal)
