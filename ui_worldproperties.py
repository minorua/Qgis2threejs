# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'D:\Users\minorua\.qgis2\python\developing_plugins\Qgis2threejs\worldproperties.ui'
#
# Created: Fri Apr 04 10:19:57 2014
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
        WorldPropertiesWidget.resize(286, 182)
        self.gridLayout = QtGui.QGridLayout(WorldPropertiesWidget)
        self.gridLayout.setObjectName(_fromUtf8("gridLayout"))
        self.formLayout = QtGui.QFormLayout()
        self.formLayout.setFieldGrowthPolicy(QtGui.QFormLayout.AllNonFixedFieldsGrow)
        self.formLayout.setObjectName(_fromUtf8("formLayout"))
        self.label = QtGui.QLabel(WorldPropertiesWidget)
        self.label.setObjectName(_fromUtf8("label"))
        self.formLayout.setWidget(0, QtGui.QFormLayout.LabelRole, self.label)
        self.lineEdit_zFactor = QtGui.QLineEdit(WorldPropertiesWidget)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.lineEdit_zFactor.sizePolicy().hasHeightForWidth())
        self.lineEdit_zFactor.setSizePolicy(sizePolicy)
        self.lineEdit_zFactor.setMaximumSize(QtCore.QSize(16777215, 16777215))
        self.lineEdit_zFactor.setInputMethodHints(QtCore.Qt.ImhDigitsOnly)
        self.lineEdit_zFactor.setAlignment(QtCore.Qt.AlignLeading|QtCore.Qt.AlignLeft|QtCore.Qt.AlignVCenter)
        self.lineEdit_zFactor.setObjectName(_fromUtf8("lineEdit_zFactor"))
        self.formLayout.setWidget(0, QtGui.QFormLayout.FieldRole, self.lineEdit_zFactor)
        self.label_2 = QtGui.QLabel(WorldPropertiesWidget)
        self.label_2.setObjectName(_fromUtf8("label_2"))
        self.formLayout.setWidget(1, QtGui.QFormLayout.LabelRole, self.label_2)
        self.horizontalLayout = QtGui.QHBoxLayout()
        self.horizontalLayout.setObjectName(_fromUtf8("horizontalLayout"))
        self.lineEdit_zShift = QtGui.QLineEdit(WorldPropertiesWidget)
        self.lineEdit_zShift.setObjectName(_fromUtf8("lineEdit_zShift"))
        self.horizontalLayout.addWidget(self.lineEdit_zShift)
        self.toolButton = QtGui.QToolButton(WorldPropertiesWidget)
        self.toolButton.setEnabled(False)
        self.toolButton.setObjectName(_fromUtf8("toolButton"))
        self.horizontalLayout.addWidget(self.toolButton)
        self.formLayout.setLayout(1, QtGui.QFormLayout.FieldRole, self.horizontalLayout)
        self.gridLayout.addLayout(self.formLayout, 1, 0, 1, 1)
        spacerItem = QtGui.QSpacerItem(20, 40, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding)
        self.gridLayout.addItem(spacerItem, 4, 0, 1, 1)
        self.groupBox_2 = QtGui.QGroupBox(WorldPropertiesWidget)
        self.groupBox_2.setObjectName(_fromUtf8("groupBox_2"))
        self.gridLayout_3 = QtGui.QGridLayout(self.groupBox_2)
        self.gridLayout_3.setObjectName(_fromUtf8("gridLayout_3"))
        self.formLayout_2 = QtGui.QFormLayout()
        self.formLayout_2.setObjectName(_fromUtf8("formLayout_2"))
        self.label_6 = QtGui.QLabel(self.groupBox_2)
        self.label_6.setObjectName(_fromUtf8("label_6"))
        self.formLayout_2.setWidget(0, QtGui.QFormLayout.LabelRole, self.label_6)
        self.lineEdit_MapCanvasExtent = QtGui.QLineEdit(self.groupBox_2)
        self.lineEdit_MapCanvasExtent.setEnabled(True)
        self.lineEdit_MapCanvasExtent.setFocusPolicy(QtCore.Qt.NoFocus)
        self.lineEdit_MapCanvasExtent.setReadOnly(True)
        self.lineEdit_MapCanvasExtent.setObjectName(_fromUtf8("lineEdit_MapCanvasExtent"))
        self.formLayout_2.setWidget(0, QtGui.QFormLayout.FieldRole, self.lineEdit_MapCanvasExtent)
        self.label_7 = QtGui.QLabel(self.groupBox_2)
        self.label_7.setObjectName(_fromUtf8("label_7"))
        self.formLayout_2.setWidget(1, QtGui.QFormLayout.LabelRole, self.label_7)
        self.lineEdit_MapCanvasSize = QtGui.QLineEdit(self.groupBox_2)
        self.lineEdit_MapCanvasSize.setEnabled(True)
        self.lineEdit_MapCanvasSize.setFocusPolicy(QtCore.Qt.NoFocus)
        self.lineEdit_MapCanvasSize.setReadOnly(True)
        self.lineEdit_MapCanvasSize.setObjectName(_fromUtf8("lineEdit_MapCanvasSize"))
        self.formLayout_2.setWidget(1, QtGui.QFormLayout.FieldRole, self.lineEdit_MapCanvasSize)
        self.gridLayout_3.addLayout(self.formLayout_2, 0, 0, 1, 1)
        self.gridLayout.addWidget(self.groupBox_2, 0, 0, 1, 1)

        self.retranslateUi(WorldPropertiesWidget)
        QtCore.QMetaObject.connectSlotsByName(WorldPropertiesWidget)

    def retranslateUi(self, WorldPropertiesWidget):
        WorldPropertiesWidget.setWindowTitle(_translate("WorldPropertiesWidget", "Form", None))
        self.label.setText(_translate("WorldPropertiesWidget", "Vertical exaggeration", None))
        self.lineEdit_zFactor.setText(_translate("WorldPropertiesWidget", "1.5", None))
        self.label_2.setText(_translate("WorldPropertiesWidget", "Vertical shift", None))
        self.lineEdit_zShift.setText(_translate("WorldPropertiesWidget", "0", None))
        self.toolButton.setText(_translate("WorldPropertiesWidget", "Calculate", None))
        self.groupBox_2.setTitle(_translate("WorldPropertiesWidget", "Current map canvas", None))
        self.label_6.setText(_translate("WorldPropertiesWidget", "Extent", None))
        self.label_7.setText(_translate("WorldPropertiesWidget", "Size", None))

