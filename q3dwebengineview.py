# -*- coding: utf-8 -*-
# (C) 2023 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later
# begin: 2023-10-03

import os
os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--ignore-gpu-blocklist --enable-gpu-rasterization"

from PyQt5.QtCore import Qt, QEventLoop, QSize, QUrl
from PyQt5.QtGui import QImage, QPainter
from PyQt5.QtWidgets import QDialog, QVBoxLayout
from PyQt5.QtWebChannel import QWebChannel
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEnginePage, QWebEngineSettings

from .q3dwebviewcommon import Q3DWebPageCommon, Q3DWebViewCommon


class Q3DWebEnginePage(Q3DWebPageCommon, QWebEnginePage):

    def __init__(self, parent=None):
        QWebEnginePage.__init__(self, parent)
        Q3DWebPageCommon.__init__(self)

        self.isWebEnginePage = True

    def setup(self, settings, wnd=None, exportMode=False):
        """wnd: Q3DWindow or None (off-screen mode)"""
        Q3DWebPageCommon.setup(self, settings, wnd, exportMode)

        self.channel = QWebChannel(self)
        self.channel.registerObject("bridge", self.bridge)
        self.setWebChannel(self.channel)

        # security setting for billboard, model file and point cloud layer
        self.settings().setAttribute(QWebEngineSettings.LocalContentCanAccessRemoteUrls, True)

        url = os.path.join(os.path.abspath(os.path.dirname(__file__)), "viewer", "webengine.html").replace("\\", "/")
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

        loop.exec_()

        if callback:
            callback(result)

        return result

    def sendData(self, data):
        self.bridge.sendScriptData.emit("loadJSONObject(pyData())", data)

    #TODO
    def renderImage(self, width, height):
        old_size = self.viewportSize()
        self.setViewportSize(QSize(width, height))

        image = QImage(width, height, QImage.Format_ARGB32_Premultiplied)
        painter = QPainter(image)
        self.mainFrame().render(painter)
        painter.end()

        self.setViewportSize(old_size)
        return image

    def javaScriptConsoleMessage(self, level, message, lineNumber, sourceID):
        Q3DWebPageCommon.javaScriptConsoleMessage(self, message, lineNumber, sourceID)


class Q3DWebEngineView(Q3DWebViewCommon, QWebEngineView):

    def __init__(self, parent=None):
        QWebEngineView.__init__(self, parent)
        Q3DWebViewCommon.__init__(self)

        self._page = Q3DWebEnginePage(self)
        self.setPage(self._page)

    def showInspector(self):
        dlg = QDialog(self)
        dlg.setAttribute(Qt.WA_DeleteOnClose)
        dlg.resize(800, 500)
        dlg.setWindowTitle("Qgis2threejs Web Inspector")

        ins = QWebEngineView(dlg)
        self._page.setDevToolsPage(ins.page())

        v = QVBoxLayout()
        v.setContentsMargins(0, 0, 0, 0)
        v.addWidget(ins)

        dlg.setLayout(v)
        dlg.show()
