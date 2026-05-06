# -*- coding: utf-8 -*-
# (C) 2026 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later

import json

# This module may be used in an external process rather than within the QGIS process.
from PyQt6.QtCore import QEventLoop, QTimer, pyqtSignal
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWebEngineCore import QWebEnginePage

from .webviewcommon import Q3DWebPageCommon, Q3DWebViewCommon, TIMEOUT_MS, WEBVIEWTYPE_WEBENGINE
from ..utils import logger


class Q3DWebEnginePageCommon(Q3DWebPageCommon):

    jsErrorWarning = pyqtSignal(bool)       # is_error

    def runScript(self, string, message="", sourceID="webenginecommon.py", callback=None, wait=False):
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

    def logToConsole(self, message, level="debug"):
        if level not in ["debug", "info", "warn", "error"]:
            level = "log"

        if level in ["warn", "error"]:
            self.jsErrorWarning.emit(bool(level == "error"))

        msg = json.dumps(message.replace('\n', '\\n'))      # new line causes issues in console

        self.runJavaScript(f"console.{level}({msg});")

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


class Q3DWebEngineViewCommon(Q3DWebViewCommon):

    def __init__(self, _=None):
        super().__init__()

        self.webViewType = WEBVIEWTYPE_WEBENGINE
