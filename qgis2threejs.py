# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Qgis2threejs
                                 A QGIS plugin
 export terrain data, map canvas image and vector data to web browser
                              -------------------
        begin                : 2013-12-21
        copyright            : (C) 2013 Minoru Akagi
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
# Import the PyQt and QGIS libraries
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *
# Initialize Qt resources from file resources.py
import resources_rc
# Import the code for the dialog
from qgis2threejsdialog import Qgis2threejsDialog
import qgis2threejstools as tools
import os

debug_mode = 1

class Qgis2threejs:

  def __init__(self, iface):
    # Save reference to the QGIS interface
    self.iface = iface

    # initialize plugin directory
    self.plugin_dir = os.path.dirname(QFile.decodeName(__file__))
    # initialize locale
    locale = QSettings().value("locale/userLocale")[0:2]
    localePath = os.path.join(self.plugin_dir, 'i18n', 'qgis2threejs_{0}.qm'.format(locale))

    if os.path.exists(localePath):
      self.translator = QTranslator()
      self.translator.load(localePath)

      if qVersion() > '4.3.3':
        QCoreApplication.installTranslator(self.translator)

    self.properties = None
    self.lastOutputFilename = ""

  def initGui(self):
    # Create action that will start plugin configuration
    icon = QIcon(":/plugins/qgis2threejs/icon.png")
    self.action = QAction(icon, u"Qgis2threejs", self.iface.mainWindow())
    self.settingAction = QAction(u"Settings", self.iface.mainWindow())

    # connect the action to the run method
    self.action.triggered.connect(self.run)
    self.settingAction.triggered.connect(self.setting)

    # Add toolbar button and web menu items
    self.iface.addWebToolBarIcon(self.action)
    self.iface.addPluginToWebMenu(u"Qgis2threejs", self.action)
    self.iface.addPluginToWebMenu(u"Qgis2threejs", self.settingAction)

  def unload(self):
    # Remove the web menu items and icon
    self.iface.removeWebToolBarIcon(self.action)
    self.iface.removePluginWebMenu(u"Qgis2threejs", self.action)
    self.iface.removePluginWebMenu(u"Qgis2threejs", self.settingAction)

    # remove temporary output directory
    tools.removeTemporaryOutputDir()

  def run(self):
    # create dialog
    dialog = Qgis2threejsDialog(self.iface, self.properties)
    ui = dialog.ui
    ui.lineEdit_OutputFilename.setText(self.lastOutputFilename)

    # show dialog
    dialog.show()
    if dialog.exec_():
      self.lastOutputFilename = ui.lineEdit_OutputFilename.text()

    self.properties = dialog.properties
    if debug_mode:
      qDebug(str(self.properties))
      #with open("M:/properties.txt", "w") as f:
      #  f.write(str(self.properties).replace("}", "}\n\n"))

  def setting(self):
    from settingsdialog import SettingsDialog
    dialog = SettingsDialog(self.iface)
    dialog.show()
    dialog.exec_()
