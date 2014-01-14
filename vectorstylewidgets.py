# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Qgis2threejs
                                 A QGIS plugin
 export terrain and map image into web browser
                             -------------------
        begin                : 2013-12-21
        copyright            : (C) 2013 by Minoru Akagi
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
from PyQt4.QtCore import QVariant
from PyQt4.QtGui import QWidget
from ui_widgetComboEdit import Ui_ComboEditWidget

class FieldValueWidget(QWidget, Ui_ComboEditWidget):
  ABSOLUTE = 1
  FIRST_ATTRIBUTE = 100

  def __init__(self, parent=None):
    QWidget.__init__(self, parent)
    self.setupUi(self)
    self.comboBox.currentIndexChanged.connect(self.comboBoxSelectionChanged)
    self.defaultValue = 0

  def comboBoxSelectionChanged(self, i):
    pass

  def values(self):
    return [self.comboBox.itemData(self.comboBox.currentIndex()), self.comboBox.currentText(), self.lineEdit.text()]

  def setValues(self, vals):
    index = self.comboBox.findText(vals[1])
    if index != -1:
      self.comboBox.setCurrentIndex(index)
    self.lineEdit.setText(vals[2])

  def addFieldNameItems(self, layer, fieldNames=None):
    fields = layer.pendingFields()
    if fieldNames is None:
      for i, field in enumerate(fields):
        if field.type() in [QVariant.Double, QVariant.Int, QVariant.LongLong, QVariant.UInt, QVariant.ULongLong]:
          self.comboBox.addItem(field.name(), FieldValueWidget.FIRST_ATTRIBUTE + i)
    else:
      for fieldName in fieldNames:
        self.comboBox.addItem(fieldName, FieldValueWidget.FIRST_ATTRIBUTE + fields.indexFromName(fieldName))

class SizeWidget(FieldValueWidget):
  def __init__(self, parent=None):
    FieldValueWidget.__init__(self, parent)

  def setup(self, name, label, defaultValue, layer=None, fieldNames=None):
    self.label_1.setText(name)
    self.label_2.setText(label)
    self.defaultValue = defaultValue
    self.layer = layer

    self.comboBox.clear()
    self.comboBox.addItem("Fixed value", FieldValueWidget.ABSOLUTE)
    if layer:
      self.addFieldNameItems(layer, fieldNames)
    self.setVisible(True)

  def comboBoxSelectionChanged(self, index):
    itemData = self.comboBox.itemData(index)
    if itemData == FieldValueWidget.ABSOLUTE:
      label = "Value"
      defaultValue = self.defaultValue
    else:
      label = "Multiplier"
      defaultValue = 1
    self.label_2.setText(label)
    self.lineEdit.setText(str(defaultValue))

class ColorWidget(QWidget, Ui_ComboEditWidget):
  CURRENTSTYLE = 1
  RANDOM = 2
  RGB = 3

  def __init__(self, parent=None):
    QWidget.__init__(self, parent)
    self.setupUi(self)
    self.comboBox.currentIndexChanged.connect(self.comboBoxSelectionChanged)
    self.label_1.setText("Color")
    self.label_2.setText("Value")
    self.lineEdit.setVisible(False)
    self.lineEdit.setPlaceholderText("Format: 0xrrggbb")

    self.comboBox.addItem("Current style", ColorWidget.CURRENTSTYLE)
    self.comboBox.addItem("Random", ColorWidget.RANDOM)
    self.comboBox.addItem("RGB value", ColorWidget.RGB)

  def setup(self):
    self.comboBox.setCurrentIndex(0)
    self.setVisible(True)

  def comboBoxSelectionChanged(self, index):
    itemData = self.comboBox.itemData(index)
    isUser = itemData == ColorWidget.RGB
    self.label_2.setVisible(isUser)
    self.lineEdit.setVisible(isUser)

  def values(self):
    return [self.comboBox.itemData(self.comboBox.currentIndex()), self.comboBox.currentText(), self.lineEdit.text()]

  def setValues(self, vals):
    index = self.comboBox.findText(vals[1])
    if index != -1:
      self.comboBox.setCurrentIndex(index)
      self.comboBoxSelectionChanged(index)  # make sure to update visibility
    self.lineEdit.setText(vals[2])

class HeightWidget(FieldValueWidget):
  RELATIVE = 2

  def __init__(self, parent=None):
    FieldValueWidget.__init__(self, parent)

  def setup(self, layer=None, fieldNames=None):
    self.label_1.setText("Height")
    self.layer = layer

    self.comboBox.clear()
    self.comboBox.addItem("Fixed value (Relative)", HeightWidget.RELATIVE)
    self.comboBox.addItem("Fixed value (Absolute)", HeightWidget.ABSOLUTE)
    if layer:
      self.addFieldNameItems(layer, fieldNames)
    self.setVisible(True)

  def comboBoxSelectionChanged(self, index):
    itemData = self.comboBox.itemData(index)
    if itemData == HeightWidget.RELATIVE or itemData == HeightWidget.ABSOLUTE:
      label = "Value"
      defaultValue = self.defaultValue
    else:
      label = "Multiplier"	#TODO: Addend
      defaultValue = 1
    self.label_2.setText(label)
    self.lineEdit.setText(str(defaultValue))
