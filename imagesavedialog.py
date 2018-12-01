# -*- coding: utf-8 -*-
"""
/***************************************************************************
 ImageSaveDialog

                              -------------------
        begin                : 2018-11-29
        copyright            : (C) 2018 Minoru Akagi
        email                : akaginch@gmail.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
from PyQt5.QtCore import QDir
from PyQt5.QtWidgets import QApplication, QDialog, QFileDialog, QMessageBox

from .export import ImageExporter
from .q3dviewercontroller import Q3DViewerController
from .qgis2threejstools import logMessage
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
    height = self.ui.spinBox_Height.setValue(size.height())

  def renderImage(self):
    width = self.ui.spinBox_Width.value()
    height = self.ui.spinBox_Height.value()
    return self.wnd.ui.webView.page().renderImage(width, height)

    ###############
    # in other way
    controller = Q3DViewerController(self.wnd.qgisIface)
    controller.settings = self.wnd.settings

    # create an exporter
    exporter = ImageExporter(controller)
    exporter.initWebPage(width, height)

    # get current camera state
    cameraState = self.wnd.ui.webView.page().cameraState()

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
    filename, _ = QFileDialog.getSaveFileName(self, self.tr("Choose a file name to save scene image as"), QDir.homePath(), "PNG files (*.png)")
    if not filename:
      return

    self.setEnabled(False)

    image = self.renderImage()
    image.save(filename)

    super().accept()
