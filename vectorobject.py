# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Qgis2threejs
                                 A QGIS plugin
 export terrain data, map canvas image and vector data to web browser
                             -------------------
        begin                : 2014-01-11
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
from PyQt4.QtCore import qDebug
from qgis.core import QGis, QgsMessageLog
import sys
from stylewidget import *

debug_mode = 1

def list_modules():
  for nam, mod in sys.modules.items():
    qDebug(nam + ": " + str(mod))

class ObjectTypeModule:
  def __init__(self, module):
    self.module = module
    self.geometryType = getattr(module, 'geometryType')()
    self.objectTypeNames = getattr(module, 'objectTypeNames')()
    self.setupForm = getattr(module, 'setupForm')     # setupForm(dialog, mapTo3d, layer, type_index=0)
    self.write = getattr(module, 'write')             # write(writer, layer, feat)

  @classmethod
  def load(self, modname):
    if modname in sys.modules:
      module = reload(sys.modules[modname])
      return ObjectTypeModule(module)

    module = __import__(modname)
    try:
      for comp in modname.split(".")[1:]:
        module = getattr(module, comp)
      return ObjectTypeModule(module)
    except:
      return None

class ObjectTypeItem:
  def __init__(self, name, mod_index, type_index):
    self.name = name
    self.mod_index = mod_index
    self.type_index = type_index

class ObjectTypeManager:
  def __init__(self):
    # load object types
    self.modules = []
    self.objTypes = {QGis.Point: [], QGis.Line: [], QGis.Polygon:[]}    # each list item is ObjectTypeItem object

    module_names = ["point_basic", "line_basic", "polygon_basic"]
    module_names += ["point_json"]
    module_fullnames = map(lambda x: "Qgis2threejs.objects." + x, module_names)
    for modname in module_fullnames:
      mod = ObjectTypeModule.load(modname)
      if mod is None:
        QMessageBox.warning(None, "Qgis2threejs", "Failed to load the module: {0}\nIf you have just upgraded this plugin, please restart QGIS.".format(modname))
        return
      mod_index = len(self.modules)
      self.modules.append(mod)
      for type_index, name in enumerate(mod.objectTypeNames):
        self.objTypes[mod.geometryType].append(ObjectTypeItem(name, mod_index, type_index))

    if debug_mode:
      qDebug("ObjectTypeManager: " + str(self.objTypes))

  def objectTypeNames(self, geom_type):
    if geom_type in self.objTypes:
      return map(lambda x: x.name, self.objTypes[geom_type])
    return []

  def objectTypeItem(self, geom_type, item_index):
    if geom_type in self.objTypes:
      return self.objTypes[geom_type][item_index]
    return None

  def module(self, mod_index):
    if mod_index < len(self.modules):
      return self.modules[mod_index]
    return None

  def setupForm(self, dialog, mapTo3d, layer, geom_type, item_index):
    try:
      typeitem = self.objTypes[geom_type][item_index]
      return self.modules[typeitem.mod_index].setupForm(dialog, mapTo3d, layer, typeitem.type_index)
    except:
      qDebug("Qgis2threejs: Failed to setup form")
      return False
