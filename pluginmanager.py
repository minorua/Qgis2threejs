# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Qgis2threejs
                                 A QGIS plugin
 export terrain data, map canvas image and vector data to web browser
                              -------------------
        begin                : 2015-05-22
        copyright            : (C) 2015 Minoru Akagi
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
import sys

from PyQt4.QtCore import QDir, QFile, QSettings
from qgis2threejstools import logMessage

class PluginManager:

  def __init__(self):
    self.reloadPlugins()

  def reloadPlugins(self):
    self.modules = []
    self.plugins = []

    allPlugins = False
    if allPlugins:
      plugin_dir = QDir(os.path.join(os.path.dirname(QFile.decodeName(__file__)), "plugins"))
      plugins = plugin_dir.entryList(QDir.Dirs | QDir.NoSymLinks | QDir.NoDotAndDotDot)
    else:
      p = QSettings().value("/Qgis2threejs/plugins", "", type=unicode)
      plugins = p.split(",") if p else []

    import importlib
    for name in plugins:
      try:
        modname = "Qgis2threejs.plugins." + str(name)
        module = reload(sys.modules[modname]) if modname in sys.modules else importlib.import_module(modname)
        self.modules.append(module)
        self.plugins.append(getattr(module, "plugin_class"))
      except ImportError:
        logMessage("Failed to load plugin: " + str(name))

  def demProviderPlugins(self):
    plugins = []
    for plugin in self.plugins:
      if plugin.type() == "demprovider":
        plugins.append(plugin)
    return plugins

  def findDEMProvider(self, id):
    for plugin in self.plugins:
      if plugin.type() == "demprovider" and plugin.providerId() == id:
        return plugin.providerClass()
    return None
