# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'D:\Users\minorua\.qgis3\python\developing_plugins\Qgis2threejs\ui\imagesavedialog.ui'
#
# Created by: PyQt5 UI code generator 5.11.3
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_ImageSaveDialog(object):
    def setupUi(self, ImageSaveDialog):
        ImageSaveDialog.setObjectName("ImageSaveDialog")
        ImageSaveDialog.resize(394, 97)
        self.verticalLayout = QtWidgets.QVBoxLayout(ImageSaveDialog)
        self.verticalLayout.setObjectName("verticalLayout")
        self.formLayout = QtWidgets.QFormLayout()
        self.formLayout.setObjectName("formLayout")
        self.label = QtWidgets.QLabel(ImageSaveDialog)
        self.label.setObjectName("label")
        self.formLayout.setWidget(0, QtWidgets.QFormLayout.LabelRole, self.label)
        self.label_2 = QtWidgets.QLabel(ImageSaveDialog)
        self.label_2.setObjectName("label_2")
        self.formLayout.setWidget(1, QtWidgets.QFormLayout.LabelRole, self.label_2)
        self.spinBox_Width = QtWidgets.QSpinBox(ImageSaveDialog)
        self.spinBox_Width.setMinimum(1)
        self.spinBox_Width.setMaximum(99999)
        self.spinBox_Width.setProperty("value", 1)
        self.spinBox_Width.setObjectName("spinBox_Width")
        self.formLayout.setWidget(0, QtWidgets.QFormLayout.FieldRole, self.spinBox_Width)
        self.spinBox_Height = QtWidgets.QSpinBox(ImageSaveDialog)
        self.spinBox_Height.setMinimum(1)
        self.spinBox_Height.setMaximum(99999)
        self.spinBox_Height.setProperty("value", 1)
        self.spinBox_Height.setObjectName("spinBox_Height")
        self.formLayout.setWidget(1, QtWidgets.QFormLayout.FieldRole, self.spinBox_Height)
        self.verticalLayout.addLayout(self.formLayout)
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.pushButton_Copy = QtWidgets.QPushButton(ImageSaveDialog)
        self.pushButton_Copy.setObjectName("pushButton_Copy")
        self.horizontalLayout.addWidget(self.pushButton_Copy)
        self.buttonBox = QtWidgets.QDialogButtonBox(ImageSaveDialog)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Cancel|QtWidgets.QDialogButtonBox.Save)
        self.buttonBox.setObjectName("buttonBox")
        self.horizontalLayout.addWidget(self.buttonBox)
        self.verticalLayout.addLayout(self.horizontalLayout)

        self.retranslateUi(ImageSaveDialog)
        self.buttonBox.accepted.connect(ImageSaveDialog.accept)
        self.buttonBox.rejected.connect(ImageSaveDialog.reject)
        QtCore.QMetaObject.connectSlotsByName(ImageSaveDialog)

    def retranslateUi(self, ImageSaveDialog):
        _translate = QtCore.QCoreApplication.translate
        ImageSaveDialog.setWindowTitle(_translate("ImageSaveDialog", "Save Scene as Image"))
        self.label.setText(_translate("ImageSaveDialog", "Output width"))
        self.label_2.setText(_translate("ImageSaveDialog", "Output height"))
        self.spinBox_Width.setSuffix(_translate("ImageSaveDialog", " px"))
        self.spinBox_Height.setSuffix(_translate("ImageSaveDialog", " px"))
        self.pushButton_Copy.setText(_translate("ImageSaveDialog", "Copy to Clipboard"))

