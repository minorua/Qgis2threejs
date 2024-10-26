# -*- coding: utf-8 -*-
# (C) 2018 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later
# begin: 2018-11-09

from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot

from .utils import logMessage


class Q3DInterface(QObject):

    # signals - iface to window
    statusMessage = pyqtSignal(str, int)             # params: msg, timeout_ms
    progressUpdated = pyqtSignal(int, str)           # params: percentage, msg

    def __init__(self, settings, webPage, parent=None):
        super().__init__(parent)

        self.settings = settings
        self.webPage = webPage
        self.enabled = True

    @pyqtSlot(dict)
    def sendJSONObject(self, obj):
        if self.enabled:
            self.webPage.sendData(obj)

    @pyqtSlot(str, object, str)
    def runScript(self, string, data=None, message=""):
        if self.enabled:
            self.webPage.runScript(string, data, message, sourceID="q3dwindow.py")

    @pyqtSlot(list, bool)
    def loadScriptFiles(self, ids, force):
        if self.enabled:
            self.webPage.loadScriptFiles(ids, force)

    # @pyqtSlot(str, int)
    def showStatusMessage(self, msg, _1=0):
        if self.enabled:
            logMessage(msg)
