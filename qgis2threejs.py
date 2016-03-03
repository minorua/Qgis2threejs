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

from PyQt4.QtCore import QFile, QProcess, Qt    #, QSettings, QTranslator, qVersion
from PyQt4.QtGui import QAction, QIcon, QMessageBox
from qgis.core import QgsProject, QgsMapLayer, QgsMapLayerRegistry, QgsPluginLayerRegistry

from qgis2threejstools import logMessage, removeTemporaryOutputDir


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
    self.pluginManager = None

    self.exportSettings = {}
    self.lastTreeItemData = None
    self.settingsFilePath = None

    # live exporter
    self.controller = None    # Q3DController

    # plugin layer
    self.layers = {}
    self.pluginLayerType = None
    self.lastLayerIndex = 0

  def initGui(self):
    # Create action that will start plugin configuration
    icon = QIcon(os.path.join(self.plugin_dir, "icon.png"))
    self.action = QAction(icon, u"Qgis2threejs", self.iface.mainWindow())
    self.action.setObjectName("Qgis2threejs")

    self.viewerAction = QAction(icon, u"Live Exporter", self.iface.mainWindow())
    self.viewerAction.setObjectName("Qgis2threejsLive")

    self.layerAction = QAction(icon, u"Add Qgis2threejs Layer...", self.iface.mainWindow())
    self.layerAction.setObjectName("Qgis2threejsLayer")

    self.settingAction = QAction(u"Settings", self.iface.mainWindow())
    self.settingAction.setObjectName("Qgis2threejsSettings")

    # connect the action to the run method
    self.action.triggered.connect(self.run)
    self.viewerAction.triggered.connect(self.launchViewer)
    self.layerAction.triggered.connect(self.addPluginLayer)
    self.settingAction.triggered.connect(self.setting)

    # Add toolbar button and web menu items
    name = u"Qgis2threejs"
    self.iface.addWebToolBarIcon(self.action)
    self.iface.addPluginToWebMenu(name, self.action)
    self.iface.addPluginToWebMenu(name, self.viewerAction)
    self.iface.addPluginToWebMenu(name, self.layerAction)
    self.iface.addPluginToWebMenu(name, self.settingAction)

  def unload(self):
    # Remove the web menu items and icon
    name = u"Qgis2threejs"
    self.iface.removeWebToolBarIcon(self.action)
    self.iface.removePluginWebMenu(name, self.action)
    self.iface.removePluginWebMenu(name, self.viewerAction)
    self.iface.removePluginWebMenu(name, self.layerAction)
    self.iface.removePluginWebMenu(name, self.settingAction)

    # remove temporary output directory
    removeTemporaryOutputDir()

  def initManagers(self):
    from vectorobject import ObjectTypeManager
    from pluginmanager import PluginManager
    if self.objectTypeManager is None:
      self.objectTypeManager = ObjectTypeManager()

    if self.pluginManager is None:
      self.pluginManager = PluginManager()

  def run(self):
    from qgis2threejsdialog import Qgis2threejsDialog
    self.initManagers()

    # restore export settings
    proj_path = QgsProject.instance().fileName()
    settingsFilePath = proj_path + ".qto3settings" if proj_path else None

    if not self.exportSettings or settingsFilePath != self.settingsFilePath:
      if settingsFilePath and os.path.exists(settingsFilePath):
        self.loadExportSettings(settingsFilePath)
        logMessage(u"Restored export settings of this project: {0}".format(os.path.basename(proj_path)))    #QgsProject.instance().title()

    dialog = Qgis2threejsDialog(self.iface, self.objectTypeManager, self.pluginManager, self.exportSettings, self.lastTreeItemData)

    # show dialog
    dialog.show()
    ret = dialog.exec_()

    self.exportSettings = dialog.settings(True)

    item = dialog.ui.treeWidget.currentItem()
    self.lastTreeItemData = item.data(0, Qt.UserRole) if item else None

    # if export succeeded, save export settings in the directory that project file exists
    if ret and settingsFilePath:
      self.saveExportSettings(settingsFilePath)

    self.settingsFilePath = settingsFilePath

  def launchViewer(self):
    from viewer.q3dlivecontroller import Q3DLiveController

    self.initManagers()
    pid = str(os.getpid())

    if self.controller is None:
      serverName = "Qgis2threejsLive" + pid
      self.controller = Q3DLiveController(self.iface, self.objectTypeManager, self.pluginManager, serverName)

    logMessage("Launching Live Exporter...")

    parent = self.iface.mainWindow()
    p = QProcess(parent)
    if os.name == "nt":
      os.system("start cmd.exe /c {0} -p {1}".format(os.path.join(self.plugin_dir, "viewer", "q3dapplication.bat"), pid))
      return
      cmd = r"C:\Python34\python.exe"
    else:
      cmd = "python3"
    p.start(cmd, [os.path.join(self.plugin_dir, "viewer", "q3dapplication.py"), "-p", pid])

    if not p.waitForStarted():
      logMessage("Cannot launch Live Exporter (code: {0}).".format(p.error()))

  def addPluginLayer(self):
    from viewer.q3dlayer import Qgis2threejsLayer, Qgis2threejs25DLayerType

    self.initManagers()

    if self.pluginLayerType is None:
      # register plugin layer
      self.pluginLayerType = Qgis2threejs25DLayerType(self)
      QgsPluginLayerRegistry.instance().addPluginLayerType(self.pluginLayerType)

    layer = self.iface.activeLayer()
    valid = True
    if layer is None or layer.type() == QgsMapLayer.PluginLayer:
      valid = False
    elif layer.type() == QgsMapLayer.RasterLayer:
      if layer.providerType() != "gdal" or layer.bandCount() != 1:
        valid = False

    if not valid:
      QMessageBox.information(None, u"Qgis2threejs", "Select a DEM/Vector layer.")
      return

    # create a plugin layer
    self.lastLayerIndex += 1
    serverName = "Qgis2threejsLayer{0}_{1}".format(os.getpid(), self.lastLayerIndex)
    layer = Qgis2threejsLayer(self, serverName)
    QgsMapLayerRegistry.instance().addMapLayer(layer)

    self.layers[layer.id()] = layer   # TODO: remove item from dict when the layer is removed from registry

  def setting(self):
    from settingsdialog import SettingsDialog
    dialog = SettingsDialog(self.iface.mainWindow())
    dialog.show()
    if dialog.exec_():
      from pluginmanager import PluginManager
      self.pluginManager = PluginManager()

  def loadExportSettings(self, filename):
    import json
    with open(filename) as f:
      self.exportSettings = json.load(f)

  def saveExportSettings(self, filename):
    import codecs
    import json
    try:
      with codecs.open(filename, "w", "UTF-8") as f:
        json.dump(self.exportSettings, f, ensure_ascii=False, indent=2, sort_keys=True)
      return True
    except Exception as e:
      logMessage("Failed to save export settings: " + str(e))
      return False
