# -*- coding: utf-8 -*-
# (C) 2022 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later

import os
from qgis.PyQt.QtCore import QDir, QUrl
from qgis.PyQt.QtGui import QDesktopServices, QIcon
from qgis.PyQt.QtWidgets import QFileDialog, QStyle
from qgis.core import QgsApplication

from .basic import pluginIconPath
from ..conf import HELP_URL_BASE, PLUGIN_VERSION


def openDirectory(dir_path):
    """Open a directory in the OS default file manager."""
    return QDesktopServices.openUrl(QUrl.fromLocalFile(dir_path))


def openFile(file_path):
    """Open a file using the default application associated with the file type."""
    return QDesktopServices.openUrl(QUrl.fromLocalFile(file_path))


def openUrl(url):
    """Open a URL using the default browser.

    Args:
        url: QUrl object.
    """
    return QDesktopServices.openUrl(url)


def openHelp(queryString=""):
    url = HELP_URL_BASE + "?version=" + PLUGIN_VERSION
    if queryString:
        url += "&" + queryString

    return openUrl(QUrl(url))


def warningIcon():
    if os.name == "nt":
        return QgsApplication.style().standardIcon(QStyle.StandardPixmap.SP_MessageBoxWarning)

    return QgsApplication.getThemeIcon("mIconWarning.svg")


def pluginIcon():
    return QIcon(pluginIconPath())


def selectImageFile(parent=None, directory=None):
    if directory is None:
        directory = QDir.homePath()
    filterString = "Supported image files (*.png *.jpg *.jpeg *.gif *.bmp)"
    filename, _ = QFileDialog.getOpenFileName(parent, "Select an image file", directory, filterString)
    return filename