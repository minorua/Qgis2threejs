# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'D:\Users\minorua\.qgis2\python\developing_plugins\Qgis2threejs\viewer\ui\propertiesdialog.ui'
#
# Created by: PyQt5 UI code generator 5.5
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_PropertiesDialog(object):
    def setupUi(self, PropertiesDialog):
        PropertiesDialog.setObjectName("PropertiesDialog")
        PropertiesDialog.resize(472, 464)
        self.verticalLayout = QtWidgets.QVBoxLayout(PropertiesDialog)
        self.verticalLayout.setObjectName("verticalLayout")
        self.scrollArea = QtWidgets.QScrollArea(PropertiesDialog)
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.setObjectName("scrollArea")
        self.container = QtWidgets.QWidget()
        self.container.setGeometry(QtCore.QRect(0, 0, 452, 415))
        self.container.setObjectName("container")
        self.scrollArea.setWidget(self.container)
        self.verticalLayout.addWidget(self.scrollArea)
        self.buttonBox = QtWidgets.QDialogButtonBox(PropertiesDialog)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Apply|QtWidgets.QDialogButtonBox.Cancel|QtWidgets.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName("buttonBox")
        self.verticalLayout.addWidget(self.buttonBox)

        self.retranslateUi(PropertiesDialog)
        self.buttonBox.accepted.connect(PropertiesDialog.accept)
        self.buttonBox.rejected.connect(PropertiesDialog.reject)
        QtCore.QMetaObject.connectSlotsByName(PropertiesDialog)

    def retranslateUi(self, PropertiesDialog):
        pass

