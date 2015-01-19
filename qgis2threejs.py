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
import os

from PyQt4.QtCore import QCoreApplication, QFile, qDebug    #, QSettings, QTranslator, qVersion
from PyQt4.QtGui import QAction, QIcon

from qgis2threejstools import removeTemporaryOutputDir

debug_mode = 1

class Qgis2threejs:

  def __init__(self, iface):
    # Save reference to the QGIS interface
    self.iface = iface

    # initialize plugin directory
    self.plugin_dir = os.path.dirname(QFile.decodeName(__file__))

    # initialize locale
    #locale = QSettings().value("locale/userLocale")[0:2]
    #localePath = os.path.join(self.plugin_dir, 'i18n', 'qgis2threejs_{0}.qm'.format(locale))

    #if os.path.exists(localePath):
    #  self.translator = QTranslator()
    #  self.translator.load(localePath)

    #  if qVersion() > '4.3.3':
    #    QCoreApplication.installTranslator(self.translator)

    self.objectTypeManager = None
    self.properties = None
    self.lastOutputFilename = ""

  def initGui(self):
    # Create action that will start plugin configuration
    icon = QIcon(os.path.join(self.plugin_dir, "icon.png"))
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
    removeTemporaryOutputDir()

  def run(self):
    from vectorobject import ObjectTypeManager
    from qgis2threejsdialog import Qgis2threejsDialog

    if self.objectTypeManager is None:
      self.objectTypeManager = ObjectTypeManager()
    dialog = Qgis2threejsDialog(self.iface, self.objectTypeManager, self.properties)

    ui = dialog.ui
    ui.lineEdit_OutputFilename.setText(self.lastOutputFilename)

    # show dialog
    dialog.show()
    if dialog.exec_():
      self.lastOutputFilename = ui.lineEdit_OutputFilename.text()

    self.properties = dialog.properties

  def setting(self):
    from settingsdialog import SettingsDialog
    dialog = SettingsDialog(self.iface)
    dialog.show()
    dialog.exec_()

  def loadProperties(self, filename):
    import json
    with open(filename) as f:
      self.properties = json.load(f)

  def saveProperties(self, filename):
    import codecs
    import json
    with codecs.open(filename, "w", "UTF-8") as f:
      json.dump(self.properties, f, ensure_ascii=False)
