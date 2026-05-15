# -*- coding: utf-8 -*-
# (C) 2023 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later
# begin: 2023-10-03

import os
import logging

# This module may be used in an external process rather than within the QGIS process.
from PyQt6.QtCore import Qt, QEvent, QUrl
from PyQt6.QtGui import QDesktopServices, QMouseEvent
from PyQt6.QtWidgets import QApplication, QDialog, QVBoxLayout, QWidget
from PyQt6.QtWebEngineCore import QWebEnginePage, QWebEngineSettings
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebChannel import QWebChannel

from .conf import DEBUG_MODE
from .const import PreviewState
from .utils import logger, web_logger
from .webviewcommon import Q3DWebPageCommon, Q3DWebViewCommon
from ...utils.basic import pluginDir


_original_chromium_flags = None
_chromium_flags_saved = False


def setChromiumFlags():
    global _original_chromium_flags, _chromium_flags_saved

    KEY = "QTWEBENGINE_CHROMIUM_FLAGS"
    OPTIONS = []        # "--remote-debugging-port=9222"

    if not _chromium_flags_saved:
        _original_chromium_flags = os.environ.get(KEY)
        _chromium_flags_saved = True

    if KEY in os.environ:
        for opt in OPTIONS:
            if opt not in os.environ[KEY]:
                os.environ[KEY] += " " + opt
    else:
        os.environ[KEY] = " ".join(OPTIONS)


def restoreChromiumFlags():
    if not _chromium_flags_saved:
        return

    KEY = "QTWEBENGINE_CHROMIUM_FLAGS"

    if _original_chromium_flags is not None:
        os.environ[KEY] = _original_chromium_flags
    else:
        if KEY in os.environ:
            del os.environ[KEY]


class Q3DWebEnginePage(Q3DWebPageCommon, QWebEnginePage):

    def __init__(self, parent=None):
        QWebEnginePage.__init__(self, parent)
        Q3DWebPageCommon.__init__(self, parent)

        self.channel = QWebChannel(self)
        self.channel.registerObject("bridge", self.bridge)
        self.setWebChannel(self.channel)

        # security setting for billboard, model file and point cloud layer
        self.settings().setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)

    def setup(self):
        url = pluginDir("web/viewer/webengine.html").replace("\\", "/")
        self.myUrl = QUrl.fromLocalFile(url)
        self.reload()

    def reload(self):
        self.showStatusMessage("Initializing preview...")
        self.setUrl(self.myUrl)

    def sendData(self, data, viaQueue=False):
        logger.debug("Sending {} data to web page...".format(data.get("type", "unknown")))
        self.bridge.sendData.emit(data, viaQueue)

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

    WebPageClass = Q3DWebEnginePage

    def __init__(self, parent):
        setChromiumFlags()

        QWebEngineView.__init__(self, parent)
        Q3DWebViewCommon.__init__(self)

        self.setAcceptDrops(True)

        self._page = self.WebPageClass(self)
        self._page.setObjectName("WebEnginePage")
        self._page.loadFinished.connect(lambda ok: self.previewStateChanged.emit(PreviewState.Active))
        self.setPage(self._page)

        restoreChromiumFlags()

    def setup(self, webViewMode=None, enabledAtStart=True):
        self._page.setup()

    def teardown(self):
        self._page = None

    def dragEnterEvent(self, event):
        event.acceptProposedAction()

    def dropEvent(self, event):
        # logger.debug(event.mimeData().formats())
        self.fileDropped.emit(event.mimeData().urls())
        event.acceptProposedAction()

    def setPreviewEnabled(self, enabled):
        if enabled:
            self._page.reload()
        else:
            self.runScript("setPreviewEnabled(false)")

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

    def triggerTestClick(self, pos):
        w = self.findChild(QWidget)
        press = QMouseEvent(QEvent.Type.MouseButtonPress, pos, Qt.MouseButton.LeftButton, Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier)
        release = QMouseEvent(QEvent.Type.MouseButtonRelease, pos, Qt.MouseButton.LeftButton, Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier)

        QApplication.postEvent(w, press)
        QApplication.postEvent(w, release)
