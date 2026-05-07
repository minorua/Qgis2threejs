# -*- coding: utf-8 -*-
# (C) 2026 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later

import os
import json
import logging
import logging as logger
import sys
import traceback

from ..gui import webview_conf
DEBUG_MODE = webview_conf.DEBUG_MODE
webview_conf.WEBVIEW_IN_QGIS_PROCESS = False

USE_QGIS = True
args = []

if __name__ == "__main__":
    import argparse

    class ConditionalPrefixFilter(logging.Filter):

        def filter(self, record):
            msg = record.getMessage()
            if not msg.startswith('['):
                record.msg = f"[ * ] {msg}"
                record.args = ()
            return True


    def handle_exception(exc_type, exc_value, exc_traceback):
        logger.error("".join(traceback.format_exception(exc_type, exc_value, exc_traceback)))

    sys.excepthook = handle_exception

    # logging
    handler = logging.StreamHandler()
    handler.addFilter(ConditionalPrefixFilter())

    formatter = logging.Formatter("[%(levelname)s]%(message)s")
    handler.setFormatter(formatter)

    logging.basicConfig(
        level=logging.DEBUG if DEBUG_MODE else logging.INFO,
        handlers=[handler]
    )

    # args
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--server", type=str, help="Server name", required=True)
    parser.add_argument("-p", "--pid", type=int, help="Parent process ID")
    parser.add_argument("-f", "--floating", action="store_true", help="Floating mode")
    parser.add_argument("--pythonpath", type=str, help="A path to append to sys.path")

    args = parser.parse_args()
    if args.pythonpath:
        sys.path.append(args.pythonpath)


if USE_QGIS:
    from qgis.PyQt.QtCore import QPointF, QTimer, QUrl
    from qgis.PyQt.QtGui import QIcon
    from qgis.PyQt.QtWidgets import QApplication
else:
    from PyQt6.QtCore import QPointF, QTimer, QUrl
    from PyQt6.QtGui import QIcon
    from PyQt6.QtWidgets import QApplication

from .ipc_const import Event, Request
from .utils import pluginDir
from .socketclient import SocketClient

from ..core.exportsettings import ExportSettings
from ..gui.webbridge import WebIPCBridge
from ..gui.webengineview import Q3DWebEnginePage, Q3DWebEngineView
from ..gui.webview import WVM_EXTERNAL_EXPORTER
from ..gui.window import Q3DWindow


class WebPage(Q3DWebEnginePage):

    BridgeClass = WebIPCBridge

    def __init__(self, parent):
        super().__init__(parent)

        self.bridge.methodInvoked.connect(self.bridgeMethodInvoked)
        self.loadStarted.connect(self.pageLoadStarted)

    def setSocketClient(self, socket):
        self.socketClient = socket
        self.socketClient.notified.connect(self.notified)
        self.socketClient.requestReceived.connect(self.requestReceived)
        self.socketClient.responseReceived.connect(self.responseReceived)

    def pageLoadStarted(self):
        self.socketClient.notify(Event.PAGE_LOAD_STARTED)

    def pageLoaded(self, ok):
        logger.debug("Page load finished.")

        super().pageLoaded(ok)
        self.socketClient.notify(Event.PAGE_LOADED, {"ok": ok})

    def bridgeMethodInvoked(self, params):
        self.socketClient.notify(Event.METHOD_INVOKED, params)

    def notified(self, method, params, payload):
        pass

    def requestReceived(self, id, method, params, payload):
        if method == Request.RUN_SCRIPT:
            def callback(result):
                self.socketClient.respond(id, method, params={"result": result})
            self.runScript(params["script"], callback=callback)
            return

        if method == Request.LOAD_DATA:
            data = json.loads(payload) if payload else params.get("data", {})

            if DEBUG_MODE:
                logger.debug(f"Loading data: {json.dumps(data)[:20]}")

            self.sendData(data, viaQueue=params["viaQueue"])

        elif method == Request.RELOAD:
            self.reload()

        else:
            logger.debug(f"Unknown request received: {method}")
            return

        self.socketClient.respond(id, method)

    def responseReceived(self, id, method, params, payload):
        pass

    def javaScriptConsoleMessage(self, level, message, lineNumber, sourceID):
        CML = Q3DWebEnginePage.JavaScriptConsoleMessageLevel
        if level in (CML.WarningMessageLevel, CML.ErrorMessageLevel):
            self.socketClient.notify(Event.JS_ERROR_WARNING, params={"is_error": bool(level == CML.ErrorMessageLevel)})


class WebView(Q3DWebEngineView):

    WebPageClass = WebPage

    def setup(self, webViewMode=None, enabledAtStart=True):
        super().setup(enabledAtStart=enabledAtStart)

        # QTimer.singleShot(3000, self.showGPUInfo)

    def setSocketClient(self, socket):
        self.socketClient = socket
        self.socketClient.notified.connect(self.notified)
        self.socketClient.requestReceived.connect(self.requestReceived)
        self.socketClient.responseReceived.connect(self.responseReceived)

        self._page.setSocketClient(self.socketClient)

    def notified(self, method, params, payload):
        if method == Event.DEV_TOOLS:
            self.showDevTools()

        elif method == Event.GPU_INFO:
            self.showGPUInfo()

        elif method == Event.CLICK:
            self.triggerTestClick(QPointF(params["x"], params["y"]))

    def requestReceived(self, id, method, params, payload):
        pass

    def responseReceived(self, id, method, params, payload):
        pass

    def handle_exception(self, exc_type, exc_value, exc_traceback):
        msg = "[Python]" + "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        self.socketClient.notify(Event.PY_ERROR, params={"msg": msg})

    def notifyDevToolsClosed(self):
        self.socketClient.notify(Event.DEV_TOOLS_CLOSED)


class Window(Q3DWindow):

    WebViewClass = WebView
    InQGISProcess = False

    def __init__(self, serverName):
        self.exportSettings = ExportSettings()
        self.exportSettings.isPreview = True

        super().__init__(qgisIface=None, settings=self.exportSettings, webViewMode=WVM_EXTERNAL_EXPORTER, previewEnabled=True)

        self.socketClient = SocketClient(self, serverName)
        self.webView.setSocketClient(self.socketClient)
        self.socketClient.connect()

    def notified(self, method, params, payload):
        if method == Event.QUIT:
            logger.info("Closing...")
            self.close()


def main():
    logger.debug("PYTHONPATH: %s", os.environ.get("PYTHONPATH"))
    logger.debug(f"sys.path: {sys.path}")
    logger.debug("=" * 20)
    logger.debug(f"pid : {os.getpid()}")
    logger.debug(f"args: {sys.argv}")
    logger.debug(f"vars: {vars(args)}")

    # os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--enable-logging --v=1"

    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(pluginDir("Qgis2threejs.png")))

    window = Window(serverName=args.server)
    # sys.excepthook = window.webView.handle_exception

    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
