# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Qgis2threejs
                                 A QGIS plugin
 export terrain and map image into web browser
                             -------------------
        begin                : 2014-01-11
        copyright            : (C) 2014 by Minoru Akagi
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
from PyQt4.QtGui import QColor
from qgis.core import QGis
import sys
import random
from vectorstylewidgets import *

debug_mode = 1
colorNames = []

def list_modules():
  for nam, mod in sys.modules.items():
    qDebug(nam + ": " + str(mod))

class ObjectTypeModule:
  def __init__(self, module):
    self.module = module
    self.geometryType = getattr(module, 'geometryType')()
    self.objectTypeNames = getattr(module, 'objectTypeNames')()
    self.setupForm = getattr(module, 'setupForm')     # setupForm(dialog, mapTo3d, layer, type_index=0)
    self.write = getattr(module, 'write')   # write(mapTo3d, pt(s), properties, layer=None, f=None)

  @classmethod
  def load(self, modname):
    if modname in sys.modules:
      module = reload(sys.modules[modname])
    else:
      module = __import__(modname)
      for comp in modname.split(".")[1:]:
        module = getattr(module, comp)
    return ObjectTypeModule(module)

class ObjectTypeItem:
  def __init__(self, name, mod_index, type_index):
    self.name = name
    self.mod_index = mod_index
    self.type_index = type_index

class ObjectTypeManager:
  def __init__(self):
    # load basic object types
    self.modules = []
    self.objTypes = {QGis.Point: [], QGis.Line: [], QGis.Polygon:[]}    # each list item is ObjectTypeItem object

    module_names = ["Qgis2threejs.objects.point_basic", "Qgis2threejs.objects.line_basic", "Qgis2threejs.objects.polygon_basic"]
    for modname in module_names:
      mod = ObjectTypeModule.load(modname)
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

  def module(self, geom_type, item_index):
    if geom_type in self.objTypes:
      return self.modules[self.objTypes[geom_type][item_index].mod_index]
    return None

  def setupForm(self, dialog, mapTo3d, layer, geom_type, item_index):
    if geom_type in self.objTypes:
      return self.module(geom_type, item_index).setupForm(dialog, mapTo3d, layer, self.objTypes[geom_type][item_index].type_index)
    return False

class VectorObjectProperties:

  def __init__(self, prop_dict=None):
    if prop_dict is None:
      self.prop_dict = []
      self.visible = False
    else:
      self.prop_dict = prop_dict
      self.item_index = prop_dict["itemindex"]
      typeitem = prop_dict["typeitem"]
      self.type_name = typeitem.name
      self.type_index = typeitem.type_index
      self.visible = prop_dict["visible"]
    self.layer = None

  def color(self, layer=None, f=None):
    global colorNames
    vals = self.prop_dict["color"]
    if vals[0] == ColorWidgetFunc.RGB:
      return vals[2]
    elif vals[0] == ColorWidgetFunc.RANDOM or layer is None or f is None:
      if len(colorNames) == 0:
        colorNames = QColor.colorNames()
      colorName = random.choice(colorNames)
      colorNames.remove(colorName)
      return QColor(colorName).name().replace("#", "0x")
    return layer.rendererV2().symbolForFeature(f).color().name().replace("#", "0x")

  def isHeightRelativeToSurface(self):
    return self.prop_dict["height"][0] == HeightWidgetFunc.RELATIVE

  def relativeHeight(self, f=None):
    lst = self.prop_dict["height"]
    if lst[0] in [HeightWidgetFunc.RELATIVE, HeightWidgetFunc.ABSOLUTE] or f is None:
      return float(lst[2])
    # attribute value + addend
    return float(f.attribute(lst[1])) + float(lst[2])

  def values(self, f=None):
    vals = []
    for i in range(32):   # big number for style count
      if i in self.prop_dict:
        lst = self.prop_dict[i]
        if lst[0] == FieldValueWidgetFunc.ABSOLUTE or f is None:
          vals.append(lst[2])
        else:
          # attribute value * multiplier
          vals.append(str(float(f.attribute(lst[1])) * float(lst[2])))
      else:
        break
    return vals
