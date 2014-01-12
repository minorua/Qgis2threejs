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
    self.setupForm = getattr(module, 'setupForm')     # setupForm(dialog, mapTo3d, layer, obj_type="")
    self.generateJS = getattr(module, 'generateJS')   # generateJS(mapTo3d, pt(s), mat, properties, f=None)

  @classmethod
  def load(self, modname):
    if modname in sys.modules:
      module = reload(sys.modules[modname])
    else:
      module = __import__(modname)
      for comp in modname.split(".")[1:]:
        module = getattr(module, comp)
    return ObjectTypeModule(module)

class ObjectTypeManager:
  def __init__(self):
    # load basic object types
    self.modules = []
    self.objTypes = {QGis.Point: {}, QGis.Line: {}, QGis.Polygon:{}}

    module_names = ["Qgis2threejs.objects.point_basic", "Qgis2threejs.objects.line_basic"]
    for modname in module_names:
      mod = ObjectTypeModule.load(modname)
      for name in mod.objectTypeNames:
        self.objTypes[mod.geometryType][name] = mod
      self.modules.append(mod)

    if debug_mode:
      qDebug("ObjectTypeManager: " + str(self.objTypes))

  def objectTypeNames(self, geom_type):
    if geom_type in self.objTypes:
      return self.objTypes[geom_type].keys()
    return []

  def setupForm(self, dialog, mapTo3d, layer, geom_type, obj_name):
    if geom_type in self.objTypes:
      return self.objTypes[geom_type][obj_name].setupForm(dialog, mapTo3d, layer, obj_name)
    return False

  def module(self, geom_type, obj_name):
    if geom_type in self.objTypes and obj_name in self.objTypes[geom_type]:
      return self.objTypes[geom_type][obj_name]
    return None

class VectorObjectProperties:

  def __init__(self, prop_dict=None):
    if prop_dict is None:
      self.prop_dict = []
      self.visible = False
    else:
      self.prop_dict = prop_dict
      self.obj_typename = prop_dict["typename"]
      self.visible = prop_dict["visible"]
    self.layer = None

  def color(self, layer=None, f=None):
    global colorNames
    vals = self.prop_dict["color"]
    if vals[0] == ColorWidget.RGB:
      return vals[2]
    elif vals[0] == ColorWidget.RANDOM or layer is None or f is None:
      if len(colorNames) == 0:
        colorNames = QColor.colorNames()
      colorName = random.choice(colorNames)
      colorNames.remove(colorName)
      return QColor(colorName).name().replace("#", "0x")
    return layer.rendererV2().symbolForFeature(f).color().name().replace("#", "0x")

  def isHeightRelativeToSurface(self):
    return self.prop_dict["height"][0] == HeightWidget.RELATIVE

  def relativeHeight(self, f=None):
    lst = self.prop_dict["height"]
    if lst[0] in [HeightWidget.RELATIVE, HeightWidget.ABSOLUTE] or f is None:
      return float(lst[2])
    # use attribute value
    return float(f.attribute(lst[1])) * float(lst[2])

  def values(self, f=None):
    vals = []
    for i in range(32):   # big number for style count
      if i in self.prop_dict:
        lst = self.prop_dict[i]
        if lst[0] == FieldValueWidget.ABSOLUTE or f is None:
          vals.append(lst[2])
        else:
          # use attribute value
          vals.append(str(float(f.attribute(lst[1])) * float(lst[2])))
      else:
        break
    return vals

class Point:
  def __init__(self, x, y, z=0):
    self.x = x
    self.y = y
    self.z = z

class MapTo3D:
  def __init__(self, mapCanvas, planeWidth=100, verticalExaggeration=1):
    # map canvas
    #self.canvasWidth, self.canvasHeight
    self.mapExtent = mapCanvas.extent()

    # 3d
    self.planeWidth = planeWidth
    self.planeHeight = planeWidth * mapCanvas.extent().height() / mapCanvas.extent().width()

    self.verticalExaggeration = verticalExaggeration
    self.multiplier = planeWidth / mapCanvas.extent().width()
    self.multiplierZ = self.multiplier * verticalExaggeration

  def transform(self, x, y, z=0):
    extent = self.mapExtent
    return Point((x - extent.xMinimum()) * self.multiplier - self.planeWidth / 2,
                 (y - extent.yMinimum()) * self.multiplier - self.planeHeight / 2,
                 z * self.multiplierZ)

  def transformPoint(self, pt):
    return self.transform(pt.x, pt.y, pt.z)
