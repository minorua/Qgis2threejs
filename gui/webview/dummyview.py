# -*- coding: utf-8 -*-
# (C) 2023 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later

from qgis.PyQt.QtCore import QObject, QUrl, pyqtSignal

from .utils import logger
from .webviewcommon import Q3DWebPageCommon, Q3DWebViewCommon


class Q3DDummyPage(Q3DWebPageCommon, QObject):

    # QWebEnginePage signals
    loadStarted = pyqtSignal()
    loadFinished = pyqtSignal(bool)

    def __init__(self, parent=None):
        QObject.__init__(self, parent)
        Q3DWebPageCommon.__init__(self, parent)

    def url(self):
        return QUrl()

    def runJavaScript(self, string, callback=None):
        pass

    def __getattr__(self, name):
        logger.debug("Q3DDummyPage.{} referenced".format(name))
        return self._func

    def _func(self, *args1, **args2):
        pass


class Q3DDummyView(Q3DWebViewCommon, QObject):

    def __init__(self, parent):
        QObject.__init__(self, parent)
        Q3DWebViewCommon.__init__(self, parent)

        self._page = Q3DDummyPage(self)
        self._page.setObjectName("DummyPage")

    def page(self):
        return self._page

    def setup(self, webViewMode=None, enabledAtStart=True):
        pass

    def teardown(self):
        pass

    def setPreviewEnabled(self, enabled):
        pass

    def showDevTools(self):
        pass

    def showGPUInfo(self):
        pass

    def triggerTestClick(self, pos):
        pass
