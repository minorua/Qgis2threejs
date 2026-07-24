# -*- coding: utf-8 -*-
# (C) 2026 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later

from qgis.PyQt.QtCore import Qt, QTimer
from qgis.PyQt.QtGui import QPalette, QPixmap, QWindow
from qgis.PyQt.QtWidgets import QLabel, QPushButton, QStackedWidget, QVBoxLayout, QWidget

from .const import PreviewState
from .utils import logger
from ...utils.basic import pluginDir


class WebViewContainer(QStackedWidget):

    def __init__(self, parent):
        super().__init__(parent)

        self.previewStateWidget = PreviewStateWidget(self)
        self.addWidget(self.previewStateWidget)

        self.webView = None
        self.embeddedWnd = None

    def setWebView(self, webView):
        # webView: Q3DWebEngineView (INPROCESS) or Q3DWebViewProxy (EMBEDDED)
        if self.count() != 1:
            raise AssertionError("Web view container has an unexpected number of widgets.")

        if isinstance(webView, QWidget):
            # INPROCESS
            self.addWidget(webView)
        else:
            # EMBEDDED
            self.previewStateWidget.buttonRestart.clicked.connect(webView.startPreview)

        self.webView = webView

    def previewStateChanged(self, state):
        logger.debug(f"previewStateChanged: {state}")
        if state == PreviewState.Active:
            self.showPreview()
        else:
            self.showPreviewState(state)

            if state == PreviewState.Disabled:
                self.removeEmbeddedWnd()

    def showPreview(self):
        if self.count() != 2:
            raise AssertionError("Web view container has an unexpected number of widgets.")

        self.setCurrentIndex(1)

    def showPreviewState(self, state):
        self.previewStateWidget.setState(state)
        self.setCurrentIndex(0)
        self.previewStateWidget.repaint()

    def embedWnd(self, winId):
        self.showPreviewState(PreviewState.Idle)

        self.embeddedWnd = QWindow.fromWinId(winId)
        container = QWidget.createWindowContainer(self.embeddedWnd)

        w = self.widget(1)
        if w:
            w.hide()
            self.removeWidget(w)

        self.addWidget(container)

        logger.debug(f"External window ({winId}) embedded.")

        self.previewStateChanged(PreviewState.Active)

    def removeEmbeddedWnd(self):
        if self.embeddedWnd:
            self.embeddedWnd.hide()
            self.embeddedWnd.setParent(None)
            self.embeddedWnd = None


class PreviewStateWidget(QWidget):

    def __init__(self, parent):
        QWidget.__init__(self, parent)

        self.setAutoFillBackground(True)

        self.msg1 = QLabel(self)
        self.msg1.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.msg2 = QLabel(self)
        self.msg2.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.buttonRestart = QPushButton(self)
        self.buttonRestart.setText("RESTART PREVIEW")
        self.buttonRestart.setStyleSheet("padding: 6px 12px;")
        self.buttonRestart.hide()

        self.icon = QLabel(self)
        self.icon.setPixmap(QPixmap(pluginDir("Qgis2threejs.png")))
        self.icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon.setDisabled(True)
        self.icon.hide()

        layout = QVBoxLayout()
        layout.addStretch(1)
        layout.addWidget(self.msg1)
        layout.addWidget(self.msg2)
        layout.addStretch(1)
        layout.addWidget(self.buttonRestart, 0, Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(self.icon)
        layout.addStretch(3)

        self.setLayout(layout)

        self.timer = QTimer(self)
        self.timer.setInterval(100)
        self.timer.timeout.connect(self.timeout)

        self.currentMsg1 = self.currentMsg2 = ""
        self.currentState = PreviewState.Idle
        self.dots = 0

    def setState(self, state):
        if state == self.currentState:
            return

        self.timer.stop()
        self.buttonRestart.hide()
        self.icon.hide()

        msg1 = msg2 = ""
        bgcolor = None
        match state:
            case PreviewState.Loading:
                msg1 = "PREPARING PREVIEW"
                bgcolor = Qt.GlobalColor.white

                self.dots = 0
                self.timer.start()

            case PreviewState.Error:
                msg1 = "PREVIEW STOPPED UNEXPECTEDLY.\nTHE CONNECTION WAS LOST."
                self.buttonRestart.show()

            case PreviewState.Disabled:
                self.icon.show()

        if bgcolor is None:
            bgcolor = self.palette().color(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Button)

        self.msg1.setText(msg1)
        self.msg2.setText(msg2)
        self.setBackgroundColor(bgcolor)

        self.currentState = state
        self.currentMsg1 = msg1
        self.currentMsg2 = msg2

    def timeout(self):
        self.dots = (self.dots + 1) % 4

        dots = "." * self.dots + " " * (3 - self.dots)
        self.msg1.setText(self.currentMsg1 + " " + dots)

    def setBackgroundColor(self, color):
        pal = self.palette()
        pal.setColor(QPalette.ColorRole.Window, color)
        self.setPalette(pal)
