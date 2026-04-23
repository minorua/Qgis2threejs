# -*- coding: utf-8 -*-
# (C) 2023 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later
# begin: 2023-10-03

import json
import os
import logging
import subprocess

from qgis.PyQt.QtCore import Qt, QEventLoop, QObject, QTimer, QUrl, pyqtSignal
from qgis.PyQt.QtGui import QDesktopServices
from qgis.PyQt.QtWidgets import QDialog, QVBoxLayout, QWidget

from .webbridge import WebBridge
from .webviewcommon import Q3DWebPageCommon, Q3DWebViewCommon, WEBVIEWTYPE_WEBENGINE
from ..conf import DEBUG_MODE
from ..preview.socketserver import SocketServer
from ..utils import createUid, pluginDir
from ..utils.logging import logger, web_logger

TIMEOUT_MS = 30000      # timeout (ms) for script execution and rendering


class WebEngineViewProcessBridge(WebBridge):
    pass


class Q3DExternalWebPage(QObject):       # (Q3DWebPageCommon):

    jsErrorWarning = pyqtSignal(bool)       # bool: is_error

    # for compatibility
    loadStarted = pyqtSignal()
    loadFinished = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.bridge = WebEngineViewProcessBridge(self)

        self.isWebEnginePage = True

    def setup(self):
        pass

    def reload(self):
        self.showStatusMessage("Initializing preview...")
        # TODO: IPC
        # self.setUrl(self.myUrl)

    def runScript(self, string, message="", sourceID="webengineview.py", callback=None, wait=False):
        """
        Run a JavaScript script in the web view with optional data and callback.
        Args:
            string (str): The JavaScript code string to execute.
            message (str, optional): A descriptive message for logging purposes.
            sourceID (str, optional): Identifier for the source of the script.
            callback (optional): Callback function to be executed after script runs.
            wait (bool, optional): Whether to wait for script execution to complete.
        """
        self.logScriptExecution(string, message, sourceID)

        # TODO: IPC
        return

        if not wait:
            if callback:
                self.runJavaScript(string, callback)
            else:
                self.runJavaScript(string)
            return

        loop = QEventLoop()
        timer = QTimer()
        timer.setSingleShot(True)
        timer.timeout.connect(loop.quit)

        finished = False
        result = None
        def runJavaScriptCallback(res):
            nonlocal finished, result
            finished = True
            result = res
            loop.quit()

        self.runJavaScript(string, runJavaScriptCallback)

        timer.start(TIMEOUT_MS)
        loop.exec()

        if not finished:
            logger.warning(f"JavaScript execution timed out: {string}")

        if callback:
            callback(result)

        return result

    def sendData(self, data, viaQueue=False):
        logger.debug("Sending {} data to web page...".format(data.get("type", "unknown")))

        # TODO: IPC
        return
        self.bridge.sendData.emit(data, viaQueue)

    def requestRendering(self, waitUntilFinished=False):
        # TODO: IPC
        return
        def render():
            self.runScript("requestRendering()")

        if waitUntilFinished:
            loop = QEventLoop()
            self.bridge.requestedRenderingFinished.connect(loop.quit)

            timer = QTimer()
            timer.setSingleShot(True)
            timer.timeout.connect(loop.quit)

            render()

            timer.start(TIMEOUT_MS)
            loop.exec()
        else:
            render()

    def logToConsole(self, message, level="debug"):
        if level not in ["debug", "info", "warn", "error"]:
            level = "log"

        if level in ["warn", "error"]:
            self.jsErrorWarning.emit(bool(level == "error"))

        msg = json.dumps(message.replace('\n', '\\n'))      # new line causes issues in console

        self.runJavaScript(f"console.{level}({msg});")

    def javaScriptConsoleMessage(self, level, message, lineNumber, sourceID):
        # TODO: move to external view page and IPC
        return
        CML = QWebEnginePage.JavaScriptConsoleMessageLevel
        if level in (CML.WarningMessageLevel, CML.ErrorMessageLevel):
            self.jsErrorWarning.emit(bool(level == CML.ErrorMessageLevel))

        if DEBUG_MODE:
            logging_level = {
                CML.InfoMessageLevel: logging.INFO,
                CML.WarningMessageLevel: logging.WARNING,
                CML.ErrorMessageLevel: logging.ERROR
            }.get(level, logging.DEBUG)

            text = message
            if sourceID:
                text += f"\t({sourceID.split('/')[-1]}:{lineNumber})"

            web_logger.log(logging_level, text)

    def acceptNavigationRequest(self, url, type, isMainFrame):
        # TODO: move to external view page
        return
        if type == QWebEnginePage.NavigationType.NavigationTypeLinkClicked:
            QDesktopServices.openUrl(url)
            return False
        return True

    def runJavaScript(self, string, callback=None):
        logger.info(f"[RUN] {string} callback={callback}")


class Q3DExternalWebView(QWidget, Q3DWebViewCommon):

    # TODO: fileDropped - IPC

    def __init__(self, parent):
        QWidget.__init__(self, parent)
        Q3DWebViewCommon.__init__(self)
        self.webViewType = WEBVIEWTYPE_WEBENGINE

        self._page = Q3DExternalWebPage(self)

    def setup(self, enabled=True, webViewMode=None):
        Q3DWebViewCommon.setup(self, enabled, webViewMode)

        self.serverName = "Q3D" + createUid()
        self.socketServer = SocketServer(self.serverName, self)
        self.socketServer.notified.connect(self.notified)
        self.socketServer.requestReceived.connect(self.requestReceived)
        self.socketServer.responseReceived.connect(self.responseReceived)
        self.socketServer.connected.connect(self.requestWinId)

        logger.info("Launching preview...")
        pid = os.getpid()
        cwd = os.path.dirname(pluginDir())

        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = 6  # SW_MINIMIZE

        subprocess.Popen([
            "python",      # "pythonw"
            "-m", "Qgis2threejs.preview.view",
            "-s", self.serverName,
            "-p", str(pid)
        ], cwd=cwd, startupinfo=startupinfo)

    def teardown(self):
        self.socketServer.notify({"name": "quit"})
        logger.info("Server closed.")

    def requestWinId(self):
        self.socketServer.request({"name": "winId"})

    def notified(self, params):
        logger.info(f"Notification received: {params}")

        if params.get("name") == "winId":       # TODO: move to responseReceived (dataType = json or dict)
            self.socketServer.responseReceived.emit(str(params.get("value")).encode("ascii"), {"type": "winId", "dataType": "json"})

            # TODO: responseReceived (params, binary)

        # code = params.get("code")
        # if code == q3dconst.N_CANVAS_EXTENT_CHANGED:

    def requestReceived(self, params):
        pass

    def responseReceived(self, data, meta):
        pass

    def showDevTools(self):
        # TODO: IPC
        return
        if self._page.devToolsPage():
            self.dlg.activateWindow()
            return

        dlg = self.dlg = QDialog(self)
        dlg.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        dlg.resize(800, 500)
        dlg.setWindowTitle("Qgis2threejs Developer Tools")
        dlg.rejected.connect(self.devToolsClosed)

        ins = QWebEngineView(dlg)
        self._page.setDevToolsPage(ins.page())

        v = QVBoxLayout()
        v.setContentsMargins(0, 0, 0, 0)
        v.addWidget(ins)

        dlg.setLayout(v)
        dlg.show()

    def showGPUInfo(self):
        # TODO: IPC
        return
        self.load(QUrl("chrome://gpu"))

    def page(self):
        return self._page

    def setAcceptDrops(self, _b):
        pass
