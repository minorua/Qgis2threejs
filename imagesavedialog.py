# -*- coding: utf-8 -*-
# (C) 2018 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later
# begin: 2018-11-29

from PyQt5.QtCore import QDir
from PyQt5.QtWidgets import QApplication, QDialog, QFileDialog

from .export import ImageExporter
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

    def renderImage(self):
        width = self.ui.spinBox_Width.value()
        height = self.ui.spinBox_Height.value()
        return self.wnd.webPage.renderImage(width, height)

        # in other way
        # create an exporter
        self.wnd.settings.setMapSettings(self.wnd.qgisIface.mapCanvas().mapSettings())
        exporter = ImageExporter(self.wnd.settings)
        exporter.initWebPage(width, height)

        # get current camera state
        cameraState = self.wnd.webPage.cameraState()

        # render image
        image, err = exporter.render(cameraState=cameraState)

        return image

    def copyToClipboard(self):
        self.setEnabled(False)

        image = self.renderImage()
        QApplication.clipboard().setImage(image)

        self.setEnabled(True)
        self.wnd.ui.statusbar.showMessage(self.tr("Image has been rendered and copied to clipboad."), 5000)

    def accept(self):
        filename, _ = QFileDialog.getSaveFileName(self, self.tr("Choose a file name to save current view as"), QDir.homePath(), "PNG files (*.png)")
        if not filename:
            return

        self.setEnabled(False)

        image = self.renderImage()
        image.save(filename)

        self.wnd.ui.statusbar.showMessage(self.tr("Image has been saved to file."), 5000)

        super().accept()
