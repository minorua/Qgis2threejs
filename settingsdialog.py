# -*- coding: utf-8 -*-
"""
/***************************************************************************
 SettingsDialog
                             -------------------
        begin                : 2014-01-10
        copyright            : (C) 2014 Minoru Akagi
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
from ui_settingsdialog import Ui_SettingsDialog

class SettingsDialog(QDialog):
  def __init__(self, iface):
    QDialog.__init__(self, iface.mainWindow())
    self.iface = iface

    # Set up the user interface from Designer.
    self.ui = ui = Ui_SettingsDialog()
    ui.setupUi(self)
    ui.lineEdit_BrowserPath.setPlaceholderText("Leave this empty to use your default browser")
    ui.toolButton_Browse.clicked.connect(self.browseClicked)

    # load settings
    settings = QSettings()
    self.ui.lineEdit_BrowserPath.setText(settings.value("/Qgis2threejs/browser", "", type=unicode))

  def accept(self):
    # save settings
    settings = QSettings()
    settings.setValue("/Qgis2threejs/browser", self.ui.lineEdit_BrowserPath.text())
    QDialog.accept(self)

  def browseClicked(self):
    filename = QFileDialog.getOpenFileName(self, self.tr("Select browser"))
    if filename != "":
      self.ui.lineEdit_BrowserPath.setText(filename)
