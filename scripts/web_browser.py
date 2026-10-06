# -*- coding: utf-8 -*-
# (C) 2026 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later

"""Simple web browser built with PyQt6 and QWebEngineView.

Usage:
    python web_browser.py [url]
"""
import argparse
import sys

from PyQt6.QtCore import QUrl
from PyQt6.QtWidgets import QApplication, QHBoxLayout, QLineEdit, QMainWindow, QPushButton, QVBoxLayout, QWidget
from PyQt6.QtWebEngineWidgets import QWebEngineView


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("url", nargs="?", default="http://127.0.0.1:80/")
    args = parser.parse_args()

    app = QApplication(sys.argv[:1])

    window = QMainWindow()
    window.setWindowTitle("Web Browser")
    window.resize(1024, 768)

    view = QWebEngineView()
    dev_tools_view = None

    central_widget = QWidget()
    layout = QVBoxLayout(central_widget)

    address_bar = QLineEdit()
    address_bar.setPlaceholderText("Enter URL")
    dev_tools_button = QPushButton("Dev tools")

    top = QHBoxLayout()
    top.addWidget(address_bar, 1)
    top.addWidget(dev_tools_button)

    layout.addLayout(top)
    layout.addWidget(view)
    window.setCentralWidget(central_widget)

    def navigate():
        view.setUrl(QUrl.fromUserInput(address_bar.text()))

    def open_dev_tools():
        nonlocal dev_tools_view
        if dev_tools_view is None:
            dev_tools_view = QWebEngineView()
            dev_tools_view.setWindowTitle("Web Browser - Dev tools")
            dev_tools_view.resize(1024, 768)
            view.page().setDevToolsPage(dev_tools_view.page())

        dev_tools_view.show()
        dev_tools_view.raise_()
        dev_tools_view.activateWindow()

    view.urlChanged.connect(lambda url: address_bar.setText(url.toString()))
    address_bar.returnPressed.connect(navigate)
    dev_tools_button.clicked.connect(open_dev_tools)

    if args.url:
        address_bar.setText(args.url)
        navigate()

    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
