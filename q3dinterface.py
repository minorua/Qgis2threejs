# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Q3DInterface

                              -------------------
        begin                : 2018-11-09
        copyright            : (C) 2018 Minoru Akagi
        email                : akaginch@gmail.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot

from .conf import DEBUG_MODE
from .qgis2threejstools import logMessage


class Q3DInterface(QObject):

    def __init__(self, settings, webPage, parent=None):
        super().__init__(parent)

        self.settings = settings
        self.webPage = webPage

    @pyqtSlot(dict)
    def loadJSONObject(self, obj):
        # display the content of the object in the debug element
        if DEBUG_MODE == 2:
            self.runScript("document.getElementById('debug').innerHTML = '{}';".format(str(obj)[:500].replace("'", "\\'")))

        self.webPage.sendData(obj)

    @pyqtSlot(str, str)
    def runScript(self, string, message=""):
        self.webPage.runScript(string, message, sourceID="q3dwindow.py")

    @pyqtSlot(str)
    def loadScriptFile(self, filepath):
        self.webPage.loadScriptFile(filepath)

    @pyqtSlot()
    def loadModelLoaders(self):
        self.webPage.loadModelLoaders()

    # @pyqtSlot(str, int, bool)     # pyqtSlot override bug in PyQt5?
    def showMessage(self, msg, _1=0, _2=False):
        logMessage(msg)

    # @pyqtSlot(int, str)
    def progress(self, percentage=100, text=None):
        pass
