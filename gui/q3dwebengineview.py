# -*- coding: utf-8 -*-
# (C) 2023 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later
# begin: 2023-10-03

import os

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

from .q3dwebviewcommon import Q3DWebPageCommon, Q3DWebViewCommon
from ..utils import pluginDir


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

    def runScript(self, string, data=None, message="", sourceID="q3dview.py", callback=None, wait=False):
        """wait: whether to wait until script execution has completed"""
        Q3DWebPageCommon.runScript(self, string, data, message, sourceID, callback, wait)

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
        if level in (QWebEnginePage.JavaScriptConsoleMessageLevel.WarningMessageLevel, QWebEnginePage.JavaScriptConsoleMessageLevel.ErrorMessageLevel):
            self.jsErrorWarning.emit(bool(level == QWebEnginePage.JavaScriptConsoleMessageLevel.ErrorMessageLevel))

        Q3DWebPageCommon.javaScriptConsoleMessage(self, message, lineNumber, sourceID)

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

    # FIXME: unstable
    def renderImage(self, width, height, callback, wnd=None):
        if wnd:
            geom = wnd.saveGeometry()
            wnd.setEnabled(False)

        img = QImage(width, height, QImage.Format.Format_ARGB32)
        painter = QPainter(img)

        minSize = self.minimumSize()
        maxSize = self.maximumSize()

        self.setMinimumSize(width, height)
        self.setMaximumSize(width, height)

        def restoreGeom():
            wnd.restoreGeometry(geom)

        def myCallback(_=None):
            self.render(painter)
            painter.end()

            callback(img)

            self.setMinimumSize(minSize)
            self.setMaximumSize(maxSize)

            if wnd:
                wnd.setEnabled(True)

                QTimer.singleShot(200, restoreGeom)

        def preCallback(_=None):
            QTimer.singleShot(200, myCallback)

        def requestRender():
            self.runScript("app.render()", callback=preCallback)

        QTimer.singleShot(1000, requestRender)
