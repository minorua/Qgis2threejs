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
import os
#from PyQt4.QtCore import qDebug
from PyQt4.QtGui import QColor
from qgis.core import QGis, QgsMessageLog, NULL
import random
from stylewidget import StyleWidget, HeightWidgetFunc, ColorWidgetFunc, FieldValueWidgetFunc, FilePathWidgetFunc, TransparencyWidgetFunc, LabelHeightWidgetFunc, OptionalColorWidgetFunc, ColorTextureWidgetFunc
from settings import debug_mode

colorNames = []

class DEMPropertyReader:

  def __init__(self, properties=None):
    self.properties = properties or {}
    self.layerId = properties["comboBox_DEMLayer"]
    self._width = properties["dem_Width"] if self.layerId else 2
    self._height = properties["dem_Height"] if self.layerId else 2

  def width(self):
    return self._width

  def height(self):
    return self._height


class VectorPropertyReader:

  def __init__(self, objectTypeManager, layer, properties=None):
    self.layer = layer
    self.properties = properties or {}

    if properties:
      self.item_index = properties["comboBox_ObjectType"]
      typeitem = objectTypeManager.objectTypeItem(layer.geometryType(), self.item_index)  #
      self.type_name = typeitem.name
      self.mod_index = typeitem.mod_index
      self.type_index = typeitem.type_index #
      self.visible = properties["visible"]
    else:
      self.visible = False

  # read color from COLOR or OPTIONAL_COLOR widget
  def _readColor(self, widgetValues, f=None, isBorder=False):
    global colorNames

    mode = widgetValues["comboData"]
    if mode == OptionalColorWidgetFunc.NONE:
      return None

    if mode == ColorWidgetFunc.RGB:
      return widgetValues["editText"]

    if mode == ColorWidgetFunc.RANDOM or f is None:
      if len(colorNames) == 0:
        colorNames = QColor.colorNames()
      colorName = random.choice(colorNames)
      colorNames.remove(colorName)
      return QColor(colorName).name().replace("#", "0x")

    # feature color
    symbol = self.layer.rendererV2().symbolForFeature(f)
    if symbol is None:
      QgsMessageLog.logMessage(u'Symbol for feature cannot be found: {0}'.format(self.layer.name()), "Qgis2threejs")
      symbol = self.layer.rendererV2().symbols()[0]
    else:
      sl = symbol.symbolLayer(0)
      if sl and isBorder:
        return sl.outlineColor().name().replace("#", "0x")

      if sl:    # and sl.hasDataDefinedProperties():  # needs >= 2.2
        expr = sl.dataDefinedProperty("color")
        if expr:
          # data defined color
          cs_rgb = expr.evaluate(f, f.fields())

          # "rrr,ggg,bbb" (dec) to "0xRRGGBB" (hex)
          rgb = map(int, cs_rgb.split(",")[0:3])
          return "0x" + "".join(map(chr, rgb)).encode("hex")

    return symbol.color().name().replace("#", "0x")

  def _readTransparency(self, widgetValues, f=None):
    vals = widgetValues

    if vals["comboData"] == TransparencyWidgetFunc.VALUE:
      try:
        return int(vals["editText"])
      except ValueError:
        return 0

    alpha = None
    symbol = self.layer.rendererV2().symbolForFeature(f)
    if symbol is None:
      QgsMessageLog.logMessage(u'Symbol for feature cannot be found: {0}'.format(self.layer.name()), "Qgis2threejs")
      symbol = self.layer.rendererV2().symbols()[0]
    else:
      sl = symbol.symbolLayer(0)
      if sl:    # and sl.hasDataDefinedProperties():
        expr = sl.dataDefinedProperty("color")
        if expr:
          # data defined transparency
          cs_rgba = expr.evaluate(f, f.fields())
          rgba = cs_rgba.split(",")
          if len(rgba) == 4:
            alpha = float(rgba[3]) / 255

    if alpha is None:
      alpha = symbol.alpha()

    opacity = float(100 - self.layer.layerTransparency()) / 100
    opacity *= alpha      # opacity = layer_opacity * feature_opacity
    return int((1.0 - opacity) * 100)

  @classmethod
  def toFloat(cls, val):
    try:
      return float(val)
    except Exception as e:
      QgsMessageLog.logMessage(u'{0} (value: {1})'.format(e.message, unicode(val)), "Qgis2threejs")
      return 0

  # functions to read values from height widget (z coordinate)
  def useZ(self):
    return self.properties["heightWidget"]["comboData"] == HeightWidgetFunc.Z_VALUE

  def isHeightRelativeToDEM(self):
    v0 = self.properties["heightWidget"]["comboData"]
    return  v0 == HeightWidgetFunc.RELATIVE or v0 >= HeightWidgetFunc.FIRST_ATTR_REL

  def relativeHeight(self, f=None):
    vals = self.properties["heightWidget"]
    if vals["comboData"] in [HeightWidgetFunc.RELATIVE, HeightWidgetFunc.ABSOLUTE, HeightWidgetFunc.Z_VALUE] or f is None:
      return self.toFloat(vals["editText"])

    # attribute value + addend
    fieldName = vals["comboText"].lstrip("+").strip(' "')
    return self.toFloat(f.attribute(fieldName)) + self.toFloat(vals["editText"])

    #if lst[0] >= HeightWidgetFunc.FIRST_ATTR_REL:
    #  return float(f.attributes()[lst[0] - HeightWidgetFunc.FIRST_ATTR_REL]) + float(lst[2])
    #return float(f.attributes()[lst[0] - HeightWidgetFunc.FIRST_ATTR_ABS]) + float(lst[2])

  # read values from style widgets
  #TODO: rename this to styles
  def values(self, f=None):
    vals = []
    for i in range(32):   # big number for style count
      p = "styleWidget" + str(i)
      if p not in self.properties:
        break

      widgetValues = self.properties[p]
      if len(widgetValues) == 0:
        break

      widgetType = widgetValues["type"]
      comboData = widgetValues["comboData"]
      if widgetType in [StyleWidget.COLOR, StyleWidget.OPTIONAL_COLOR]:
        vals.append(self._readColor(widgetValues, f, widgetType == StyleWidget.OPTIONAL_COLOR))

      elif widgetType == StyleWidget.COLOR_TEXTURE:
        if comboData == ColorTextureWidgetFunc.MAP_CANVAS:
          vals.append(comboData)
        elif comboData == ColorTextureWidgetFunc.LAYER:
          vals.append(widgetValues.get("layerIds", []))
        else:
          vals.append(self._readColor(widgetValues, f))

      elif widgetType == StyleWidget.TRANSPARENCY:
        vals.append(self._readTransparency(widgetValues, f))

      elif widgetType == StyleWidget.FILEPATH:
        if comboData == FilePathWidgetFunc.FILEPATH or f is None:
          vals.append(widgetValues["editText"])
        else:
          # prefix + attribute
          fieldName = widgetValues["comboText"].strip('"')
          value = f.attribute(fieldName)
          if value == NULL:
            value = ""
            QgsMessageLog.logMessage(u"Empty attribute value in the field '{0}'".format(fieldName), "Qgis2threejs")
          vals.append(os.path.join(widgetValues["editText"], value.strip('"')))

      elif widgetType == StyleWidget.HEIGHT:
        if widgetValues["comboData"] in [HeightWidgetFunc.RELATIVE, HeightWidgetFunc.ABSOLUTE, HeightWidgetFunc.Z_VALUE] or f is None:
          vals.append(self.toFloat(widgetValues["editText"]))
        else:
          # attribute value + addend
          fieldName = widgetValues["comboText"].lstrip("+").strip(' "')
          vals.append(self.toFloat(f.attribute(fieldName)) + self.toFloat(widgetValues["editText"]))

      else:
        if comboData == FieldValueWidgetFunc.ABSOLUTE or f is None:
          vals.append(widgetValues["editText"])
        else:
          # attribute value * multiplier
          fieldName = widgetValues["comboText"].strip('"')
          val = self.toFloat(f.attribute(fieldName)) * self.toFloat(widgetValues["editText"])
          vals.append(str(val))
    return vals
