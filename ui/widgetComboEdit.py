# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'D:\Users\minorua\.qgis3\python\developing_plugins\Qgis2threejs\ui\widgetComboEdit.ui'
#
# Created by: PyQt5 UI code generator 5.5
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_ComboEditWidget(object):
    def setupUi(self, ComboEditWidget):
        ComboEditWidget.setObjectName("ComboEditWidget")
        ComboEditWidget.resize(259, 58)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(ComboEditWidget.sizePolicy().hasHeightForWidth())
        ComboEditWidget.setSizePolicy(sizePolicy)
        ComboEditWidget.setMinimumSize(QtCore.QSize(50, 0))
        self.formLayout = QtWidgets.QFormLayout(ComboEditWidget)
        self.formLayout.setContentsMargins(0, 2, 0, 2)
        self.formLayout.setObjectName("formLayout")
        self.gridLayout_1 = QtWidgets.QGridLayout()
        self.gridLayout_1.setObjectName("gridLayout_1")
        self.comboBox = QtWidgets.QComboBox(ComboEditWidget)
        self.comboBox.setMinimumSize(QtCore.QSize(125, 0))
        self.comboBox.setObjectName("comboBox")
        self.gridLayout_1.addWidget(self.comboBox, 0, 2, 1, 1)
        self.checkBox = QtWidgets.QCheckBox(ComboEditWidget)
        self.checkBox.setObjectName("checkBox")
        self.gridLayout_1.addWidget(self.checkBox, 0, 4, 1, 1)
        self.toolButton = QtWidgets.QToolButton(ComboEditWidget)
        self.toolButton.setObjectName("toolButton")
        self.gridLayout_1.addWidget(self.toolButton, 0, 5, 1, 1)
        self.formLayout.setLayout(0, QtWidgets.QFormLayout.FieldRole, self.gridLayout_1)
        self.label_1 = QtWidgets.QLabel(ComboEditWidget)
        self.label_1.setObjectName("label_1")
        self.formLayout.setWidget(0, QtWidgets.QFormLayout.LabelRole, self.label_1)
        self.expression = QgsFieldExpressionWidget(ComboEditWidget)
        self.expression.setMinimumSize(QtCore.QSize(20, 20))
        self.expression.setObjectName("expression")
        self.formLayout.setWidget(1, QtWidgets.QFormLayout.FieldRole, self.expression)
        self.label_2 = QtWidgets.QLabel(ComboEditWidget)
        self.label_2.setObjectName("label_2")
        self.formLayout.setWidget(1, QtWidgets.QFormLayout.LabelRole, self.label_2)

        self.retranslateUi(ComboEditWidget)
        QtCore.QMetaObject.connectSlotsByName(ComboEditWidget)

    def retranslateUi(self, ComboEditWidget):
        _translate = QtCore.QCoreApplication.translate
        ComboEditWidget.setWindowTitle(_translate("ComboEditWidget", "Form"))
        self.toolButton.setText(_translate("ComboEditWidget", "..."))
        self.label_1.setText(_translate("ComboEditWidget", "Name"))
        self.label_2.setText(_translate("ComboEditWidget", "Value"))

from qgis.gui import QgsFieldExpressionWidget
