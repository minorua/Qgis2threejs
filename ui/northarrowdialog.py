# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'D:\Users\minorua\.qgis3\python\developing_plugins\Qgis2threejs\ui\northarrowdialog.ui'
#
# Created by: PyQt5 UI code generator 5.5
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_NorthArrowDialog(object):
    def setupUi(self, NorthArrowDialog):
        NorthArrowDialog.setObjectName("NorthArrowDialog")
        NorthArrowDialog.resize(281, 101)
        self.verticalLayout = QtWidgets.QVBoxLayout(NorthArrowDialog)
        self.verticalLayout.setObjectName("verticalLayout")
        self.groupBox = QtWidgets.QGroupBox(NorthArrowDialog)
        self.groupBox.setCheckable(True)
        self.groupBox.setChecked(False)
        self.groupBox.setObjectName("groupBox")
        self.gridLayout = QtWidgets.QGridLayout(self.groupBox)
        self.gridLayout.setObjectName("gridLayout")
        self.label = QtWidgets.QLabel(self.groupBox)
        self.label.setObjectName("label")
        self.gridLayout.addWidget(self.label, 0, 0, 1, 1)
        self.colorButton = QgsColorButton(self.groupBox)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.colorButton.sizePolicy().hasHeightForWidth())
        self.colorButton.setSizePolicy(sizePolicy)
        self.colorButton.setText("")
        self.colorButton.setObjectName("colorButton")
        self.gridLayout.addWidget(self.colorButton, 0, 1, 1, 1)
        self.verticalLayout.addWidget(self.groupBox)
        self.buttonBox = QtWidgets.QDialogButtonBox(NorthArrowDialog)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Apply|QtWidgets.QDialogButtonBox.Cancel|QtWidgets.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName("buttonBox")
        self.verticalLayout.addWidget(self.buttonBox)

        self.retranslateUi(NorthArrowDialog)
        self.buttonBox.accepted.connect(NorthArrowDialog.accept)
        self.buttonBox.rejected.connect(NorthArrowDialog.reject)
        QtCore.QMetaObject.connectSlotsByName(NorthArrowDialog)

    def retranslateUi(self, NorthArrowDialog):
        _translate = QtCore.QCoreApplication.translate
        NorthArrowDialog.setWindowTitle(_translate("NorthArrowDialog", "North Arrow"))
        self.groupBox.setTitle(_translate("NorthArrowDialog", "Enable North Arrow"))
        self.label.setText(_translate("NorthArrowDialog", "Color"))

from qgis.gui import QgsColorButton
