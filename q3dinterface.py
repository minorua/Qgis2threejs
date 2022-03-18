# -*- coding: utf-8 -*-
# (C) 2018 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later
# begin: 2018-11-09

from PyQt5.QtCore import QObject, pyqtSlot

from .conf import DEBUG_MODE
from .tools import logMessage


class Q3DInterface(QObject):

    def __init__(self, settings, webPage, parent=None):
        super().__init__(parent)

        self.settings = settings
        self.webPage = webPage
        self.enabled = True

    @pyqtSlot(dict)
    def loadJSONObject(self, obj):
        # display the content of the object in the debug element
        if not self.enabled:
            return

        if DEBUG_MODE == 2:
            self.runScript("document.getElementById('debug').innerHTML = '{}';".format(str(obj)[:500].replace("'", "\\'")))

        self.webPage.sendData(obj)

    @pyqtSlot(str, object, str)
    def runScript(self, string, data=None, message=""):
        if self.enabled:
            self.webPage.runScript(string, data, message, sourceID="q3dwindow.py")

    @pyqtSlot(list, bool)
    def loadScriptFiles(self, ids, force):
        if self.enabled:
            self.webPage.loadScriptFiles(ids, force)

    # @pyqtSlot(str, int, bool)     # pyqtSlot override bug in PyQt5?
    def showMessage(self, msg, _1=0, _2=False):
        if self.enabled:
            logMessage(msg)

    # @pyqtSlot(int, str)
    def progress(self, percentage=100, msg=None):
        pass
