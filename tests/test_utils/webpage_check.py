# -*- coding: utf-8 -*-
# (C) 2025 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later

import logging
from dataclasses import dataclass
from qgis.PyQt.QtCore import QEventLoop, QTimer, QUrl
from qgis.PyQt.QtGui import QImage, QPainter
from qgis.PyQt.QtWebEngineWidgets import QWebEngineView

from .unit import logger
from ...gui.webengineview import QWebEnginePage, setChromiumFlags


@dataclass
class ConsoleMessage:
    level: str   # "error", "warning", "info"
    message: str
    line: int | None = None
    source: str | None = None


@dataclass
class ErrorCheckResult:
    ok: bool
    errors: list[ConsoleMessage]
    warnings: list[ConsoleMessage]


class WebEnginePage(QWebEnginePage):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.errors: list[ConsoleMessage] = []
        self.warnings: list[ConsoleMessage] = []

    def javaScriptConsoleMessage(self, level, message, lineNumber, sourceID):
        CML = QWebEnginePage.JavaScriptConsoleMessageLevel

        if level == CML.ErrorMessageLevel:
            self.errors.append(ConsoleMessage("error", message, lineNumber, sourceID))
        elif level == CML.WarningMessageLevel:
            self.warnings.append(ConsoleMessage("warning", message, lineNumber, sourceID))

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
        loop = QEventLoop()
        self.loadFinished.connect(loop.quit)

        self.setUrl(self._url)
        QTimer.singleShot(10000, loop.quit)
        loop.exec()

        logger.debug("Page load finished.")

    def runScript(self, string, wait=True):
        return self._page.runScript(string, wait=wait)

    def waitForSceneLoadFinished(self):
        # wait until scene has finished loading.
        loop = QEventLoop()
        timer = QTimer()
        timer.timeout.connect(loop.quit)
        timer.start(100)

        while True:
            scene_loaded = self.runScript("Q3D.application.sceneLoaded")
            if scene_loaded:
                break
            loop.exec()

        timer.stop()
        logger.debug("Scene finished loading.")

    def renderScene(self):
        self.runScript("Q3D.application.render();")
        logger.debug("Scene rendered.")

        loop = QEventLoop()
        timer = QTimer()
        timer.timeout.connect(loop.quit)
        timer.start(1000)
        loop.exec()


class WebPageErrorChecker(WebPageCheckerBase):

    def check(self):
        self.waitForSceneLoadFinished()
        self.renderScene()

        ignore_warnings = [
            "THREE.FileLoader: HTTP Status 0 received.",
            "RENDER WARNING: Render count or primcount is 0."
        ]

        warnings = [w for w in self._page.warnings if not any(i in w.message for i in ignore_warnings)]

        return ErrorCheckResult(
            ok=len(self._page.errors) == 0,
            errors=self._page.errors,
            warnings=warnings,
        )

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
