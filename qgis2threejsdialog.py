# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Qgis2threejsDialog
                                 A QGIS plugin
 export terrain and map image into web browser
                             -------------------
        begin                : 2013-12-21
        copyright            : (C) 2013 by Minoru Akagi
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

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from ui_qgis2threejsdialog import Ui_Qgis2threejsDialog

class Qgis2threejsDialog(QDialog):
  def __init__(self, iface):
    QDialog.__init__(self)
    self.iface = iface
    # Set up the user interface from Designer.
    self.ui = Ui_Qgis2threejsDialog()
    self.ui.setupUi(self)
    self.ui.toolButton_Browse.clicked.connect(self.browseClicked)

  def accept(self):
    filename = self.ui.lineEdit_OutputFilename.text()
    if filename == "":
      QMessageBox.information(None, "Qgis2threejs", "Please specify output filename")
      return
    if QFileInfo(filename).exists() and QMessageBox.question(None, "Qgis2threejs", "Output file already exists. Overwrite it?", QMessageBox.Ok | QMessageBox.Cancel) != QMessageBox.Ok:
      return

    QDialog.accept(self)

  def browseClicked(self):
    directory = self.ui.lineEdit_OutputFilename.text()
    if directory == "":
      directory = QDir.homePath()
    filename = QFileDialog.getSaveFileName(self, self.tr("Output filename"), directory, "HTML file (*.html *.htm)", options=QFileDialog.DontConfirmOverwrite)
    if filename != "":
      self.ui.lineEdit_OutputFilename.setText(filename)
