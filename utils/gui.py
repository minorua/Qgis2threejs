# -*- coding: utf-8 -*-
# (C) 2022 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later

from qgis.PyQt.QtCore import QDir, QProcess, QSettings, QUrl
from qgis.PyQt.QtGui import QDesktopServices
from qgis.PyQt.QtWidgets import QFileDialog

from .logging import logger
from ..conf import HELP_URL_BASE, PLUGIN_VERSION


def openDirectory(dir_path):
    """Open a directory in the OS default file manager."""
    QDesktopServices.openUrl(QUrl.fromLocalFile(dir_path))


def openFile(file_path):
    """Open a file using the default application associated with the file type."""
    QDesktopServices.openUrl(QUrl.fromLocalFile(file_path))


def openUrl(url):
    """Open a URL using the default browser.

    Args:
        url: QUrl object.
    """
    QDesktopServices.openUrl(url)


def openHelp(queryString=""):
    url = HELP_URL_BASE + "?version=" + PLUGIN_VERSION
    if queryString:
        url += "&" + queryString

    openUrl(QUrl(url))


def selectImageFile(parent=None, directory=None):
    if directory is None:
        directory = QDir.homePath()
    filterString = "Supported image files (*.png *.jpg *.jpeg *.gif *.bmp)"
    filename, _ = QFileDialog.getOpenFileName(parent, "Select an image file", directory, filterString)
    return filename