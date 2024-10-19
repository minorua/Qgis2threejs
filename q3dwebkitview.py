# -*- coding: utf-8 -*-
# (C) 2016 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later
# begin: 2016-02-10

import os

from PyQt5.QtCore import Qt, QSize, QUrl
from PyQt5.QtGui import QImage, QPainter
from PyQt5.QtWidgets import QDialog, QMessageBox, QVBoxLayout

from .conf import DEBUG_MODE, PLUGIN_NAME
try:
    from PyQt5.QtWebKit import QWebSettings, QWebSecurityOrigin
    from PyQt5.QtWebKitWidgets import QWebPage, QWebView
    from PyQt5.QtWebKitWidgets import QWebInspector
except ModuleNotFoundError:
    if os.name == "posix":
        QMessageBox.warning(None, PLUGIN_NAME, 'Missing dependencies related to PyQt5 and QtWebKit. Please install "python3-pyqt5.qtwebkit" package (Debian/Ubuntu) before using this plugin.')
    raise

from .q3dwebviewcommon import Q3DWebPageCommon, Q3DWebViewCommon


class Q3DWebKitPage(Q3DWebPageCommon, QWebPage):

    def __init__(self, parent=None):
        QWebPage.__init__(self, parent)
        Q3DWebPageCommon.__init__(self)

        self.isWebEnginePage = False

    def url(self):
        return self.mainFrame().url()

    def setup(self, settings, wnd=None, exportMode=False):
        """wnd: Q3DWindow or None (off-screen mode)"""
        Q3DWebPageCommon.setup(self, settings, wnd, exportMode)

        self.mainFrame().javaScriptWindowObjectCleared.connect(self.addJSObject)

        # security settings
        origin = self.mainFrame().securityOrigin()
        origin.addAccessWhitelistEntry("http:", "*", QWebSecurityOrigin.AllowSubdomains)
        origin.addAccessWhitelistEntry("https:", "*", QWebSecurityOrigin.AllowSubdomains)

        # if self.offScreen:
        #     # transparent background
        #     palette = self.palette()
        #     palette.setBrush(QPalette.Base, Qt.transparent)
        #     self.setPalette(palette)
        #     #webview: self.setAttribute(Qt.WA_OpaquePaintEvent, False)

        url = os.path.join(os.path.abspath(os.path.dirname(__file__)), "viewer", "webkit.html").replace("\\", "/")
        self.myUrl = QUrl.fromLocalFile(url)
        self.reload()

    def addJSObject(self):
        self.mainFrame().addToJavaScriptWindowObject("pyObj", self.bridge)
        if DEBUG_MODE:
            self.logToConsole("pyObj added")

    def reload(self):
        Q3DWebPageCommon.reload(self)

        self.mainFrame().setUrl(self.myUrl)

    def runScript(self, string, data=None, message="", sourceID="q3dview.py", callback=None, wait=False):
        Q3DWebPageCommon.runScript(self, string, data, message, sourceID, callback, wait)

        if data is not None:
            self.bridge.setData(data)

        result = self.mainFrame().evaluateJavaScript(string)
        if callback:
            callback(result)

        return result

    def sendData(self, data):
        string = "loadJSONObject(pyData())"
        if DEBUG_MODE:
            self.logToConsole(string)

        self.runScript(string, data, message=None)

    def logToConsole(self, message, level="debug"):
        self.mainFrame().evaluateJavaScript('console.{}("{}");'.format(level, message.replace('"', '\\"')))

    def renderImage(self, width, height, callback):
        old_size = self.viewportSize()
        self.setViewportSize(QSize(width, height))

        image = QImage(width, height, QImage.Format_ARGB32_Premultiplied)
        painter = QPainter(image)
        self.mainFrame().render(painter)
        painter.end()

        self.setViewportSize(old_size)

        callback(image)


class Q3DWebKitView(Q3DWebViewCommon, QWebView):

    def __init__(self, parent=None):
        QWebView.__init__(self, parent)
        Q3DWebViewCommon.__init__(self)

        self._page = Q3DWebKitPage(self)
        self.setPage(self._page)

        # security setting for billboard, model file and point cloud layer
        self.settings().setAttribute(QWebSettings.LocalContentCanAccessRemoteUrls, True)

        # web inspector setting
        self.settings().setAttribute(QWebSettings.DeveloperExtrasEnabled, True)

    def showDevTools(self):
        dlg = QDialog(self)
        dlg.setAttribute(Qt.WA_DeleteOnClose)
        dlg.resize(800, 500)
        dlg.setWindowTitle("Qgis2threejs Web Inspector")
        dlg.rejected.connect(self.devToolsClosed)

        wi = QWebInspector(dlg)
        wi.setPage(self._page)

        v = QVBoxLayout()
        v.setContentsMargins(0, 0, 0, 0)
        v.addWidget(wi)

        dlg.setLayout(v)
        dlg.show()

    def renderImage(self, width, height, callback, wnd=None):
        self._page.renderImage(width, height, callback)
