# -*- coding: utf-8 -*-
# (C) 2014 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later
# begin: 2014-01-06

import os

from qgis.PyQt.QtCore import Qt, QDir, QEvent, QObject, QVariant
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QComboBox, QFileDialog, QWidget
from qgis.core import QgsApplication, QgsFieldProxyModel, QgsProject

from .ui.widgetComboEdit import Ui_ComboEditWidget
from ..utils import selectColor, getDEMLayersInProject, shortTextFromSelectedLayerIds


class WVT:
    # widget value type
    SIZE = 1
    ANGLE = 2
    OTHERS = 3


class WidgetFuncBase:

    def __init__(self, widget, mapLayer):
        self.widget = widget
        self.mapLayer = mapLayer

    def setup(self, name=None, editLabel="", lineEdit="", placeholderText="", toolButton=False, checkBox=False):
        # setup widgets
        b = bool(name is not None)
        self.widget.label_1.setVisible(b)
        self.widget.comboBox.setVisible(b)
        self.widget.checkBox.setVisible(b and checkBox)

        if name:
            self.widget.label_1.setText(name)

        if editLabel:
            self.widget.label_2.setText(editLabel)

        self.widget.label_2.setVisible(bool(editLabel))

        self.widget.expression.setExpression(lineEdit or "")
        self.widget.expression.setLayer(None)

        b = bool(lineEdit is not None)
        self.widget.expression.setVisible(b)

        if b:
            self.setPlaceholderText(placeholderText)

        self.widget.toolButton.setVisible(toolButton)
        if toolButton and self.widget.toolButton.icon():
            self.widget.toolButton.setIcon(QIcon())

    def dispose(self):
        pass

    def comboBoxSelectionChanged(self, index):
        pass

    def toolButtonClicked(self):
        pass

    def setPlaceholderText(self, text):
        try:
            lineEdit = self.widget.expressionComboBox().lineEdit()
            lineEdit.setPlaceholderText(text)
            lineEdit.setToolTip(text)
        except:
            pass

    def values(self):
        return {"type": self.widget.funcType,
                "comboData": self.widget.comboBox.itemData(self.widget.comboBox.currentIndex()),
                "comboText": self.widget.comboBox.currentText(),
                "editText": self.widget.expression.expression()}

    def setValues(self, vals):
        index = self.widget.comboBox.findData(vals["comboData"])
        if index != -1:
            self.widget.comboBox.setCurrentIndex(index)
        self.widget.expression.setExpression(vals["editText"])

    @classmethod
    def numericalFields(cls, layer):
        numeric_fields = []
        for i, field in enumerate(layer.fields()):
            if field.type() in [QVariant.Double, QVariant.Int, QVariant.LongLong, QVariant.UInt, QVariant.ULongLong]:
                numeric_fields.append([i, field.name()])
        return numeric_fields


class ExpressionWidgetFunc(WidgetFuncBase):

    def __init__(self, widget, mapLayer):
        WidgetFuncBase.__init__(self, widget, mapLayer)
        self.valType = None

    def setup(self, options=None):
        """ options: name, valType, label, defaultValue """
        options = options or {}
        valType = options.get("valType", WVT.SIZE)

        if valType == self.valType:
            val = self.widget.expression.expression()
        else:
            val = str(options.get("defVal", 0))
            self.valType = valType

        WidgetFuncBase.setup(self, editLabel=options.get("name", ""), lineEdit=val)

        self.widget.comboBox.clear()
        self.widget.comboBox.addItem("Expression")

        self.widget.expression.setFilters(QgsFieldProxyModel.Numeric)
        self.widget.expression.setLayer(self.mapLayer)


class ColorWidgetFunc(WidgetFuncBase):

    FEATURE = 1
    RANDOM = 2
    EXPRESSION = 3

    def setup(self, options=None):
        """ options: defaultValue """
        WidgetFuncBase.setup(self, "Color", lineEdit=None)
        options = options or {}

        self.widget.comboBox.clear()
        self.widget.comboBox.addItem("Feature style", ColorWidgetFunc.FEATURE)
        self.widget.comboBox.addItem("Random", ColorWidgetFunc.RANDOM)
        self.widget.comboBox.addItem("Expression", ColorWidgetFunc.EXPRESSION)

        self.widget.expression.setExpression(str(options.get("defVal", "")))
        self.widget.expression.setFilters(QgsFieldProxyModel.String)
        self.setPlaceholderText("e.g. color_rgb(255, 127, 0), '#FF7F00'")

        self.widget.expression.setFilters(QgsFieldProxyModel.String | QgsFieldProxyModel.Int | QgsFieldProxyModel.LongLong)
        self.widget.expression.setLayer(self.mapLayer)

        self.widget.toolButton.setIcon(QgsApplication.getThemeIcon("mIconColorSwatches.svg"))

    def comboBoxSelectionChanged(self, index):
        itemData = self.widget.comboBox.itemData(index)
        isRGB = itemData == ColorWidgetFunc.EXPRESSION
        self.widget.label_2.setVisible(isRGB)
        self.widget.expression.setVisible(isRGB)
        self.widget.toolButton.setVisible(isRGB)

    def toolButtonClicked(self):
        color = selectColor()
        if color:
            self.widget.expression.setExpression("'" + color.name().replace("#", "0x") + "'")

    def setValues(self, vals):
        index = self.widget.comboBox.findData(vals["comboData"])
        if index != -1:
            self.widget.comboBox.setCurrentIndex(index)
            self.widget.comboBoxSelectionChanged(index)  # make sure to update visibility
        self.widget.expression.setExpression(vals["editText"])


class OptionalColorWidgetFunc(ColorWidgetFunc):

    def setup(self, options=None):
        """ options: name, itemText, defaultValue """
        options = options or {}
        ColorWidgetFunc.setup(self, options)
        self.widget.label_1.setText(options.get("name", "Color"))

        itemText = options.get("itemText", {})
        if itemText.get(None, "") is not None:
            self.widget.comboBox.insertItem(0, "None", None)

        for id, text in itemText.items():
            index = self.widget.comboBox.findData(id)
            if index != -1:
                self.widget.comboBox.setItemText(index, text)

        index = self.widget.comboBox.findData(options.get("defVal"))
        if index != -1:
            self.widget.comboBox.setCurrentIndex(index)


class FilePathWidgetFunc(WidgetFuncBase):

    FILEPATH = 1

    def setup(self, options=None):
        """ options: name, label, defaultValue, filterString, allowURL """
        options = options or {}
        self.lineEditLabel = options.get("label", "")
        WidgetFuncBase.setup(self, options.get("name", ""), editLabel=self.lineEditLabel, toolButton=True)
        self.widget.expression.setExpression(str(options.get("defVal", "")))

        self.widget.comboBox.clear()
        if options.get("allowURL"):
            self.widget.comboBox.addItem("File path or URL", FilePathWidgetFunc.FILEPATH)
        else:
            self.widget.comboBox.addItem("File path", FilePathWidgetFunc.FILEPATH)

        self.widget.expression.setFilters(QgsFieldProxyModel.String)
        self.widget.expression.setLayer(self.mapLayer)

        self.filterString = options.get("filterString", "")

    def toolButtonClicked(self):
        workdir = os.path.split(self.widget.expression.expression())[0]
        if not workdir:
            workdir = QgsProject.instance().homePath()
        if not workdir:
            workdir = QDir.homePath()

        filepath, _ = QFileDialog.getOpenFileName(None, "Select a file", workdir, self.filterString)
        if filepath:
            self.widget.expression.setExpression("'" + filepath + "'")


class HeightWidgetFunc(WidgetFuncBase):

    def setup(self, options=None):
        """ options: name, defaultValue, defaultValue """
        options = options or {}
        WidgetFuncBase.setup(self, options.get("name", "Mode"))
        self.defaultValue = options.get("defVal", 0)

        # set up combo box
        comboBox = self.widget.comboBox
        comboBox.clear()
        comboBox.addItem("Absolute")
        for lyr in getDEMLayersInProject():
            comboBox.addItem('Relative to "{0}" layer'.format(lyr.name()), lyr.id())

        # z value if layer has
        # if layer and layer.wkbType() in [QgsWkbTypes.Point25D, QgsWkbTypes.LineString25D, QgsWkbTypes.MultiPoint25D, QgsWkbTypes.MultiLineString25D]:
        #  comboBox.addItem("Z value", HeightWidgetFunc.Z_VALUE)
        #  comboBox.insertSeparator(1)

        defaultValue = options.get("defVal")
        if defaultValue:
            index = comboBox.findData(defaultValue)
            if index != -1:
                comboBox.setCurrentIndex(index)

    def comboBoxSelectionChanged(self, index):
        if self.widget.comboBox.itemData(index):
            label = "Addend"
            defaultValue = 0
        else:
            label = "Altitude"
            defaultValue = self.defaultValue
        self.widget.label_2.setText(label)
        self.widget.expression.setExpression(str(defaultValue))

    def isCurrentItemRelativeHeight(self):
        return self.widget.comboBox.itemData(self.widget.comboBox.currentIndex()) is None


class LabelHeightWidgetFunc(WidgetFuncBase):

    ABSOLUTE = 0
    RELATIVE = 1

    def setup(self, options=None):
        """ options: defaultValue """
        WidgetFuncBase.setup(self, "Label height")
        options = options or {}

        self.widget.comboBox.clear()
        self.widget.comboBox.addItem("Relative", self.RELATIVE)
        self.widget.comboBox.addItem("Absolute", self.ABSOLUTE)

        self.widget.expression.setFilters(QgsFieldProxyModel.Numeric)
        self.widget.expression.setLayer(self.mapLayer)

        self.defaultValue = options.get("defVal")
        if self.defaultValue is not None:
            self.widget.expression.setExpression(str(self.defaultValue))


class OpacityWidgetFunc(WidgetFuncBase):

    FEATURE = 1
    EXPRESSION = 2

    def setup(self, options=None):
        WidgetFuncBase.setup(self, "Opacity", lineEdit=None)
        options = options or {}

        self.widget.comboBox.clear()
        self.widget.comboBox.addItem("Feature style", OpacityWidgetFunc.FEATURE)
        self.widget.comboBox.addItem("Expression", OpacityWidgetFunc.EXPRESSION)

        self.widget.expression.setFilters(QgsFieldProxyModel.Numeric)
        self.widget.expression.setLayer(self.mapLayer)
        self.setPlaceholderText("numeric (percentage. 0 - 100)")

    def comboBoxSelectionChanged(self, index):
        itemData = self.widget.comboBox.itemData(index)
        isValue = itemData == OpacityWidgetFunc.EXPRESSION
        self.widget.label_2.setVisible(isValue)
        self.widget.expression.setVisible(isValue)

    def setValues(self, vals):
        index = self.widget.comboBox.findData(vals["comboData"])
        if index != -1:
            self.widget.comboBox.setCurrentIndex(index)
            self.widget.comboBoxSelectionChanged(index)  # make sure to update visibility
        self.widget.expression.setExpression(vals["editText"])


class ColorTextureWidgetFunc(ColorWidgetFunc):

    MAP_CANVAS = 10
    LAYER = 11

    def __init__(self, widget):
        ColorWidgetFunc.__init__(self, widget)
        self.layerIds = []
        self.mapSettings = None

    def setup(self, options=None):
        """ options: mapSettings """
        options = options or {}
        self.mapSettings = options.get("mapSettings")
        ColorWidgetFunc.setup(self, options)
        self.widget.label_1.setText("Color/Texture")
        comboBox = self.widget.comboBox
        comboBox.insertSeparator(comboBox.count())
        comboBox.addItem("Map canvas image", ColorTextureWidgetFunc.MAP_CANVAS)
        comboBox.addItem("Layer image", ColorTextureWidgetFunc.LAYER)

        self.updateLineEdit()

    def comboBoxSelectionChanged(self, index):
        itemData = self.widget.comboBox.itemData(index)
        isRGB = bool(itemData == ColorWidgetFunc.EXPRESSION)
        isLayer = bool(itemData == ColorTextureWidgetFunc.LAYER)

        self.widget.label_2.setText("Layers" if isLayer else "Value")
        self.widget.label_2.setVisible(isRGB or isLayer)

        # self.widget.expression.setPlaceholderText("0xrrggbb" if isRGB else "")
        # self.widget.expression.setReadOnly(isLayer)
        self.widget.expression.setVisible(isRGB or isLayer)

        if isRGB:
            self.widget.expression.setExpression("")
        elif isLayer:
            self.updateLineEdit()

        self.widget.toolButton.setVisible(isRGB or isLayer)

    def toolButtonClicked(self):
        itemData = self.widget.comboBox.itemData(self.widget.comboBox.currentIndex())
        if itemData == ColorWidgetFunc.EXPRESSION:
            ColorWidgetFunc.toolButtonClicked(self)
            return

        # ColorTextureWidgetFunc.LAYER
        from .layerselectdialog import LayerSelectDialog
        dialog = LayerSelectDialog(self.widget)
        dialog.initTree(self.layerIds)
        dialog.setMapSettings(self.mapSettings)
        if dialog.exec():
            self.layerIds = dialog.visibleLayerIds()
            self.updateLineEdit()

    def updateLineEdit(self):
        self.widget.expression.setExpression(shortTextFromSelectedLayerIds(self.layerIds))

    def values(self):
        v = ColorWidgetFunc.values(self)
        if self.layerIds:
            v["layerIds"] = self.layerIds
        return v

    def setValues(self, vals):
        self.layerIds = vals.get("layerIds", [])
        ColorWidgetFunc.setValues(self, vals)


class CheckBoxWidgetFunc(WidgetFuncBase):

    def setup(self, options=None):
        """ options: name, defaultValue, connectTo """
        options = options or {}
        WidgetFuncBase.setup(self, options.get("name", ""), checkBox=True)
        self.setLayoutVisible(False)
        checked = options.get("defVal", False)

        # connect with widgets
        self.connectedWidgets = []
        for w in options.get("connectTo", []):
            w.setEnabled(checked)
            self.widget.checkBox.toggled.connect(w.setEnabled)
            self.connectedWidgets.append(w)

    def dispose(self):
        self.setLayoutVisible(True)
        for w in self.connectedWidgets:
            self.widget.checkBox.toggled.disconnect(w.setEnabled)
            w.setEnabled(True)

    def values(self):
        return {"type": self.widget.funcType,
                "checkBox": self.widget.checkBox.isChecked()}

    def setValues(self, vals):
        checked = vals.get("checkBox", False)
        self.widget.checkBox.setChecked(checked)
        for w in self.connectedWidgets:
            w.setEnabled(checked)

    def setLayoutVisible(self, visible):
        self.widget.label_2.setVisible(visible)
        self.widget.comboBox.setVisible(visible)
        self.widget.expression.setVisible(visible)
        self.widget.toolButton.setVisible(visible)


class ComboBoxWidgetFunc(WidgetFuncBase):

    def setup(self, options=None):
        """ options: name, items, defaultValue"""
        options = options or {}
        WidgetFuncBase.setup(self, options.get("name", ""), lineEdit=None)

        self.widget.comboBox.clear()
        for item in options.get("items", []):
            self.widget.comboBox.addItem(item, item)

        def_val = options.get("defVal")
        if def_val:
            index = self.widget.comboBox.findData(def_val)
            if index != -1:
                self.widget.comboBox.setCurrentIndex(index)

    def values(self):
        return {"type": self.widget.funcType,
                "comboData": self.widget.comboBox.itemData(self.widget.comboBox.currentIndex())}

    def setValues(self, vals):
        index = self.widget.comboBox.findData(vals["comboData"])
        if index != -1:
            self.widget.comboBox.setCurrentIndex(index)


class PropertyWidget(QWidget, Ui_ComboEditWidget):
    # function types
    EXPRESSION = 1
    COLOR = 2
    FILEPATH = 3
    HEIGHT = 4      # OBSOLETE
    OPACITY = 5
    LABEL_HEIGHT = 6
    OPTIONAL_COLOR = 7
    COLOR_TEXTURE = 8   # OBSOLETE
    CHECKBOX = 9
    COMBOBOX = 10

    type2funcClass = {EXPRESSION: ExpressionWidgetFunc,
                      COLOR: ColorWidgetFunc,
                      FILEPATH: FilePathWidgetFunc,
                      HEIGHT: HeightWidgetFunc,         # OBSOLETE
                      LABEL_HEIGHT: LabelHeightWidgetFunc,
                      OPACITY: OpacityWidgetFunc,
                      OPTIONAL_COLOR: OptionalColorWidgetFunc,
                      COLOR_TEXTURE: ColorTextureWidgetFunc,     # OBSOLETE
                      CHECKBOX: CheckBoxWidgetFunc,
                      COMBOBOX: ComboBoxWidgetFunc}

    FIELDTYPE_ALL = 0
    FIELDTYPE_NUMBER = 1
    FIELDTYPE_STRING = 2

    def __init__(self, parent=None):
        QWidget.__init__(self, parent)
        self.setupUi(self)
        self.comboBox.currentIndexChanged.connect(self.comboBoxSelectionChanged)
        self.toolButton.clicked.connect(self.toolButtonClicked)
        self.funcType = None
        self.func = None
        self.hasValues = False

        # install event filter
        self.enterKeyFilter = EnterKeyEventFilter(self)
        for w in self.expression.findChildren(QComboBox):
            w.installEventFilter(self.enterKeyFilter)

    def setup(self, funcType, mapLayer=None, options=None):
        if self.func:
            self.func.dispose()

        if self.func is None or self.funcType != funcType:
            self.func = self.type2funcClass[funcType](self, mapLayer)

        self.funcType = funcType
        self.func.setup(options)
        self.setVisible(True)
        self.hasValues = True

    def expressionComboBox(self):
        for w in self.expression.findChildren(QComboBox):
            return w

    def comboBoxSelectionChanged(self, index):
        if self.func and index != -1:
            self.func.comboBoxSelectionChanged(index)

    def toolButtonClicked(self):
        if self.func:
            self.func.toolButtonClicked()

    def hide(self):
        self.hasValues = False
        QWidget.hide(self)

    def values(self):
        if self.func and self.hasValues:
            return self.func.values()
        else:
            return {}

    def setValues(self, vals):
        if self.func:
            self.func.setValues(vals)


class EnterKeyEventFilter(QObject):

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.KeyPress and (event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter):
            event.ignore()
            return True
        return QObject.eventFilter(self, obj, event)
