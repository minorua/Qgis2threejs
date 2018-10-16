# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'D:\Users\minorua\.qgis3\python\developing_plugins\Qgis2threejs\ui\footerlabeldialog.ui'
#
# Created by: PyQt5 UI code generator 5.5
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_FooterLabelDialog(object):
    def setupUi(self, FooterLabelDialog):
        FooterLabelDialog.setObjectName("FooterLabelDialog")
        FooterLabelDialog.resize(532, 136)
        self.verticalLayout = QtWidgets.QVBoxLayout(FooterLabelDialog)
        self.verticalLayout.setObjectName("verticalLayout")
        self.label = QtWidgets.QLabel(FooterLabelDialog)
        self.label.setObjectName("label")
        self.verticalLayout.addWidget(self.label)
        self.textEdit = QtWidgets.QTextEdit(FooterLabelDialog)
        self.textEdit.setObjectName("textEdit")
        self.verticalLayout.addWidget(self.textEdit)
        self.buttonBox = QtWidgets.QDialogButtonBox(FooterLabelDialog)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Apply|QtWidgets.QDialogButtonBox.Cancel|QtWidgets.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName("buttonBox")
        self.verticalLayout.addWidget(self.buttonBox)

        self.retranslateUi(FooterLabelDialog)
        self.buttonBox.accepted.connect(FooterLabelDialog.accept)
        self.buttonBox.rejected.connect(FooterLabelDialog.reject)
        QtCore.QMetaObject.connectSlotsByName(FooterLabelDialog)

    def retranslateUi(self, FooterLabelDialog):
        _translate = QtCore.QCoreApplication.translate
        FooterLabelDialog.setWindowTitle(_translate("FooterLabelDialog", "Footer Label Dialog"))
        self.label.setText(_translate("FooterLabelDialog", "Label Text"))
        self.textEdit.setPlaceholderText(_translate("FooterLabelDialog", "Enter text that you want to display at page bottom. It can contain valid HTML tags."))

