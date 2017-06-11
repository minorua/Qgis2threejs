# -*- coding: utf-8 -*-
"""
/***************************************************************************
 ExportToWebDialog

                              -------------------
        begin                : 2017-06-11
        copyright            : (C) 2017 Minoru Akagi
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
import os
from PyQt5.Qt import Qt
from PyQt5.QtCore import QSettings
from PyQt5.QtWidgets import QDialog, QFileDialog, QMessageBox

from Qgis2threejs.conf import def_vals
from Qgis2threejs.export import ThreeJSFileExporter
from Qgis2threejs.qgis2threejstools import logMessage


class ExportToWebDialog(QDialog):

  def __init__(self, parent, qgisIface, settings, pluginManager=None):
    QDialog.__init__(self, parent)
    self.setAttribute(Qt.WA_DeleteOnClose)

    self.iface = qgisIface
    self.settings = settings
    self.pluginManager = pluginManager

    from .ui5_exporttowebdialog import Ui_ExportToWebDialog
    self.ui = Ui_ExportToWebDialog()
    self.ui.setupUi(self)
    self.ui.pushButton_Browse.clicked.connect(self.browseClicked)
    self.ui.pushButton_Export.clicked.connect(self.exportClicked)
    self.ui.pushButton_Cancel.clicked.connect(self.close)

  def browseClicked(self):
    # directory select dialog
    #TODO: home directory
    d  = QFileDialog.getExistingDirectory(self, self.tr("Select Output Directory"), self.ui.lineEdit_OutputDir.text())
    if d:
      self.ui.lineEdit_OutputDir.setText(d)

  def exportClicked(self):
    outputDir = self.ui.lineEdit_OutputDir.text()
    filetitle = self.ui.lineEdit_FileTitle.text()
    filename = os.path.join(outputDir, filetitle + ".html")

    #TODO: check validity

    if os.path.exists(filename):
      if QMessageBox.question(self, "Qgis2threejs", "HTML file already exists. Overwrite it?", QMessageBox.Ok | QMessageBox.Cancel) != QMessageBox.Ok:
        return

    # output html file path
    self.settings.setOutputFilename(filename)

    # template
    self.settings.setTemplatePath(self.settings.get("Template", def_vals.template))


    err_msg = self.settings.checkValidity()
    if err_msg is not None:
      QMessageBox.warning(self, "Qgis2threejs", err_msg or "Invalid settings")
      return

    self.ui.pushButton_Export.setEnabled(False)
    self.progress(0)

    # export
    exporter = ThreeJSFileExporter(self.settings, self.progress)
    exporter.export()

    self.progress(100)

    # store last settings
    settings = QSettings()
    settings.setValue("/Qgis2threejs/lastTemplate", self.settings.templatePath)
    settings.setValue("/Qgis2threejs/lastControls", self.settings.controls)

    self.close()

  def progress(self, percentage=None, statusMsg=None):
    #TODO
    pass
