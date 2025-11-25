# -*- coding: utf-8 -*-
# (C) 2018 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later
# begin: 2018-11-29

from qgis.PyQt.QtCore import QDir
from qgis.PyQt.QtWidgets import QApplication, QDialog, QFileDialog

# from .export import ImageExporter
from .ui.imagesavedialog import Ui_ImageSaveDialog


class ImageSaveDialog(QDialog):

    def __init__(self, parent):
        QDialog.__init__(self, parent)

        self.wnd = parent

        self.ui = Ui_ImageSaveDialog()
        self.ui.setupUi(self)
        self.ui.pushButton_Copy.clicked.connect(self.copyToClipboard)

        size = self.wnd.ui.webView.size()
        self.ui.spinBox_Width.setValue(size.width())
        self.ui.spinBox_Height.setValue(size.height())

    def copyToClipboard(self):
        self.setEnabled(False)

        width = self.ui.spinBox_Width.value()
        height = self.ui.spinBox_Height.value()

        self.wnd.ui.statusbar.showMessage(self.tr("Rendering..."))
        self.wnd.runScript(f"copyCanvasToClipboard({width}, {height})", wait=True)

        self.setEnabled(True)

    def accept(self):
        # filename, _ = QFileDialog.getSaveFileName(self, self.tr("Choose a file name to save current view as"), QDir.homePath(), "PNG files (*.png)")
        # if not filename:
        #    return

        self.setEnabled(False)

        width = self.ui.spinBox_Width.value()
        height = self.ui.spinBox_Height.value()

        self.wnd.ui.statusbar.showMessage(self.tr("Rendering..."))
        self.wnd.runScript(f"saveCanvasImage({width}, {height})", wait=True)

        QDialog.accept(self)
