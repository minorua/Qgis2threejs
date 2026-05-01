# -*- coding: utf-8 -*-
# (C) 2016 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later
# begin: 2016-02-10

import base64
from functools import wraps

# This module may be used in an external process rather than within the QGIS process.
try:
    from PyQt6.QtCore import QByteArray, QObject, QVariant, pyqtSignal, pyqtSlot
    from PyQt6.QtGui import QImage
except ImportError:
    from PyQt5.QtCore import QByteArray, QObject, QVariant, pyqtSignal, pyqtSlot
    from PyQt5.QtGui import QImage

from .webview_conf import DEBUG_MODE, WEBVIEW_IN_QGIS_PROCESS
from .webview_utils import logger

if WEBVIEW_IN_QGIS_PROCESS:
    if DEBUG_MODE:
        def deco(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                logger.debug("↑ " + func.__name__)
                return func(*args, **kwargs)
            return wrapper
    else:
        def noop_decorator(func):
            return func

        deco = noop_decorator
else:
    def deco(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            params = {
                "name": func.__name__,
                "args": args[1:]
            }

            args[0].methodInvoked.emit(params)
            logger.debug(f"[IPC] ↑ {func.__name__}: {args[1:]}")
            return None
        return wrapper


class WebBridge(QObject):

    # signals - Python to JS
    sendData = pyqtSignal(QVariant, bool)           # data, viaQueue

    # signals - Bridge to Python (window, web page, etc.)
    initialized = pyqtSignal()
    dataLoaded = pyqtSignal()
    dataLoadError = pyqtSignal()
    sceneLoaded = pyqtSignal()
    scriptFileLoaded = pyqtSignal(int)              # scriptFileId
    tweenStarted = pyqtSignal(int)
    animationStopped = pyqtSignal()
    imageReady = pyqtSignal("QImage", bool)         # image, copy_to_clipboard -> Window
    modelDataReady = pyqtSignal("QByteArray", str, bool, bool)  # data, filename, is_first, is_last -> Window
    requestedRenderingFinished = pyqtSignal()       # -> WebPage
    resized = pyqtSignal(int, int)                  # width, height
    statusMessage = pyqtSignal(str, int)
    testResultReceived = pyqtSignal(str, bool, str)

    def __init__(self, parent):
        super().__init__(parent)

        self._storedData = QVariant()

    @pyqtSlot(result="QVariant")
    def data(self):
        return self._storedData

    def setData(self, data):
        self._storedData = QVariant(data)

    @pyqtSlot()
    @deco
    def emitInitialized(self):
        self.initialized.emit()

    @pyqtSlot()
    @deco
    def emitDataLoaded(self):
        self.dataLoaded.emit()

    @pyqtSlot()
    @deco
    def emitDataLoadError(self):
        self.dataLoadError.emit()

    @pyqtSlot()
    @deco
    def emitSceneLoaded(self):
        self.sceneLoaded.emit()

    @pyqtSlot(int)
    @deco
    def emitScriptReady(self, scriptFileId):
        self.scriptFileLoaded.emit(scriptFileId)

    @pyqtSlot(int)
    @deco
    def emitTweenStarted(self, index):
        self.tweenStarted.emit(index)

    @pyqtSlot()
    @deco
    def emitAnimationStopped(self):
        self.animationStopped.emit()

    @pyqtSlot(str, int)
    @deco
    def showStatusMessage(self, message, timeout_ms=0):
        self.statusMessage.emit(message, timeout_ms)

    @pyqtSlot(str, str, bool, bool)
    @deco
    def saveBase64(self, b64str, filename, is_first, is_last):
        self.modelDataReady.emit(base64.b64decode(b64str), filename, is_first, is_last)

    @pyqtSlot(str, str, bool, bool)
    @deco
    def saveText(self, text, filename, is_first, is_last):
        self.modelDataReady.emit(text.encode("UTF-8"), filename, is_first, is_last)

    @pyqtSlot(str)
    @deco
    def saveImage(self, dataUrl):
        image = QImage()
        if dataUrl:
            ba = QByteArray.fromBase64(dataUrl[22:].encode("ascii"))
            image.loadFromData(ba)
        self.imageReady.emit(image, False)

    @pyqtSlot(str)
    @deco
    def copyToClipboard(self, dataUrl):
        image = QImage()
        if dataUrl:
            ba = QByteArray.fromBase64(dataUrl[22:].encode("ascii"))
            image.loadFromData(ba)
        self.imageReady.emit(image, True)

    @pyqtSlot()
    @deco
    def emitRequestedRenderingFinished(self):
        self.requestedRenderingFinished.emit()

    @pyqtSlot(str, bool, str)
    @deco
    def sendTestResult(self, testName, result, msg):
        self.testResultReceived.emit(testName, result, msg)

    """
    @pyqtSlot(int, int, result=str)
    @notify_slot_called
    def mouseUpMessage(self, x, y):
        logger.debug(f"↑ Clicked at ({x}, {y})")
        # JS side: console.log(pyObj.mouseUpMessage(e.clientX, e.clientY));
    """


class WebIPCBridge(WebBridge):
    # signal - Bridge to Bridge via IPC
    methodInvoked = pyqtSignal(dict)    # {"name": "method name", "args": [args...]}
