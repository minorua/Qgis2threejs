# -*- coding: utf-8 -*-
# (C) 2022 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later

from qgis.PyQt.QtCore import QDir
from qgis.PyQt.QtWidgets import QDialog, QDialogButtonBox, QFileDialog, QVBoxLayout

from qgis.gui import QgsCompoundColorWidget


def selectColor(parent=None):
    dlg = QDialog(parent)
    dlg.setWindowTitle("Select a color")
    dlg.setLayout(QVBoxLayout())

    widget = QgsCompoundColorWidget()
    widget.setAllowOpacity(False)
    dlg.layout().addWidget(widget)

    buttonBox = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
    buttonBox.accepted.connect(dlg.accept)
    buttonBox.rejected.connect(dlg.reject)
    dlg.layout().addWidget(buttonBox)

    if dlg.exec():
        return widget.color()


def selectImageFile(parent=None, directory=None):
    if directory is None:
        directory = QDir.homePath()
    filterString = "Supported image files (*.png *.jpg *.jpeg *.gif *.bmp)"
    filename, _ = QFileDialog.getOpenFileName(parent, "Select an image file", directory, filterString)
    return filename