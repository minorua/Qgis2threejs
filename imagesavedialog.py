# -*- coding: utf-8 -*-
# (C) 2018 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later
# begin: 2018-11-29

from PyQt5.QtCore import QDir
from PyQt5.QtWidgets import QApplication, QDialog, QFileDialog

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

    def renderImage(self, callback):
        width = self.ui.spinBox_Width.value()
        height = self.ui.spinBox_Height.value()
        self.wnd.ui.webView.renderImage(width, height, callback, self.wnd)

    def copyToClipboard(self):
        self.setEnabled(False)

        def callback(image):
            QApplication.clipboard().setImage(image)

            self.setEnabled(True)
            self.wnd.ui.statusbar.showMessage(self.tr("Image has been rendered and copied to clipboad."), 5000)

        self.renderImage(callback)

    def accept(self):
        filename, _ = QFileDialog.getSaveFileName(self, self.tr("Choose a file name to save current view as"), QDir.homePath(), "PNG files (*.png)")
        if not filename:
            return

        self.setEnabled(False)

        if not filename.lower().endswith(".png"):       # fix for #278
            filename += ".png"

        def callback(image):
            image.save(filename)

            self.wnd.ui.statusbar.showMessage(self.tr("Image has been saved to file."), 5000)
            QDialog.accept(self)

        self.renderImage(callback)
