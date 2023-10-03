# -*- coding: utf-8 -*-
# (C) 2016 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later
# begin: 2016-02-10

from PyQt5.QtCore import QByteArray, QObject, QVariant, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QImage


class Bridge(QObject):

    # Python to Python signals
    initialized = pyqtSignal()
    sceneLoaded = pyqtSignal()
    sceneLoadError = pyqtSignal()
    statusMessage = pyqtSignal(str, int)
    modelDataReady = pyqtSignal("QByteArray", str)
    imageReady = pyqtSignal(int, int, "QImage")
    tweenStarted = pyqtSignal(int)
    animationStopped = pyqtSignal()

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
    def onSceneLoaded(self):
        self.sceneLoaded.emit()

    @pyqtSlot()
    def onSceneLoadError(self):
        self.sceneLoadError.emit()

    @pyqtSlot(str, int)
    def showStatusMessage(self, message, duration=0):
        self.statusMessage.emit(message, duration)

    @pyqtSlot("QByteArray", str)
    def saveBytes(self, data, filename):
        self.modelDataReady.emit(data, filename)

    @pyqtSlot(str, str)
    def saveString(self, text, filename):
        self.modelDataReady.emit(text.encode("UTF-8"), filename)

    @pyqtSlot(int, int, str)
    def saveImage(self, width, height, dataUrl):
        image = None
        if dataUrl:
            ba = QByteArray.fromBase64(dataUrl[22:].encode("ascii"))
            image = QImage()
            image.loadFromData(ba)
        self.imageReady.emit(width, height, image)

    @pyqtSlot(int)
    def onTweenStarted(self, index):
        self.tweenStarted.emit(index)

    @pyqtSlot()
    def onAnimationStopped(self):
        self.animationStopped.emit()

    """
    @pyqtSlot(int, int, result=str)
    def mouseUpMessage(self, x, y):
        return "Clicked at ({0}, {1})".format(x, y)
        # JS side: console.log(pyObj.mouseUpMessage(e.clientX, e.clientY));
    """
