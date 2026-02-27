# -*- coding: utf-8 -*-
# (C) 2023 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later
# begin: 2023-10-03

import json
from qgis.PyQt.QtCore import QEventLoop, QTimer, pyqtSignal
from qgis.PyQt.QtWidgets import QMessageBox

from .webbridge import WebBridge
from ..conf import DEBUG_MODE
from ..core.const import ScriptFile
from ..utils import js_bool, logger


TIMEOUT_MS = 30000      # timeout (ms) for script loading


class Q3DWebPageCommon:

    def __init__(self, _=None):
        self.bridge = WebBridge(self)

        self.loadedScripts = {}
        self.loadScriptCallbacks = {}

        self.loadFinished.connect(self.pageLoaded)
        self.bridge.scriptFileLoaded.connect(self.scriptFileLoaded)

    def setup(self):
        pass

    def teardown(self):
        pass

    def pageLoaded(self):
        self.loadedScripts = {}

    def scriptFileLoaded(self, scriptFileId):
        self.loadedScripts[scriptFileId] = True

        callbacks = self.loadScriptCallbacks.pop(scriptFileId, [])
        for cb in callbacks:
            cb()

    def logScriptExecution(self, string, message="", sourceID=""):
        if not DEBUG_MODE or message is None:
            return

        text = message or string
        if sourceID:
            text += f"\t({sourceID})"

        logger.debug(f"> {text}")

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
        if not scriptFileIds:
            raise Exception("loadScriptFiles called with empty scriptFileIds")

        remaining = list(scriptFileIds)

        def load_next():
            if not remaining:
                if callback:
                    callback()
                return

            id = remaining.pop(0)
            self.loadScriptFile(id, callback=load_next)

        load_next()

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


class Q3DWebViewCommon:

    devToolsClosed = pyqtSignal()
    fileDropped = pyqtSignal(list)

    def __init__(self, _=None):
        self.setAcceptDrops(True)

    def setup(self, enabled=True):
        """
        :param enabled: whether preview is enabled at start
        """
        self._enabled = enabled     # whether preview is enabled at start

        self._page.setup()

    def teardown(self):
        self._page = None

    def dragEnterEvent(self, event):
        event.acceptProposedAction()

    def dropEvent(self, event):
        # logger.debug(event.mimeData().formats())
        self.fileDropped.emit(event.mimeData().urls())
        event.acceptProposedAction()

    def runScript(self, string, message="", sourceID="webviewcommon.py", callback=None, wait=False):
        return self._page.runScript(string, message, sourceID, callback, wait)

    def showJSInfo(self):
        def showInfo(info):
            QMessageBox.information(self, "three.js Renderer Info", str(info))

        self.runScript("app.renderer.info", callback=showInfo)
