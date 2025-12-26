# -*- coding: utf-8 -*-
# (C) 2023 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later
# begin: 2023-10-03

import os

from qgis.PyQt.QtCore import QEventLoop, QObject, QTimer, pyqtSignal, pyqtSlot
from qgis.PyQt.QtWidgets import QMessageBox

from .webbridge import WebBridge
from ..conf import DEBUG_MODE
from ..core.const import ScriptFile
from ..utils import hex_color, js_bool, logger, pluginDir


class Q3DViewInterface(QObject):

    def __init__(self, parent, webPage):
        super().__init__(parent)

        self.webPage = webPage
        self.enabled = True

    @pyqtSlot(dict)
    def sendData(self, data):
        if self.enabled:
            self.webPage.sendData(data)

    @pyqtSlot(str, object, str)
    def runScript(self, string, data=None, message=""):
        if self.enabled:
            self.webPage.runScript(string, data, message, sourceID="interface.py")

    @pyqtSlot(list, bool)
    def loadScriptFiles(self, ids, force=False):
        """
        Args:
            ids: list of script IDs
            force: if False, do not load a script that is already loaded
        """
        if self.enabled:
            self.webPage.loadScriptFiles(ids, force)


class Q3DWebPageCommon:

    initialized = pyqtSignal()
    sceneLoaded = pyqtSignal()
    sceneLoadError = pyqtSignal()

    def __init__(self, _=None):
        self.bridge = WebBridge(self)
        self.bridge.initialized.connect(self.initialized)
        self.bridge.sceneLoaded.connect(self.sceneLoaded)
        self.bridge.sceneLoadError.connect(self.sceneLoadError)

        self.loadedScripts = {}
        self.loadFinished.connect(self.pageLoaded)

    def setup(self, settings, wnd=None):
        """wnd: Q3DWindow or None (off-screen mode)"""
        self.expSettings = settings
        self.wnd = wnd
        self.offScreen = bool(wnd is None)

    def teardown(self):
        self.wnd = None

    def pageLoaded(self):
        self.loadedScripts = {}

    def reload(self):
        self.showStatusMessage("Initializing preview...")

    def logScriptExecution(self, string, data=None, message="", sourceID=""):
        if not DEBUG_MODE or message is None:
            return

        text = message or string
        if sourceID:
            text += f"\t({sourceID})"

        logger.debug(f"> {text}")

    def loadScriptFile(self, scriptFileId, force=False):
        """evaluate a script file without using a script tag. script is loaded synchronously"""
        if scriptFileId in self.loadedScripts and not force:
            return

        filename = pluginDir("web/js", ScriptFile.PATHS[scriptFileId])

        with open(filename, "r", encoding="utf-8") as f:
            script = f.read()

        self.runScript(script, message="{} loaded.".format(os.path.basename(filename)))
        self.loadedScripts[scriptFileId] = True

    def loadScriptFiles(self, scriptFileIds, force=False):
        for id in scriptFileIds:
            self.loadScriptFile(id, force)

    def waitForSceneLoaded(self, abortSignal=None, timeout=None):
        loading = self.runScript("app.loadingManager.isLoading", wait=True)

        logger.debug("waitForSceneLoaded: loading=%s", loading)

        if not loading:
            return False

        loop = QEventLoop()

        def error():
            loop.exit(1)

        def userCancel():
            loop.exit(2)

        def timeOut():
            loop.exit(3)

        self.sceneLoaded.connect(loop.quit)
        self.sceneLoadError.connect(error)

        if abortSignal:
            abortSignal.connect(userCancel)

        if timeout:
            timer = QTimer()
            timer.setSingleShot(True)
            timer.timeout.connect(timeOut)
            timer.start(timeout)

        err = loop.exec()

        self.sceneLoaded.disconnect(loop.quit)
        self.sceneLoadError.disconnect(error)

        if abortSignal:
            abortSignal.disconnect(userCancel)

        if err:
            return {1: "error", 2: "canceled", 3: "timeout"}[err]
        return False

    def showMessageBar(self, msg, timeout_ms=0, warning=False):
        self.runScript(f"showMessageBar(pyData(), {timeout_ms}, {js_bool(warning)})", msg)

    def showStatusMessage(self, message, timeout_ms=0):
        self.bridge.statusMessage.emit(message, timeout_ms)


class Q3DWebViewCommon:

    devToolsClosed = pyqtSignal()
    fileDropped = pyqtSignal(list)

    def __init__(self, _=None):
        self.setAcceptDrops(True)

    def setup(self, settings, wnd=None, enabled=True):
        """
        :param settings: ExportSettings
        :param wnd: Q3DWindow or None (off-screen mode)
        :param enabled: whether preview is enabled at start
        """
        self._enabled = enabled     # whether preview is enabled at start

        self._page.setup(settings, wnd)

    def teardown(self):
        self._page.wnd = None
        self._page = None

    def dragEnterEvent(self, event):
        event.acceptProposedAction()

    def dropEvent(self, event):
        # logger.debug(event.mimeData().formats())
        self.fileDropped.emit(event.mimeData().urls())
        event.acceptProposedAction()

    def sendData(self, data):
        self._page.sendData(data)

    def runScript(self, string, data=None, message="", sourceID="webviewcommon.py", callback=None, wait=False):
        return self._page.runScript(string, data, message, sourceID, callback, wait)

    def showJSInfo(self):
        info = self.runScript("app.renderer.info", wait=True)
        QMessageBox.information(self, "three.js Renderer Info", str(info))
