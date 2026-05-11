# -*- coding: utf-8 -*-
# (C) 2023 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later

from qgis.PyQt.QtCore import QObject, pyqtSignal

from .const import WebViewType
from ..utils import logger


class Q3DDummyView(QObject):
    """A dummy view."""

    fileDropped = pyqtSignal(list)

    def __init__(self, parent):
        super().__init__(parent)
        self.webViewType = WebViewType.NONE

        self._page = Q3DDummyPage(self)

    def page(self):
        return self._page

    def setup(self, webViewMode=None, enabledAtStart=True):
        pass

    def teardown(self):
        pass

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
        """Dummy view represents absence of a usable Web view."""
        return False


class Q3DDummyPage:
    """No-op dummy page."""

    def __init__(self, parent):
        pass

    def __bool__(self):
        """Dummy page represents absence of a usable Web page."""
        return False

    def __getattr__(self, name):
        logger.debug("Q3DDummyPage.{} referenced".format(name))
        return self._func

    def _func(self, *args1, **args2):
        pass
