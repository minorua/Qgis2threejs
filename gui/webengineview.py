# -*- coding: utf-8 -*-
# (C) 2023 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later
# begin: 2023-10-03

import os
import logging

from qgis.PyQt.QtCore import PYQT_VERSION_STR, Qt, QEventLoop, QTimer, QUrl, pyqtSignal
from qgis.PyQt.QtGui import QDesktopServices, QImage, QPainter
from qgis.PyQt.QtWidgets import QDialog, QVBoxLayout
from qgis.PyQt.QtWebEngineWidgets import QWebEngineView

if PYQT_VERSION_STR.split(".")[0] == "5":
    from PyQt5.QtWebEngineWidgets import QWebEnginePage, QWebEngineSettings
    from PyQt5.QtWebChannel import QWebChannel
else:
    from PyQt6.QtWebEngineCore import QWebEnginePage, QWebEngineSettings
    from PyQt6.QtWebChannel import QWebChannel

from .webviewcommon import Q3DWebPageCommon, Q3DWebViewCommon
from ..conf import DEBUG_MODE
from ..utils import pluginDir
from ..utils.logging import logger, web_logger


def setChromiumFlags():
    KEY = "QTWEBENGINE_CHROMIUM_FLAGS"
    OPTIONS = ["--ignore-gpu-blocklist", "--enable-gpu-rasterization"]

    if KEY in os.environ:
        for opt in OPTIONS:
            if opt not in os.environ[KEY]:
                os.environ[KEY] += " " + opt
    else:
        os.environ[KEY] = " ".join(OPTIONS)


class Q3DWebEnginePage(Q3DWebPageCommon, QWebEnginePage):

    jsErrorWarning = pyqtSignal(bool)       # bool: is_error

    def __init__(self, parent=None):
        QWebEnginePage.__init__(self, parent)
        Q3DWebPageCommon.__init__(self)

        self.isWebEnginePage = True

    def setup(self, settings, wnd=None):
        """wnd: Q3DWindow or None (off-screen mode)"""
        Q3DWebPageCommon.setup(self, settings, wnd)

        self.channel = QWebChannel(self)
        self.channel.registerObject("bridge", self.bridge)
        self.setWebChannel(self.channel)

        # security setting for billboard, model file and point cloud layer
        self.settings().setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)

        url = pluginDir("web/viewer/webengine.html").replace("\\", "/")
        self.myUrl = QUrl.fromLocalFile(url)
        self.reload()

    def reload(self):
        Q3DWebPageCommon.reload(self)

        self.setUrl(self.myUrl)

    def runScript(self, string, data=None, message="", sourceID="webengineview.py", callback=None, wait=False):
        """
        Run a JavaScript script in the web view with optional data and callback.
        Args:
            string (str): The JavaScript code string to execute.
            data (optional): Data to be passed along with the script execution.
            message (str, optional): A descriptive message for logging purposes.
            sourceID (str, optional): Identifier for the source of the script.
            callback (optional): Callback function to be executed after script runs.
            wait (bool, optional): Whether to wait for script execution to complete.
        """
        self.logScriptExecution(string, data, message, sourceID)

        if data is not None:
            assert callback is None, "cannot callback when data is set"
            assert not wait, "synchronous script execution with data not supported"

            self.bridge.sendScriptData.emit(string, data)
            return

        if not wait:
            if callback:
                self.runJavaScript(string, callback)

            else:
                self.runJavaScript(string)

            return

        loop = QEventLoop()
        result = None

        def runJavaScriptCallback(res):
            nonlocal result
            result = res
            loop.quit()

        self.runJavaScript(string, runJavaScriptCallback)

        loop.exec()

        if callback:
            callback(result)

        return result

    def sendData(self, data):
        self.bridge.sendScriptData.emit("loadJSONObject(pyData())", data)

    def logToConsole(self, message, level="debug"):
        if level not in ["debug", "info", "warn", "error"]:
            level = "log"
        self.runJavaScript('console.{}("{}");'.format(level, message.replace('"', '\\"')))

    def javaScriptConsoleMessage(self, level, message, lineNumber, sourceID):
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
        if type == QWebEnginePage.NavigationType.NavigationTypeLinkClicked:
            QDesktopServices.openUrl(url)
            return False
        return True


class Q3DWebEngineView(Q3DWebViewCommon, QWebEngineView):

    def __init__(self, parent=None):
        setChromiumFlags()

        QWebEngineView.__init__(self, parent)
        Q3DWebViewCommon.__init__(self)

        self._page = Q3DWebEnginePage(self)
        self._page.setObjectName("webEnginePage")
        self.setPage(self._page)

    def showDevTools(self):
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
        self.load(QUrl("chrome://gpu"))
