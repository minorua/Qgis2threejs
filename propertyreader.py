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
import random
from PyQt5.QtCore import QSize
from PyQt5.QtGui import QColor
from qgis.core import NULL, QgsExpression, QgsExpressionContext, QgsExpressionContextUtils

from .qgis2threejscore import calculateDEMSize
from .qgis2threejstools import logMessage
from .stylewidget import StyleWidget, HeightWidgetFunc, ColorWidgetFunc, FieldValueWidgetFunc, FilePathWidgetFunc, OpacityWidgetFunc, OptionalColorWidgetFunc, ColorTextureWidgetFunc

colorNames = []


class DEMPropertyReader:

  def __init__(self, layerId, properties=None):
    properties = properties or {}
    self.layerId = layerId
    self.properties = properties

  def demSize(self, canvasSize):
    if self.layerId == "FLAT":
      return QSize(2, 2)

    sizeLevel = self.properties.get("horizontalSlider_DEMSize", 2)
    roughening = 0
    if self.properties.get("checkBox_Surroundings", False):
      roughening = self.properties.get("spinBox_Roughening", 0)
    return calculateDEMSize(canvasSize, sizeLevel, roughening)


class VectorPropertyReader:

  def __init__(self, objectTypeManager, renderContext, layer, properties):
    assert(properties is not None)
    self.renderContext = renderContext
    self.expressionContext = QgsExpressionContext()
    self.expressionContext.appendScope(QgsExpressionContextUtils.layerScope(layer))
    self.layer = layer
    properties = properties or {}
    self.properties = properties

    if properties:
      self.objType = objectTypeManager.objectType(layer.geometryType(), properties["comboBox_ObjectType"])
      self.visible = properties.get("visible", True)
    else:
      self.visible = False

    self._exprs = {}
    self.exprAlt = QgsExpression(properties.get("fieldExpressionWidget_altitude") or "0")

  def evaluateExpression(self, expr_str, f):
    if expr_str not in self._exprs:
      self._exprs[expr_str] = QgsExpression(expr_str)

    self.expressionContext.setFeature(f)
    return self._exprs[expr_str].evaluate(self.expressionContext)

  def readFillColor(self, vals, f):
    return self._readColor(vals, f)

  def readBorderColor(self, vals, f):
    return self._readColor(vals, f, isBorder=True)

  # read color from COLOR or OPTIONAL_COLOR widget
  def _readColor(self, widgetValues, f, isBorder=False):
    global colorNames

    mode = widgetValues["comboData"]
    if mode == OptionalColorWidgetFunc.NONE:
      return None

    if mode == ColorWidgetFunc.EXPRESSION:
      return self.evaluateExpression(widgetValues["editText"], f)

    if mode == ColorWidgetFunc.RANDOM or f is None:
      if len(colorNames) == 0:
        colorNames = QColor.colorNames()
      colorName = random.choice(colorNames)
      colorNames.remove(colorName)
      return QColor(colorName).name().replace("#", "0x")

    # feature color
    symbol = self.layer.renderer().symbolForFeature(f, self.renderContext)
    if symbol is None:
      logMessage('Symbol for feature cannot be found: {0}'.format(self.layer.name()))
      symbol = self.layer.renderer().symbols()[0]
    else:
      sl = symbol.symbolLayer(0)
      if sl and isBorder:
        return sl.strokeColor().name().replace("#", "0x")

      if sl and symbol.hasDataDefinedProperties():
        expr = sl.dataDefinedProperty("color")    #TODO: QGIS 3
        if expr:
          # data defined color
          rgb = expr.evaluate(f, f.fields())

          # "rrr,ggg,bbb" (dec) to "0xRRGGBB" (hex)
          r, g, b = [max(0, min(int(c), 255)) for c in rgb.split(",")[:3]]
          return "0x{0:02x}{1:02x}{2:02x}".format(r, g, b)

    return symbol.color().name().replace("#", "0x")

  def readOpacity(self, widgetValues, f):
    vals = widgetValues

    if vals["comboData"] == OpacityWidgetFunc.VALUE:
      try:
        val = self.evaluateExpression(widgetValues["editText"], f)
        return min(max(0, val), 100) / 100
      except ValueError:
        return 1

    alpha = None
    symbol = self.layer.renderer().symbolForFeature(f, self.renderContext)
    if symbol is None:
      logMessage('Symbol for feature cannot be found: {0}'.format(self.layer.name()))
      symbol = self.layer.renderer().symbols()[0]
    else:
      sl = symbol.symbolLayer(0)
      if sl and symbol.hasDataDefinedProperties():
        expr = sl.dataDefinedProperty("color")    #TODO: QGIS 3
        if expr:
          # data defined opacity
          cs_rgba = expr.evaluate(f, f.fields())
          rgba = cs_rgba.split(",")
          if len(rgba) == 4:
            alpha = rgba[3] / 255

    if alpha is None:
      alpha = 1         #TODO: QGIS 3 symbol.alpha()
                        # 'QgsMarkerSymbol' object has no attribute 'alpha'

    return self.layer.opacity() * alpha    # opacity = layer_opacity * feature_opacity

  @classmethod
  def toFloat(cls, val):
    try:
      return float(val)
    except Exception as e:
      logMessage('{0} (value: {1})'.format(e.message, str(val)))
      return 0

  # functions to read values from height widget (z coordinate)
  def useZ(self):
    return self.properties.get("radioButton_zValue", False)

  def useM(self):
    return self.properties.get("radioButton_mValue", False)

  def isHeightRelativeToDEM(self):
    return self.properties.get("comboBox_altitudeMode") is not None

  def altitude(self):
    return self.exprAlt.evaluate(self.expressionContext)

  def setContextFeature(self, f):
    self.expressionContext.setFeature(f)

  # read values from style widgets
  #TODO: rename this to styleValues
  def values(self, f):
    assert(f is not None)
    vals = []
    for i in range(32):   # big number for style count
      p = "styleWidget" + str(i)
      if p not in self.properties:
        break

      widgetValues = self.properties[p]
      if len(widgetValues) == 0:
        break

      widgetType = widgetValues["type"]
      comboData = widgetValues.get("comboData")
      if widgetType == StyleWidget.COLOR:
        vals.append(self.readFillColor(widgetValues, f))

      elif widgetType == StyleWidget.OPTIONAL_COLOR:
        vals.append(self.readBorderColor(widgetValues, f))

      elif widgetType == StyleWidget.COLOR_TEXTURE:
        if comboData == ColorTextureWidgetFunc.MAP_CANVAS:
          vals.append(comboData)
        elif comboData == ColorTextureWidgetFunc.LAYER:
          vals.append(widgetValues.get("layerIds", []))
        else:
          vals.append(self.readFillColor(widgetValues, f))

      elif widgetType == StyleWidget.OPACITY:
        vals.append(self.readOpacity(widgetValues, f))

      elif widgetType == StyleWidget.CHECKBOX:
        vals.append(widgetValues["checkBox"])

      elif widgetType == StyleWidget.HEIGHT:
        #TODO
        if widgetValues["comboData"] in [HeightWidgetFunc.RELATIVE, HeightWidgetFunc.ABSOLUTE, HeightWidgetFunc.Z_VALUE] or f is None:
          vals.append(self.toFloat(widgetValues["editText"]))
        else:
          # attribute value + addend
          fieldName = widgetValues["comboText"].lstrip("+").strip(' "')
          vals.append(self.toFloat(f.attribute(fieldName)) + self.toFloat(widgetValues["editText"]))

      else:
        expr = widgetValues["editText"]
        val = self.evaluateExpression(expr, f)
        if val is None:
          logMessage("Failed to evaluate expression: " + expr)
          if widgetType == StyleWidget.FILEPATH:
            val = ""
          else:
            val = 0
        vals.append(val)
    return vals
