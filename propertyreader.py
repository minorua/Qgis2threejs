# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Qgis2threejs
                                 A QGIS plugin
 export terrain data, map canvas image and vector data to web browser
                             -------------------
        begin                : 2014-04-03
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
#from PyQt4.QtCore import qDebug
from PyQt4.QtGui import QColor, QMessageBox
from qgis.core import QGis, QgsMessageLog
import random
from stylewidget import HeightWidgetFunc, ColorWidgetFunc, FieldValueWidgetFunc, TransparencyWidgetFunc, LabelHeightWidgetFunc

debug_mode = 1

colorNames = []

class DEMPropertyReader:
  def __init__(self, properties=None):
    self.properties = properties

  def width(self):
    if self.properties["comboBox_DEMLayer"]:
      return self.properties["dem_Width"]
    return 2

  def height(self):
    if self.properties["comboBox_DEMLayer"]:
      return self.properties["dem_Height"]
    return 2

class VectorPropertyReader:
  def __init__(self, objectTypeManager, layer, properties=None):
    self.properties = properties
    if properties is None:
      self.properties = {}
      self.visible = False
    else:
      self.properties = properties
      self.item_index = properties["comboBox_ObjectType"]
      typeitem = objectTypeManager.objectTypeItem(layer.geometryType(), self.item_index)  #
      self.type_name = typeitem.name
      self.mod_index = typeitem.mod_index
      self.type_index = typeitem.type_index #
      self.visible = properties["visible"]

  def color(self, layer=None, f=None):
    global colorNames   #TODO: add function to material manager
    vals = self.properties["colorWidget"]
    if vals[0] == ColorWidgetFunc.RGB:
      return vals[2]
    elif vals[0] == ColorWidgetFunc.RANDOM or layer is None or f is None:
      if len(colorNames) == 0:
        colorNames = QColor.colorNames()
      colorName = random.choice(colorNames)
      colorNames.remove(colorName)
      return QColor(colorName).name().replace("#", "0x")

    symbol = layer.rendererV2().symbolForFeature(f)
    if symbol is None:
      QgsMessageLog.logMessage(u'Symbol for feature is not found. Once try to show layer: {0}'.format(layer.name()), "Qgis2threejs")
      symbol = layer.rendererV2().symbols()[0]
    else:
      sl = symbol.symbolLayer(0)
      if sl:    # and sl.hasDataDefinedProperties():  # needs >= 2.2
        expr = sl.dataDefinedProperty("color")
        if expr:
          # data defined color
          cs_rgb = expr.evaluate(f, f.fields())

          # "rrr,ggg,bbb" (dec) to "0xRRGGBB" (hex)
          rgb = map(int, cs_rgb.split(",")[0:3])
          return "0x" + "".join(map(chr, rgb)).encode("hex")

    return symbol.color().name().replace("#", "0x")

  def transparency(self, layer=None, f=None):
    vals = self.properties["transparencyWidget"]
    if vals[0] == TransparencyWidgetFunc.VALUE:
      try:
        return int(vals[2])
      except:
        return 0

    if vals[0] == TransparencyWidgetFunc.LAYER:
      return layer.layerTransparency()

    symbol = layer.rendererV2().symbolForFeature(f)
    if symbol is None:
      QgsMessageLog.logMessage(u'Symbol for feature is not found. Once try to show layer: {0}'.format(layer.name()), "Qgis2threejs")
      symbol = layer.rendererV2().symbols()[0]
    else:
      sl = symbol.symbolLayer(0)
      if sl:    # and sl.hasDataDefinedProperties():
        expr = sl.dataDefinedProperty("color")
        if expr:
          # data defined color
          cs_rgba = expr.evaluate(f, f.fields())
          rgba = cs_rgba.split(",")
          if len(rgba) == 4:
            return int((1.0 - (float(rgba[3]) / 255)) * 100)

    return int((1.0 - symbol.alpha()) * 100)

  @classmethod
  def toFloat(cls, val):
    try:
      return float(val)
    except Exception as e:
      QgsMessageLog.logMessage(u'{0} {1}'.format(e.message, unicode(val)), "Qgis2threejs")
      return 0

  # functions to read values from height widget (z coordinate)
  def useZ(self):
    return self.properties["heightWidget"][0] == HeightWidgetFunc.Z_VALUE

  def isHeightRelativeToDEM(self):
    v0 = self.properties["heightWidget"][0]
    return  v0 == HeightWidgetFunc.RELATIVE or v0 >= HeightWidgetFunc.FIRST_ATTR_REL

  def relativeHeight(self, f=None):
    lst = self.properties["heightWidget"]
    if lst[0] in [HeightWidgetFunc.RELATIVE, HeightWidgetFunc.ABSOLUTE, HeightWidgetFunc.Z_VALUE] or f is None:
      return self.toFloat(lst[2])

    # attribute value + addend
    fieldName = lst[1].lstrip("+").strip(' "')
    return self.toFloat(f.attribute(fieldName)) + self.toFloat(lst[2])

    #if lst[0] >= HeightWidgetFunc.FIRST_ATTR_REL:
    #  return float(f.attributes()[lst[0] - HeightWidgetFunc.FIRST_ATTR_REL]) + float(lst[2])
    #return float(f.attributes()[lst[0] - HeightWidgetFunc.FIRST_ATTR_ABS]) + float(lst[2])

  # read values from style widgets
  def values(self, f=None):
    vals = []
    for i in range(32):   # big number for style count
      p = "styleWidget" + str(i)
      if p in self.properties:
        lst = self.properties[p]
        if len(lst) == 0:
          break
        if lst[0] == FieldValueWidgetFunc.ABSOLUTE or f is None:
          vals.append(lst[2])
        else:
          # attribute value * multiplier
          fieldName = lst[1].strip('"')
          val = self.toFloat(f.attribute(fieldName)) * self.toFloat(lst[2])
          vals.append(str(val))
      else:
        break
    return vals
