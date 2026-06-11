# -*- coding: utf-8 -*-
# (C) 2016 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later
# begin: 2016-02-10

import base64
from functools import wraps

# This module may be used in an external process rather than within the QGIS process.
from PyQt6.QtCore import QByteArray, QObject, QVariant, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QImage

from .conf import DEBUG_MODE, WEBVIEW_IN_QGIS_PROCESS
from .utils import logger

if WEBVIEW_IN_QGIS_PROCESS:
    if DEBUG_MODE:
        def log_decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                logger.debug("↑ " + func.__name__)
                return func(*args, **kwargs)
            return wrapper

        deco = log_decorator
    else:
        def noop_decorator(func):
            return func

        deco = noop_decorator
else:
    def log_emit_decorator(func):
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

    deco = log_emit_decorator


class WebBridge(QObject):

    # signals - Python to JS
    sendData = pyqtSignal(QVariant, bool)           # data, viaQueue

    # signals - Bridge to Python (window, web page, etc.)
    initialized = pyqtSignal()
    dataLoaded = pyqtSignal()
    dataLoadError = pyqtSignal()                    # not used yet
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

    @pyqtSlot()
    def emitDataLoaded(self):
        self.dataLoaded.emit()

    @pyqtSlot()
    def emitInitialized(self):
        self.initialized.emit()

    @pyqtSlot()
    def emitDataLoadError(self):
        self.dataLoadError.emit()

    @pyqtSlot()
    def emitSceneLoaded(self):
        self.sceneLoaded.emit()

    @pyqtSlot(int)
    def emitScriptReady(self, scriptFileId):
        self.scriptFileLoaded.emit(scriptFileId)

    @pyqtSlot(int)
    def emitTweenStarted(self, index):
        self.tweenStarted.emit(index)

    @pyqtSlot()
    def emitAnimationStopped(self):
        self.animationStopped.emit()

    @pyqtSlot(str, int)
    def showStatusMessage(self, message, timeout_ms=0):
        self.statusMessage.emit(message, timeout_ms)

    @pyqtSlot(str, str, bool, bool)
    def saveBase64(self, b64str, filename, is_first, is_last):
        self.modelDataReady.emit(base64.b64decode(b64str), filename, is_first, is_last)

    @pyqtSlot(str, str, bool, bool)
    def saveText(self, text, filename, is_first, is_last):
        self.modelDataReady.emit(text.encode("UTF-8"), filename, is_first, is_last)

    @pyqtSlot(str)
    def saveImage(self, dataUrl):
        image = QImage()
        if dataUrl:
            ba = QByteArray.fromBase64(dataUrl[22:].encode("ascii"))
            image.loadFromData(ba)
        self.imageReady.emit(image, False)

    @pyqtSlot(str)
    def copyToClipboard(self, dataUrl):
        image = QImage()
        if dataUrl:
            ba = QByteArray.fromBase64(dataUrl[22:].encode("ascii"))
            image.loadFromData(ba)
        self.imageReady.emit(image, True)

    @pyqtSlot()
    def emitRequestedRenderingFinished(self):
        self.requestedRenderingFinished.emit()

    @pyqtSlot(str, bool, str)
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
