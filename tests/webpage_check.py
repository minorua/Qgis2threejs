# -*- coding: utf-8 -*-
# (C) 2025 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later

import logging
from qgis.PyQt.QtCore import QEventLoop, QTimer, QUrl
from qgis.PyQt.QtGui import QImage, QPainter
from qgis.PyQt.QtTest import QSignalSpy
from qgis.PyQt.QtWebEngineWidgets import QWebEngineView

from .cli.utils import logger
from ..gui.webview.webengineview import QWebEnginePage, setChromiumFlags


class WebEnginePage(QWebEnginePage):

    def javaScriptConsoleMessage(self, level, message, lineNumber, sourceID):
        CML = QWebEnginePage.JavaScriptConsoleMessageLevel

        logging_level = {
            CML.InfoMessageLevel: logging.INFO,
            CML.WarningMessageLevel: logging.WARNING,
            CML.ErrorMessageLevel: logging.ERROR
        }.get(level, logging.DEBUG)

        text = message
        if sourceID:
            text += f"\t({sourceID.split('/')[-1]}:{lineNumber})"

        logger.log(logging_level, text + " (Web)")

    def runScript(self, string, wait=True):
        if not wait:
            self.runJavaScript(string)
            return

        loop = QEventLoop()
        result = None

        def runJavaScriptCallback(res):
            nonlocal result
            result = res
            loop.quit()

        self.runJavaScript(string, runJavaScriptCallback)

        QTimer.singleShot(5000, loop.quit)
        loop.exec()

        return result


class WebPageCheckerBase(QWebEngineView):

    def __init__(self, url, size=None, parent=None):
        setChromiumFlags()

        super().__init__(parent)

        self._url = QUrl(url)
        self._page = WebEnginePage(self)
        self.setPage(self._page)
        self.show()

        if size:
            self.setFixedSize(size)

        self._loadPage()

    def _loadPage(self):
        spy = QSignalSpy(self.loadFinished)

        self.setUrl(self._url)
        if spy.wait(10000):
            logger.debug("Page load finished.")
        else:
            logger.error("Time out while loading page.")

    def runScript(self, string, wait=True):
        return self._page.runScript(string, wait=wait)

    def waitForSceneLoadFinished(self):
        # wait until scene has finished loading.
        loop = QEventLoop()
        timer = QTimer()
        timer.timeout.connect(loop.quit)
        timer.start(100)

        while True:
            scene_loaded = self.runScript("app.sceneLoaded")
            if scene_loaded:
                break
            loop.exec()

        timer.stop()
        logger.debug("Scene finished loading.")

    def renderScene(self):
        self.runScript("app.render();")
        logger.debug("Scene rendered.")

        loop = QEventLoop()
        timer = QTimer()
        timer.timeout.connect(loop.quit)
        timer.start(1000)
        loop.exec()


class WebPageCapturer(WebPageCheckerBase):

    def capture(self):
        # capture page
        image = QImage(self.size(), QImage.Format.Format_ARGB32_Premultiplied)
        painter = QPainter(image)
        self.render(painter)
        painter.end()

        logger.debug("Page captured.")

        return image

    def captureToFile(self, filename):
        image = self.capture()
        image.save(filename)

        logger.info(f"Image saved to: {filename}")
