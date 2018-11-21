# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'D:\Users\minorua\.qgis3\python\developing_plugins\Qgis2threejs\ui\hflabeldialog.ui'
#
# Created by: PyQt5 UI code generator 5.11.3
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_HFLabelDialog(object):
    def setupUi(self, HFLabelDialog):
        HFLabelDialog.setObjectName("HFLabelDialog")
        HFLabelDialog.resize(532, 231)
        self.verticalLayout = QtWidgets.QVBoxLayout(HFLabelDialog)
        self.verticalLayout.setObjectName("verticalLayout")
        self.label = QtWidgets.QLabel(HFLabelDialog)
        self.label.setObjectName("label")
        self.verticalLayout.addWidget(self.label)
        self.textEdit_Header = QtWidgets.QTextEdit(HFLabelDialog)
        self.textEdit_Header.setObjectName("textEdit_Header")
        self.verticalLayout.addWidget(self.textEdit_Header)
        self.label_2 = QtWidgets.QLabel(HFLabelDialog)
        self.label_2.setObjectName("label_2")
        self.verticalLayout.addWidget(self.label_2)
        self.textEdit_Footer = QtWidgets.QTextEdit(HFLabelDialog)
        self.textEdit_Footer.setObjectName("textEdit_Footer")
        self.verticalLayout.addWidget(self.textEdit_Footer)
        self.buttonBox = QtWidgets.QDialogButtonBox(HFLabelDialog)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Apply|QtWidgets.QDialogButtonBox.Cancel|QtWidgets.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName("buttonBox")
        self.verticalLayout.addWidget(self.buttonBox)

        self.retranslateUi(HFLabelDialog)
        self.buttonBox.accepted.connect(HFLabelDialog.accept)
        self.buttonBox.rejected.connect(HFLabelDialog.reject)
        QtCore.QMetaObject.connectSlotsByName(HFLabelDialog)
        HFLabelDialog.setTabOrder(self.textEdit_Header, self.textEdit_Footer)

    def retranslateUi(self, HFLabelDialog):
        _translate = QtCore.QCoreApplication.translate
        HFLabelDialog.setWindowTitle(_translate("HFLabelDialog", "Header/Footer Label Dialog"))
        self.label.setText(_translate("HFLabelDialog", "Header Label Text"))
        self.textEdit_Header.setPlaceholderText(_translate("HFLabelDialog", "Enter text that you want to display at page top. It can contain valid HTML tags."))
        self.label_2.setText(_translate("HFLabelDialog", "Footer Label Text"))
        self.textEdit_Footer.setPlaceholderText(_translate("HFLabelDialog", "Enter text that you want to display at page bottom. It can contain valid HTML tags."))

