# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'D:\Users\minorua\.qgis2\python\developing_plugins\Qgis2threejs\ui\controlsproperties.ui'
#
# Created by: PyQt5 UI code generator 5.5
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_ControlsPropertiesWidget(object):
    def setupUi(self, ControlsPropertiesWidget):
        ControlsPropertiesWidget.setObjectName("ControlsPropertiesWidget")
        ControlsPropertiesWidget.resize(284, 377)
        self.gridLayout = QtWidgets.QGridLayout(ControlsPropertiesWidget)
        self.gridLayout.setObjectName("gridLayout")
        self.verticalLayout = QtWidgets.QVBoxLayout()
        self.verticalLayout.setObjectName("verticalLayout")
        self.formLayout = QtWidgets.QFormLayout()
        self.formLayout.setSizeConstraint(QtWidgets.QLayout.SetDefaultConstraint)
        self.formLayout.setObjectName("formLayout")
        self.label = QtWidgets.QLabel(ControlsPropertiesWidget)
        self.label.setObjectName("label")
        self.formLayout.setWidget(0, QtWidgets.QFormLayout.LabelRole, self.label)
        self.comboBox_Controls = QtWidgets.QComboBox(ControlsPropertiesWidget)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.comboBox_Controls.sizePolicy().hasHeightForWidth())
        self.comboBox_Controls.setSizePolicy(sizePolicy)
        self.comboBox_Controls.setObjectName("comboBox_Controls")
        self.formLayout.setWidget(0, QtWidgets.QFormLayout.FieldRole, self.comboBox_Controls)
        self.verticalLayout.addLayout(self.formLayout)
        self.textEdit = QtWidgets.QTextEdit(ControlsPropertiesWidget)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.textEdit.sizePolicy().hasHeightForWidth())
        self.textEdit.setSizePolicy(sizePolicy)
        self.textEdit.setMinimumSize(QtCore.QSize(0, 300))
        self.textEdit.setReadOnly(True)
        self.textEdit.setObjectName("textEdit")
        self.verticalLayout.addWidget(self.textEdit)
        self.gridLayout.addLayout(self.verticalLayout, 0, 0, 1, 1)
        spacerItem = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.gridLayout.addItem(spacerItem, 1, 0, 1, 1)

        self.retranslateUi(ControlsPropertiesWidget)
        QtCore.QMetaObject.connectSlotsByName(ControlsPropertiesWidget)

    def retranslateUi(self, ControlsPropertiesWidget):
        _translate = QtCore.QCoreApplication.translate
        ControlsPropertiesWidget.setWindowTitle(_translate("ControlsPropertiesWidget", "Form"))
        self.label.setText(_translate("ControlsPropertiesWidget", "Controls"))

