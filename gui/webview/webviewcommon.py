# -*- coding: utf-8 -*-
# (C) 2023 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later
# begin: 2023-10-03

import json

# This module may be used in an external process rather than within the QGIS process.
from PyQt6.QtCore import QEventLoop, QTimer, pyqtSignal
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import QMessageBox
from PyQt6.QtWebEngineCore import QWebEnginePage

from .conf import DEBUG_MODE
from .webbridge import WebBridge
from .utils import logger
from ...core.const import ScriptFile
from ...utils.js import js_bool


TIMEOUT_MS = 30000      # timeout (ms) for script loading


class Q3DWebPageCommon:

    BridgeClass = WebBridge

    # signals
    jsErrorWarning = pyqtSignal(bool)       # is_error

    def __init__(self, _=None):
        self.loadedScripts = {}
        self.loadScriptCallbacks = {}

        self.loadFinished.connect(self.pageLoaded)

        self.bridge = self.BridgeClass(self)
        self.bridge.scriptFileLoaded.connect(self.scriptFileLoaded)

    def setup(self):
        pass

    def teardown(self):
        pass

    def pageLoaded(self, _ok):
        self.loadedScripts = {}

    def scriptFileLoaded(self, scriptFileId):
        self.loadedScripts[scriptFileId] = True

        callbacks = self.loadScriptCallbacks.pop(scriptFileId, [])
        for cb in callbacks:
            cb()

    def loadScriptFile(self, scriptFileId, callback=None, wait=False):
        if scriptFileId in self.loadedScripts:
            if callback:
                callback()
            return

        if callback:
            self.loadScriptCallbacks.setdefault(scriptFileId, []).append(callback)

        path = "../js/" + ScriptFile.PATHS[scriptFileId]
        script = f"loadScriptFile('{path}', function () {{pyObj.emitScriptReady({scriptFileId})}})"

        if wait:
            loop = QEventLoop()
            self.bridge.scriptFileLoaded.connect(loop.quit)

            timer = QTimer()
            timer.setSingleShot(True)
            timer.timeout.connect(loop.quit)

            self.runScript(script)
            timer.start(TIMEOUT_MS)
            loop.exec()

            if not timer.isActive():
                logger.warning(f"Loading script file timed out: {path}")
        else:
            self.runScript(script)

    def loadScriptFiles(self, scriptFileIds, callback=None):
        remaining = list(scriptFileIds)

        def load_next():
            if not remaining:
                if callback:
                    callback()
                return

            id = remaining.pop(0)
            self.loadScriptFile(id, callback=load_next)

        load_next()

    def runScript(self, string, message="", sourceID="webviewcommon.py", callback=None, wait=False):
        """
        Run a JavaScript script in the web view with optional data and callback.
        Args:
            string (str): The JavaScript code string to execute.
            message (str, optional): A descriptive message for logging purposes.
            sourceID (str, optional): Identifier for the source of the script.
            callback (optional): Callback function to be executed after script runs.
            wait (bool, optional): Whether to wait for script execution to complete.
        """

        if DEBUG_MODE and message is not None:
            text = message or string
            if sourceID:
                text += f"\t({sourceID})"
            logger.debug(f"> {text}")

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

    def showMessageBar(self, msg, timeout_ms=0, warning=False):
        """Show a message bar at the top of the web page.
        Args:
            msg: Message text or HTML string to display.
            timeout_ms: Time in milliseconds before the message bar is hidden.
            warning: If True, display the message bar in warning style.
        """
        self.runScript(f"showMessageBar({json.dumps(msg)}, {timeout_ms}, {js_bool(warning)})")

    def showStatusMessage(self, message, timeout_ms=0):
        self.bridge.statusMessage.emit(message, timeout_ms)

    def acceptNavigationRequest(self, url, type, isMainFrame):
        if type == QWebEnginePage.NavigationType.NavigationTypeLinkClicked:
            QDesktopServices.openUrl(url)
            return False
        return True

    def requestRendering(self, waitUntilFinished=False):
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


class Q3DWebViewCommon:

    WebViewType = None

    devToolsClosed = pyqtSignal()
    fileDropped = pyqtSignal(list)
    previewStateChanged = pyqtSignal(int)       # PreviewState

    def __init__(self, _=None):
        pass

    def runScript(self, string, message="", sourceID="webviewcommon.py", callback=None, wait=False):
        return self._page.runScript(string, message, sourceID, callback, wait)

    def showJSInfo(self):
        def showInfo(info):
            QMessageBox.information(self, "three.js Renderer Info", str(info))

        self.runScript("app.renderer.info", callback=showInfo)

    # <abstract methods>
    # def page(self):
    # def setup(self, webViewMode=None, enabledAtStart=True):
    # def teardown(self):
    # def setPreviewEnabled(self, enabled):
    # def showDevTools(self):
    # def showGPUInfo(self):
    # def triggerTestClick(self, pos):
