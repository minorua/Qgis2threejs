# -*- coding: utf-8 -*-
# (C) 2016 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later
# begin: 2016-02-10

from functools import wraps
from qgis.PyQt.QtCore import QByteArray, QObject, QVariant, pyqtSignal, pyqtSlot
from qgis.PyQt.QtGui import QImage

from ..conf import DEBUG_MODE
from ..utils import logger


if DEBUG_MODE:
    def emit_slotCalled(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger.debug("↑ " + func.__name__)
            return func(*args, **kwargs)
        return wrapper
else:
    def noop(func):
        return func
    emit_slotCalled = noop


class WebBridge(QObject):

    # signals - Python to JS
    sendScriptData = pyqtSignal(str, QVariant)

    # signals - Bridge to Python (window, web page, etc.)
    initialized = pyqtSignal()
    sceneLoaded = pyqtSignal()
    sceneLoadError = pyqtSignal()
    statusMessage = pyqtSignal(str, int)
    modelDataReady = pyqtSignal("QByteArray", str)
    imageReady = pyqtSignal(int, int, "QImage")
    tweenStarted = pyqtSignal(int)
    animationStopped = pyqtSignal()
    testResultReceived = pyqtSignal(str, bool, str)

    def __init__(self, parent=None):
        QObject.__init__(self, parent)
        self._parent = parent
        self._storedData = QVariant()

    @pyqtSlot(result="QVariant")
    def data(self):
        return self._storedData

    def setData(self, data):
        self._storedData = QVariant(data)

    @pyqtSlot()
    @emit_slotCalled
    def emitInitialized(self):
        self.initialized.emit()

    @pyqtSlot()
    @emit_slotCalled
    def emitSceneLoaded(self):
        self.sceneLoaded.emit()

    @pyqtSlot()
    @emit_slotCalled
    def emitSceneLoadError(self):
        self.sceneLoadError.emit()

    @pyqtSlot(int)
    @emit_slotCalled
    def emitTweenStarted(self, index):
        self.tweenStarted.emit(index)

    @pyqtSlot()
    @emit_slotCalled
    def emitAnimationStopped(self):
        self.animationStopped.emit()

    @pyqtSlot(str, int)
    @emit_slotCalled
    def showStatusMessage(self, message, timeout_ms=0):
        self.statusMessage.emit(message, timeout_ms)

    @pyqtSlot("QByteArray", str)
    @emit_slotCalled
    def saveBytes(self, data, filename):
        self.modelDataReady.emit(data, filename)

    @pyqtSlot(str, str)
    @emit_slotCalled
    def saveString(self, text, filename):
        self.modelDataReady.emit(text.encode("UTF-8"), filename)

    @pyqtSlot(int, int, str)
    @emit_slotCalled
    def saveImage(self, width, height, dataUrl):
        image = None
        if dataUrl:
            ba = QByteArray.fromBase64(dataUrl[22:].encode("ascii"))
            image = QImage()
            image.loadFromData(ba)
        self.imageReady.emit(width, height, image)

    @pyqtSlot(str, bool, str)
    @emit_slotCalled
    def sendTestResult(self, testName, result, msg):
        self.testResultReceived.emit(testName, result, msg)

    """
    @pyqtSlot(int, int, result=str)
    @notify_slot_called
    def mouseUpMessage(self, x, y):
        logger.debug(f"↑ Clicked at ({x}, {y})")
        # JS side: console.log(pyObj.mouseUpMessage(e.clientX, e.clientY));
    """
