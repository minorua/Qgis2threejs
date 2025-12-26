# -*- coding: utf-8 -*-
# (C) 2023 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later
# begin: 2023-11-10

from qgis.PyQt.QtCore import Qt, QObject
from qgis.PyQt.QtWidgets import QLabel, QVBoxLayout, QWidget
from qgis.PyQt.QtGui import QPixmap

from ..utils import logger, pluginDir


class Q3DFallbackView(QWidget):
    """A fallback view displayed when web view is unavailable."""

    def __init__(self, parent):
        super().__init__(parent)
        self._page = Q3DFallbackPage(self)

        url = "https://github.com/minorua/Qgis2threejs/wiki/How-to-use-Qt-WebEngine-view-with-Qgis2threejs"

        msg1 = QLabel(self)
        msg1.setText("PyQt-WebEngine is not installed. See <a href='{}'>wiki page</a> for details.".format(url))
        msg1.setAlignment(Qt.AlignmentFlag.AlignCenter)
        msg1.setOpenExternalLinks(True)

        msg2 = QLabel(self)
        msg2.setText("WebEngine modules are unavailable. The preview has been disabled.")
        msg2.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icon = QLabel(self)
        icon.setPixmap(QPixmap(pluginDir("Qgis2threejs.png")))
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setDisabled(True)

        layout = QVBoxLayout()
        layout.addStretch(1)
        layout.addWidget(msg1)
        layout.addWidget(msg2)
        layout.addStretch(1)
        layout.addWidget(icon)
        layout.addStretch(3)
        self.setLayout(layout)

    def teardown(self):
        pass

    def page(self):
        return self._page

    def reload(self):
        pass

    def showDevTools(self):
        pass

    def disableWidgetsAndMenus(self, ui):
        objs = [ui.checkBoxPreview, ui.menuSaveAs, ui.actionReload,
                ui.actionResetCameraPosition, ui.actionDevTools, ui.actionUsage]

        for obj in objs:
            obj.setEnabled(False)

    def __bool__(self):
        """Fallback view represents absence of a usable Web view."""
        return False


class Q3DFallbackPage(QObject):
    """No-op fallback page used when the Web page is unavailable."""

    def __bool__(self):
        """Fallback page represents absence of a usable Web page."""
        return False

    def __getattr__(self, name):
        logger.debug("Q3DFallbackPage.{} referenced".format(name))
        return self._func

    def _func(self, *args1, **args2):
        pass
