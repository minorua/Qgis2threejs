# -*- coding: utf-8 -*-
# (C) 2015 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later

from dataclasses import dataclass
from qgis.PyQt.QtCore import QEventLoop, QSize, QTimer, QUrl
from qgis.PyQt.QtGui import QImage, QPainter
from qgis.PyQt.QtWebKitWidgets import QWebPage

from .unit import logger


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


class WebPageCheckerBase(QWebPage):

    SIZE_WIDTH = 800
    SIZE_HEIGHT = 600

    def __init__(self, url, width=SIZE_WIDTH, height=SIZE_HEIGHT):
        super().__init__()
        self.url = url
        self.setViewportSize(QSize(width, height))
        self._loadPage()

    def _loadPage(self):
        # load the page and wait until page loading is finished
        loop = QEventLoop()
        self.loadFinished.connect(loop.quit)
        self.mainFrame().setUrl(self.url)
        loop.exec()

        logger.debug("Page load finished.")

    def runScript(self, script):
        return self.mainFrame().evaluateJavaScript(script)

    def waitForDataLoadFinished(self):
        # wait until data loading is finished
        loop = QEventLoop()
        timer = QTimer()
        timer.timeout.connect(loop.quit)
        timer.start(100)

        # TODO: loadingManager.isLoading not correct immediately after page load?
        #       This short wait should not be necessary.
        loop.exec()

        while True:
            is_loading = self.runScript("app.loadingManager.isLoading")
            logger.debug(f"Data loading flag: {is_loading}")
            if not is_loading:
                break
            loop.exec()

        timer.stop()
        logger.debug("Data load finished.")

    def renderScene(self):
        self.runScript("app.render();")
        logger.debug("Scene rendered.")

    def javaScriptConsoleMessage(self, message, lineNumber, sourceID):
        text = message
        if sourceID:
            text += f"\t({sourceID.split('/')[-1]}:{lineNumber})"
        logger.debug(text + " (Web)")


class WebPageErrorChecker(WebPageCheckerBase):

    def __init__(self, url, width=WebPageCheckerBase.SIZE_WIDTH, height=WebPageCheckerBase.SIZE_HEIGHT):
        super().__init__(url, width, height)
        self.errors: list[ConsoleMessage] = []
        self.warnings: list[ConsoleMessage] = []

    def check(self):
        self.waitForDataLoadFinished()
        self.renderScene()

        return ErrorCheckResult(
            ok=len(self.errors) == 0,
            errors=self.errors,
            warnings=self.warnings,
        )

    def javaScriptConsoleMessage(self, message, lineNumber, sourceID):
        text = message
        if sourceID:
            text += f"\t({sourceID.split('/')[-1]}:{lineNumber})"

        msg_lower = message.lower()
        if "error" in msg_lower:
            self.errors.append(ConsoleMessage("error", message, lineNumber, sourceID))
            logger.error("JS Error: " + text)
        elif "warning" in msg_lower:
            self.warnings.append(ConsoleMessage("warning", message, lineNumber, sourceID))
            logger.warning("JS Warning: " + text)
        else:
            logger.info("JS Info: " + text)


class WebPageCapturer(WebPageCheckerBase):

    def capture(self):
        # capture page
        image = QImage(self.viewportSize(), QImage.Format.Format_ARGB32_Premultiplied)
        painter = QPainter(image)
        self.mainFrame().render(painter)
        painter.end()

        logger.debug("Page captured.")

        return image

    def captureToFile(self, filename):
        image = self.capture()
        image.save(filename)

        logger.debug(f"Image saved to: {filename}")
