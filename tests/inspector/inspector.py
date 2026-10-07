# -*- coding: utf-8 -*-
# (C) 2026 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later

"""Test app for inspecting an exported web page with QWebEngineView.

Usage:
    python inspector.py <page.html> [--timeout SEC] [--port PORT]

- Serves the directory containing the HTML file with an HTTP server in a separate thread.
- Prints browser console messages to stdout.
- Reads JavaScript code from stdin and evaluates it in the page.
- Exits automatically after --timeout seconds (0 to disable) unless the "Cancel auto-exit" button is pressed.
"""
import argparse
import functools
import json
import os
import sys
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

from PyQt6.QtCore import QTimer, QUrl, pyqtSignal
from PyQt6.QtWebEngineCore import QWebEnginePage
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWidgets import QApplication, QHBoxLayout, QLineEdit, QPushButton, QVBoxLayout, QWidget

LEVELS = {
    QWebEnginePage.JavaScriptConsoleMessageLevel.InfoMessageLevel: "INFO",
    QWebEnginePage.JavaScriptConsoleMessageLevel.WarningMessageLevel: "WARNING",
    QWebEnginePage.JavaScriptConsoleMessageLevel.ErrorMessageLevel: "ERROR",
}


def out(text):
    sys.stdout.write(text + "\n")
    sys.stdout.flush()


class RequestHandler(SimpleHTTPRequestHandler):

    def log_request(self, code="-", size="-"):
        out(f'[server] "{self.requestline}" {getattr(code, "value", code)}')

    def log_error(self, format, *args):
        out("[server] ERROR " + format % args)


def startServer(root, port=0):
    handler = functools.partial(RequestHandler, directory=root)
    server = ThreadingHTTPServer(("127.0.0.1", port), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


class ConsoleLoggingPage(QWebEnginePage):

    def javaScriptConsoleMessage(self, level, message, lineNumber, sourceID):
        message = message.replace("\\", "\\\\").replace("\r", "").replace("\n", "\\n")
        out(f'[console] {LEVELS.get(level, "INFO")} {sourceID}:{lineNumber} {message}')


class StdinReader(threading.Thread):

    def __init__(self, callback):
        super().__init__(daemon=True)
        self.callback = callback

    def run(self):
        for line in sys.stdin:
            line = line.strip()
            if line:
                self.callback(line)


class Inspector(QWidget):

    scriptReceived = pyqtSignal(str)

    def __init__(self, url, timeout):
        super().__init__()
        self.setWindowTitle("Web Page Inspector")
        self.resize(1024, 768)

        self.view = QWebEngineView()
        self.page = ConsoleLoggingPage(self.view)
        self.view.setPage(self.page)

        self.urlBox = QLineEdit(url)
        self.devToolsBtn = QPushButton("Dev tools")
        self.cancelBtn = QPushButton("Cancel auto-exit")

        top = QHBoxLayout()
        top.addWidget(self.urlBox, 1)
        top.addWidget(self.devToolsBtn)
        top.addWidget(self.cancelBtn)

        layout = QVBoxLayout(self)
        layout.addLayout(top)
        layout.addWidget(self.view, 1)

        self.view.loadFinished.connect(self.onLoadFinished)
        self.view.urlChanged.connect(lambda u: self.urlBox.setText(u.toString()))
        self.devToolsBtn.clicked.connect(self.openDevTools)
        self.urlBox.returnPressed.connect(lambda: self.view.load(QUrl.fromUserInput(self.urlBox.text())))
        self.scriptReceived.connect(self.runScript)

        self.devToolsView = None
        self.loaded = False
        self.pending = []

        self.timer = None
        if timeout > 0:
            self.timer = QTimer(self)
            self.timer.setSingleShot(True)
            self.timer.timeout.connect(self.close)
            self.timer.start(int(timeout * 1000))
            self.cancelBtn.clicked.connect(self.cancelAutoExit)
        else:
            self.cancelBtn.setEnabled(False)

        self.view.load(QUrl(url))

    def openDevTools(self):
        if not self.devToolsView:
            self.devToolsView = QWebEngineView()
            self.devToolsView.setWindowTitle("Web Page Inspector - Dev tools")
            self.devToolsView.resize(1024, 768)
            self.page.setDevToolsPage(self.devToolsView.page())

        self.devToolsView.show()
        self.devToolsView.raise_()
        self.devToolsView.activateWindow()

    def cancelAutoExit(self):
        self.timer.stop()
        self.cancelBtn.setEnabled(False)
        out("[cancel-auto-exit]")

    def onLoadFinished(self, ok):
        out("[pageload] {}".format("finished" if ok else "failed"))
        self.loaded = True

        for code in self.pending:
            self.runScript(code)
        self.pending = []

    def runScript(self, code):
        if self.loaded:
            self.page.runJavaScript(code, lambda result: out("[result] " + json.dumps(result, default=str)))
        else:
            self.pending.append(code)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("html", help="HTML file to open")
    parser.add_argument("--timeout", type=float, default=60, help="auto-exit timeout in seconds (0: disable)")
    parser.add_argument("--port", type=int, default=0, help="HTTP server port (0: auto)")
    args = parser.parse_args()

    path = os.path.abspath(args.html)
    if not os.path.isfile(path):
        sys.exit("File not found: " + path)

    server = startServer(os.path.dirname(path), args.port)
    url = "http://127.0.0.1:{}/{}".format(server.server_address[1], os.path.basename(path))

    app = QApplication(sys.argv[:1])
    win = Inspector(url, args.timeout)
    win.show()
    StdinReader(win.scriptReceived.emit).start()

    ret = app.exec()
    server.shutdown()
    sys.exit(ret)


if __name__ == "__main__":
    main()
