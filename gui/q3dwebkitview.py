# -*- coding: utf-8 -*-
# (C) 2016 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later
# begin: 2016-02-10

import os

from qgis.PyQt.QtCore import Qt, QSize, QUrl
from qgis.PyQt.QtGui import QDesktopServices, QImage, QPainter
from qgis.PyQt.QtWidgets import QDialog, QVBoxLayout

from qgis.PyQt.QtWebKit import QWebSettings, QWebSecurityOrigin
from qgis.PyQt.QtWebKitWidgets import QWebInspector, QWebPage, QWebView

from .q3dwebviewcommon import Q3DWebPageCommon, Q3DWebViewCommon
from ..conf import DEBUG_MODE
from ..utils import pluginDir, logger


class Q3DWebKitPage(Q3DWebPageCommon, QWebPage):

    def __init__(self, parent=None):
        QWebPage.__init__(self, parent)
        Q3DWebPageCommon.__init__(self)

        self.isWebEnginePage = False

    def url(self):
        return self.mainFrame().url()

    def setup(self, settings, wnd=None):
        """wnd: Q3DWindow or None (off-screen mode)"""
        Q3DWebPageCommon.setup(self, settings, wnd)

        self.mainFrame().javaScriptWindowObjectCleared.connect(self.addJSObject)

        # security settings
        origin = self.mainFrame().securityOrigin()
        origin.addAccessWhitelistEntry("http:", "*", QWebSecurityOrigin.AllowSubdomains)
        origin.addAccessWhitelistEntry("https:", "*", QWebSecurityOrigin.AllowSubdomains)

        self.setLinkDelegationPolicy(QWebPage.DelegateAllLinks)
        self.linkClicked.connect(QDesktopServices.openUrl)

        # if self.offScreen:
        #     # transparent background
        #     palette = self.palette()
        #     palette.setBrush(QPalette.Base, Qt.GlobalColor.transparent)
        #     self.setPalette(palette)
        #     #webview: self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, False)

        url = pluginDir("web/viewer/webkit.html").replace("\\", "/")
        self.myUrl = QUrl.fromLocalFile(url)
        self.reload()

    def addJSObject(self):
        self.mainFrame().addToJavaScriptWindowObject("pyObj", self.bridge)
        logger.debug("pyObj added")

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
        logger.debug(string)

        self.runScript(string, data, message=None)

    def logToConsole(self, message, level="debug"):
        self.mainFrame().evaluateJavaScript('console.{}("{}");'.format(level, message.replace('"', '\\"')))

    def renderImage(self, width, height, callback):
        old_size = self.viewportSize()
        self.setViewportSize(QSize(width, height))

        image = QImage(width, height, QImage.Format.Format_ARGB32_Premultiplied)
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
        self._page.setObjectName("webKitPage")
        self.setPage(self._page)

        # security setting for billboard, model file and point cloud layer
        self.settings().setAttribute(QWebSettings.LocalContentCanAccessRemoteUrls, True)

        # web inspector setting
        self.settings().setAttribute(QWebSettings.DeveloperExtrasEnabled, True)

    def showDevTools(self):
        dlg = QDialog(self)
        dlg.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
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
