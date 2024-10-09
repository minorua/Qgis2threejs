# -*- coding: utf-8 -*-
# (C) 2016 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later
# begin: 2016-02-10

from functools import wraps
from PyQt5.QtCore import QByteArray, QObject, QVariant, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QImage

from .conf import DEBUG_MODE


def notify_slot_called(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if DEBUG_MODE:
            args[0].slotCalled.emit("↑ " + func.__name__)

        return func(*args, **kwargs)

    return wrapper


class Bridge(QObject):

    # Python to JS signals
    sendScriptData = pyqtSignal(str, QVariant)

    # Python to Python signals
    slotCalled = pyqtSignal(str)
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
        self.data = QVariant()

    @pyqtSlot(result="QVariant")
    def data(self):
        return self.data

    def setData(self, data):
        self.data = QVariant(data)

    @pyqtSlot()
    @notify_slot_called
    def onInitialized(self):
        self.initialized.emit()

    @pyqtSlot()
    @notify_slot_called
    def onSceneLoaded(self):
        self.sceneLoaded.emit()

    @pyqtSlot()
    @notify_slot_called
    def onSceneLoadError(self):
        self.sceneLoadError.emit()

    @pyqtSlot(str, int)
    @notify_slot_called
    def showStatusMessage(self, message, duration=0):
        self.statusMessage.emit(message, duration)

    @pyqtSlot("QByteArray", str)
    @notify_slot_called
    def saveBytes(self, data, filename):
        self.modelDataReady.emit(data, filename)

    @pyqtSlot(str, str)
    @notify_slot_called
    def saveString(self, text, filename):
        self.modelDataReady.emit(text.encode("UTF-8"), filename)

    @pyqtSlot(int, int, str)
    @notify_slot_called
    def saveImage(self, width, height, dataUrl):
        image = None
        if dataUrl:
            ba = QByteArray.fromBase64(dataUrl[22:].encode("ascii"))
            image = QImage()
            image.loadFromData(ba)
        self.imageReady.emit(width, height, image)

    @pyqtSlot(int)
    @notify_slot_called
    def onTweenStarted(self, index):
        self.tweenStarted.emit(index)

    @pyqtSlot()
    @notify_slot_called
    def onAnimationStopped(self):
        self.animationStopped.emit()

    @pyqtSlot(str, bool, str)
    @notify_slot_called
    def sendTestResult(self, testName, result, msg):
        self.testResultReceived.emit(testName, result, msg)

    """
    @pyqtSlot(int, int, result=str)
    @notify_slot_called
    def mouseUpMessage(self, x, y):
        self.logToConsole.emit("↑ mouseUpMessage")
        return "Clicked at ({0}, {1})".format(x, y)
        # JS side: console.log(pyObj.mouseUpMessage(e.clientX, e.clientY));
    """
