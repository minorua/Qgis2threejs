# -*- coding: utf-8 -*-
# (C) 2026 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later

import os
import argparse
import logging
import sys
import traceback

from PyQt6.QtCore import Qt, QPointF, QTimer, qDebug
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout

from . import conf
conf.WEBVIEW_IN_QGIS_PROCESS = False

from .webbridge import WebIPCBridge
from .webengineview import Q3DWebEnginePage, Q3DWebEngineView
from ..ipc.ipc_const import Event, Request
from ..ipc.socketclient import SocketClient
from ...conf import DEBUG_MODE, PLUGIN_NAME
from ...utils.basic import pluginDir


logger = logging.getLogger(PLUGIN_NAME)


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
            self.sendData(params["data"], viaQueue=params["viaQueue"])

        elif method == Request.REMOVE_LAYER_DATA:
            self.sendQueue.removeLayer(params["jsLayerId"])

        elif method == Request.CLEAR_QUEUE:
            self.sendQueue.clear()

        elif method == Request.RELOAD:
            self.reload()

        else:
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

    # TODO: fileDropped

    def __init__(self, parent, serverName):
        Q3DWebEngineView.__init__(self, parent)

        self.socketClient = SocketClient(self, serverName)
        self.socketClient.notified.connect(self.notified)
        self.socketClient.requestReceived.connect(self.requestReceived)
        self.socketClient.responseReceived.connect(self.responseReceived)

        self._page.setSocketClient(self.socketClient)

        self.devToolsClosed.connect(self.notifyDevToolsClosed)

    def setup(self, webViewMode=None, enabledAtStart=True):
        super().setup(enabledAtStart=enabledAtStart)
        self.socketClient.connect()

    def notified(self, method, params, payload):
        if method == Event.DEV_TOOLS:
            self.showDevTools()

        elif method == Event.GPU_INFO:
            self.showGPUInfo()

        elif method == Event.CLICK:
            self.triggerTestClick(QPointF(params["x"], params["y"]))

    def requestReceived(self, id, method, params, payload):
        if method == Request.SIZE:
            size = self.size()
            self.socketClient.respond(id, method, {"width": size.width(), "height": size.height()})

    def responseReceived(self, id, method, params, payload):
        pass

    def handle_exception(self, exc_type, exc_value, exc_traceback):
        msg = "[Preview]" + "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        self.socketClient.notify(Event.PY_ERROR, params={"msg": msg})

    def notifyDevToolsClosed(self):
        self.socketClient.notify(Event.DEV_TOOLS_CLOSED)


class Window(QWidget):

    def __init__(self, serverName, embedMode=True, pid=None):
        self.timer = None
        super().__init__()

        if embedMode:
            self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)
        else:
            self.timer = QTimer(self)
            self.timer.setSingleShot(True)
            self.timer.setInterval(1000)
            self.timer.timeout.connect(self.notifyWndGeometry)

            self.setWindowTitle("Qgis2threejs Preview")
            self.setWindowFlags(Qt.WindowType.Window)
            self.setMinimumSize(400, 300)

        self.embedMode = embedMode

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.webView = WebView(self, serverName)
        self.webView.socketClient.connected.connect(self.connected)
        self.webView.socketClient.notified.connect(self.notified)
        self.webView.socketClient.requestReceived.connect(self.requestReceived)
        self.webView.setup()
        layout.addWidget(self.webView)

    def moveEvent(self, event):
        if self.timer:
            self.timer.start()
        QWidget.moveEvent(self, event)

    def resizeEvent(self, event):
        if self.timer:
            self.timer.start()
        QWidget.resizeEvent(self, event)

    def notifyWndGeometry(self):
        rect = self.geometry()
        self.webView.socketClient.notify(Event.WND_GEOM_CHANGED, {"x": rect.x(), "y": rect.y(), "width": rect.width(), "height": rect.height()})

    def connected(self):
        if self.embedMode:
            self.webView.socketClient.request(Request.EMBED_WND, {"winId": int(self.winId())})

    def notified(self, method, params, payload):
        if method == Event.QUIT:
            logger.info("Closing...")
            self.close()

    def requestReceived(self, id, method, params, payload):
        if method == Request.RESIZE:
            self.resize(params["width"], params["height"])
            self.webView.socketClient.respond(id, method)


class ConditionalPrefixFilter(logging.Filter):
    def filter(self, record):
        msg = record.getMessage()
        if not msg.startswith('['):
            record.msg = f"[ * ] {msg}"
            record.args = ()
        return True


class QDebugHandler(logging.Handler):
    def emit(self, record):
        msg = self.format(record)
        qDebug(msg.encode("utf-8"))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--server", type=str, help="Server name", required=True)
    parser.add_argument("-p", "--pid", type=int, help="Parent process ID")
    parser.add_argument("-f", "--floating", action="store_true", help="Floating mode")
    parser.add_argument("--x", type=int, default=None, help="Window x position")
    parser.add_argument("--y", type=int, default=None, help="Window y position")
    parser.add_argument("--width", type=int, default=None, help="Window width")
    parser.add_argument("--height", type=int, default=None, help="Window height")
    args = parser.parse_args()

    # logging
    formatter = logging.Formatter("[%(levelname)s]%(message)s")

    handlers = []
    if DEBUG_MODE:
        handler = QDebugHandler()
        handler.addFilter(ConditionalPrefixFilter())
        handler.setFormatter(formatter)
        handlers.append(handler)

    logging.basicConfig(
        level=logging.DEBUG if DEBUG_MODE else logging.INFO,
        handlers=handlers
    )

    logger.debug("PYTHONPATH: %s", os.environ.get("PYTHONPATH"))
    logger.debug(f"sys.path: {sys.path}")
    logger.debug("=" * 20)
    logger.debug(f"pid : {os.getpid()}")
    logger.debug(f"args: {sys.argv}")
    logger.debug(f"vars: {vars(args)}")

    # os.environ["QTWEBENGINE_CHROMIUM_FLAGS"] = "--enable-logging --v=1"

    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(pluginDir("Qgis2threejs.png")))

    window = Window(serverName=args.server, embedMode=not args.floating, pid=args.pid)
    if args.x is not None and args.y is not None and args.width and args.height:
        window.setGeometry(args.x, args.y, args.width, args.height)

    sys.excepthook = window.webView.handle_exception

    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
