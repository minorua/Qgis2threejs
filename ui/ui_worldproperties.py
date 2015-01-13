# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'D:\Users\minorua\.qgis2\python\developing_plugins\Qgis2threejs\ui\worldproperties.ui'
#
# Created: Tue Jan 13 14:11:54 2015
#      by: PyQt4 UI code generator 4.10.2
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    def _fromUtf8(s):
        return s

try:
    _encoding = QtGui.QApplication.UnicodeUTF8
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig, _encoding)
except AttributeError:
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig)

class Ui_WorldPropertiesWidget(object):
    def setupUi(self, WorldPropertiesWidget):
        WorldPropertiesWidget.setObjectName(_fromUtf8("WorldPropertiesWidget"))
        WorldPropertiesWidget.resize(286, 366)
        self.gridLayout = QtGui.QGridLayout(WorldPropertiesWidget)
        self.gridLayout.setObjectName(_fromUtf8("gridLayout"))
        spacerItem = QtGui.QSpacerItem(20, 40, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding)
        self.gridLayout.addItem(spacerItem, 5, 0, 1, 1)
        self.groupBox_3 = QtGui.QGroupBox(WorldPropertiesWidget)
        self.groupBox_3.setObjectName(_fromUtf8("groupBox_3"))
        self.verticalLayout_2 = QtGui.QVBoxLayout(self.groupBox_3)
        self.verticalLayout_2.setObjectName(_fromUtf8("verticalLayout_2"))
        self.radioButton_Sky = QtGui.QRadioButton(self.groupBox_3)
        self.radioButton_Sky.setChecked(True)
        self.radioButton_Sky.setObjectName(_fromUtf8("radioButton_Sky"))
        self.verticalLayout_2.addWidget(self.radioButton_Sky)
        self.horizontalLayout_2 = QtGui.QHBoxLayout()
        self.horizontalLayout_2.setObjectName(_fromUtf8("horizontalLayout_2"))
        self.radioButton_Color = QtGui.QRadioButton(self.groupBox_3)
        self.radioButton_Color.setObjectName(_fromUtf8("radioButton_Color"))
        self.horizontalLayout_2.addWidget(self.radioButton_Color)
        self.lineEdit_Color = QtGui.QLineEdit(self.groupBox_3)
        self.lineEdit_Color.setEnabled(False)
        self.lineEdit_Color.setObjectName(_fromUtf8("lineEdit_Color"))
        self.horizontalLayout_2.addWidget(self.lineEdit_Color)
        self.toolButton_Color = QtGui.QToolButton(self.groupBox_3)
        self.toolButton_Color.setEnabled(False)
        self.toolButton_Color.setObjectName(_fromUtf8("toolButton_Color"))
        self.horizontalLayout_2.addWidget(self.toolButton_Color)
        spacerItem1 = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.horizontalLayout_2.addItem(spacerItem1)
        self.verticalLayout_2.addLayout(self.horizontalLayout_2)
        self.gridLayout.addWidget(self.groupBox_3, 3, 0, 1, 1)
        self.groupBox_4 = QtGui.QGroupBox(WorldPropertiesWidget)
        self.groupBox_4.setObjectName(_fromUtf8("groupBox_4"))
        self.verticalLayout = QtGui.QVBoxLayout(self.groupBox_4)
        self.verticalLayout.setObjectName(_fromUtf8("verticalLayout"))
        self.radioButton_ProjectCRS = QtGui.QRadioButton(self.groupBox_4)
        self.radioButton_ProjectCRS.setChecked(True)
        self.radioButton_ProjectCRS.setObjectName(_fromUtf8("radioButton_ProjectCRS"))
        self.verticalLayout.addWidget(self.radioButton_ProjectCRS)
        self.radioButton_WGS84 = QtGui.QRadioButton(self.groupBox_4)
        self.radioButton_WGS84.setObjectName(_fromUtf8("radioButton_WGS84"))
        self.verticalLayout.addWidget(self.radioButton_WGS84)
        self.gridLayout.addWidget(self.groupBox_4, 4, 0, 1, 1)
        self.groupBox_2 = QtGui.QGroupBox(WorldPropertiesWidget)
        self.groupBox_2.setObjectName(_fromUtf8("groupBox_2"))
        self.formLayout_3 = QtGui.QFormLayout(self.groupBox_2)
        self.formLayout_3.setFieldGrowthPolicy(QtGui.QFormLayout.AllNonFixedFieldsGrow)
        self.formLayout_3.setObjectName(_fromUtf8("formLayout_3"))
        self.label = QtGui.QLabel(self.groupBox_2)
        self.label.setObjectName(_fromUtf8("label"))
        self.formLayout_3.setWidget(0, QtGui.QFormLayout.LabelRole, self.label)
        self.lineEdit_zFactor = QtGui.QLineEdit(self.groupBox_2)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.lineEdit_zFactor.sizePolicy().hasHeightForWidth())
        self.lineEdit_zFactor.setSizePolicy(sizePolicy)
        self.lineEdit_zFactor.setMaximumSize(QtCore.QSize(16777215, 16777215))
        self.lineEdit_zFactor.setInputMethodHints(QtCore.Qt.ImhDigitsOnly)
        self.lineEdit_zFactor.setAlignment(QtCore.Qt.AlignLeading|QtCore.Qt.AlignLeft|QtCore.Qt.AlignVCenter)
        self.lineEdit_zFactor.setObjectName(_fromUtf8("lineEdit_zFactor"))
        self.formLayout_3.setWidget(0, QtGui.QFormLayout.FieldRole, self.lineEdit_zFactor)
        self.label_2 = QtGui.QLabel(self.groupBox_2)
        self.label_2.setObjectName(_fromUtf8("label_2"))
        self.formLayout_3.setWidget(1, QtGui.QFormLayout.LabelRole, self.label_2)
        self.lineEdit_zShift = QtGui.QLineEdit(self.groupBox_2)
        self.lineEdit_zShift.setObjectName(_fromUtf8("lineEdit_zShift"))
        self.formLayout_3.setWidget(1, QtGui.QFormLayout.FieldRole, self.lineEdit_zShift)
        self.gridLayout.addWidget(self.groupBox_2, 1, 0, 1, 1)
        self.groupBox_1 = QtGui.QGroupBox(WorldPropertiesWidget)
        self.groupBox_1.setObjectName(_fromUtf8("groupBox_1"))
        self.formLayout = QtGui.QFormLayout(self.groupBox_1)
        self.formLayout.setFieldGrowthPolicy(QtGui.QFormLayout.AllNonFixedFieldsGrow)
        self.formLayout.setObjectName(_fromUtf8("formLayout"))
        self.label_6 = QtGui.QLabel(self.groupBox_1)
        self.label_6.setObjectName(_fromUtf8("label_6"))
        self.formLayout.setWidget(0, QtGui.QFormLayout.LabelRole, self.label_6)
        self.lineEdit_MapCanvasExtent = QtGui.QLineEdit(self.groupBox_1)
        self.lineEdit_MapCanvasExtent.setEnabled(True)
        self.lineEdit_MapCanvasExtent.setFocusPolicy(QtCore.Qt.NoFocus)
        self.lineEdit_MapCanvasExtent.setReadOnly(True)
        self.lineEdit_MapCanvasExtent.setObjectName(_fromUtf8("lineEdit_MapCanvasExtent"))
        self.formLayout.setWidget(0, QtGui.QFormLayout.FieldRole, self.lineEdit_MapCanvasExtent)
        self.label_7 = QtGui.QLabel(self.groupBox_1)
        self.label_7.setObjectName(_fromUtf8("label_7"))
        self.formLayout.setWidget(1, QtGui.QFormLayout.LabelRole, self.label_7)
        self.lineEdit_MapCanvasSize = QtGui.QLineEdit(self.groupBox_1)
        self.lineEdit_MapCanvasSize.setEnabled(True)
        self.lineEdit_MapCanvasSize.setFocusPolicy(QtCore.Qt.NoFocus)
        self.lineEdit_MapCanvasSize.setReadOnly(True)
        self.lineEdit_MapCanvasSize.setObjectName(_fromUtf8("lineEdit_MapCanvasSize"))
        self.formLayout.setWidget(1, QtGui.QFormLayout.FieldRole, self.lineEdit_MapCanvasSize)
        self.gridLayout.addWidget(self.groupBox_1, 0, 0, 1, 1)

        self.retranslateUi(WorldPropertiesWidget)
        QtCore.QMetaObject.connectSlotsByName(WorldPropertiesWidget)

    def retranslateUi(self, WorldPropertiesWidget):
        WorldPropertiesWidget.setWindowTitle(_translate("WorldPropertiesWidget", "Form", None))
        self.groupBox_3.setTitle(_translate("WorldPropertiesWidget", "Background", None))
        self.radioButton_Sky.setText(_translate("WorldPropertiesWidget", "Sky", None))
        self.radioButton_Color.setText(_translate("WorldPropertiesWidget", "Solid color", None))
        self.lineEdit_Color.setPlaceholderText(_translate("WorldPropertiesWidget", "0xrrggbb", None))
        self.toolButton_Color.setText(_translate("WorldPropertiesWidget", "...", None))
        self.groupBox_4.setTitle(_translate("WorldPropertiesWidget", "Display of coordinates", None))
        self.radioButton_ProjectCRS.setText(_translate("WorldPropertiesWidget", "Coordinates in the project CRS", None))
        self.radioButton_WGS84.setText(_translate("WorldPropertiesWidget", "Latitude and longitude (WGS84)", None))
        self.groupBox_2.setTitle(_translate("WorldPropertiesWidget", "Scale and shift", None))
        self.label.setText(_translate("WorldPropertiesWidget", "Vertical exaggeration", None))
        self.lineEdit_zFactor.setText(_translate("WorldPropertiesWidget", "1.5", None))
        self.label_2.setText(_translate("WorldPropertiesWidget", "Vertical shift", None))
        self.lineEdit_zShift.setText(_translate("WorldPropertiesWidget", "0", None))
        self.groupBox_1.setTitle(_translate("WorldPropertiesWidget", "Map canvas", None))
        self.label_6.setText(_translate("WorldPropertiesWidget", "Extent", None))
        self.label_7.setText(_translate("WorldPropertiesWidget", "Size", None))

