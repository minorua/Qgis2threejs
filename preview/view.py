# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Qgis2threejs Live Exporter Application

                              -------------------
        begin                : 2016-02-10
        copyright            : (C) 2016 Minoru Akagi
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
import argparse
import sys

from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout
from PyQt6.QtWebEngineWidgets import QWebEngineView

from .socketclient import SocketClient
from .utils import logger, pluginDir


class WebView(QWebEngineView):

    def __init__(self, parent=None):
        super().__init__(parent)
        # self.setUrl(QUrl("chrome://gpu"))
        self.setUrl(QUrl("file:///D:/Users/akagi/Desktop/Airport/index.html"))


class Window(QWidget):

    def __init__(self, serverName, embedMode=True, pid=None):
        super().__init__()

        if embedMode:
            self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)
            # self.setAttribute(Qt.WidgetAttribute.WA_NativeWindow, True)
        else:
            self.setWindowTitle("Qgis2threejs Preview")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.webview = WebView(self)
        layout.addWidget(self.webview)

        self.socketClient = SocketClient(serverName)
        self.socketClient.notified.connect(self.notified)
        self.socketClient.requestReceived.connect(self.requestReceived)
        self.socketClient.responseReceived.connect(self.responseReceived)

    def notified(self, params):
        logger.info(str(params))
        if params.get("name") == "quit":
            logger.info("Closing...")
            self.close()

    def requestReceived(self, params):
        logger.info(str(params))
        if params.get("name") == "winId":
            self.socketClient.notify({"name": "winId", "value": int(self.winId())})     # TODO: use .respond (dataType = json)

    def responseReceived(self, data, meta):
        logger.info(str(meta))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--server", type=str, help="Server name", required=True)
    parser.add_argument("-p", "--pid", type=int, help="Parent process ID")
    parser.add_argument("-f", "--floating", action="store_true", help="Floating mode")
    args = parser.parse_args()

    logger.info(str(sys.argv))
    logger.info(str(vars(args)))
    logger.info(f"Server name: {args.server}")
    logger.info(f"Parent Process ID: {args.pid}")

    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(pluginDir("Qgis2threejs.png")))

    window = Window(serverName=args.server, embedMode=not args.floating, pid=args.pid)
    window.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
