# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'D:\Users\minorua\.qgis3\python\developing_plugins\Qgis2threejs\ui\exporttowebdialog.ui'
#
# Created by: PyQt5 UI code generator 5.5
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_ExportToWebDialog(object):
    def setupUi(self, ExportToWebDialog):
        ExportToWebDialog.setObjectName("ExportToWebDialog")
        ExportToWebDialog.resize(495, 168)
        self.formLayout = QtWidgets.QFormLayout(ExportToWebDialog)
        self.formLayout.setObjectName("formLayout")
        self.label_2 = QtWidgets.QLabel(ExportToWebDialog)
        self.label_2.setObjectName("label_2")
        self.formLayout.setWidget(3, QtWidgets.QFormLayout.LabelRole, self.label_2)
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.lineEdit_OutputDir = QtWidgets.QLineEdit(ExportToWebDialog)
        self.lineEdit_OutputDir.setObjectName("lineEdit_OutputDir")
        self.horizontalLayout.addWidget(self.lineEdit_OutputDir)
        self.pushButton_Browse = QtWidgets.QPushButton(ExportToWebDialog)
        self.pushButton_Browse.setObjectName("pushButton_Browse")
        self.horizontalLayout.addWidget(self.pushButton_Browse)
        self.formLayout.setLayout(3, QtWidgets.QFormLayout.FieldRole, self.horizontalLayout)
        self.comboBox_Template = QtWidgets.QComboBox(ExportToWebDialog)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.comboBox_Template.sizePolicy().hasHeightForWidth())
        self.comboBox_Template.setSizePolicy(sizePolicy)
        self.comboBox_Template.setObjectName("comboBox_Template")
        self.formLayout.setWidget(1, QtWidgets.QFormLayout.FieldRole, self.comboBox_Template)
        self.label = QtWidgets.QLabel(ExportToWebDialog)
        self.label.setObjectName("label")
        self.formLayout.setWidget(1, QtWidgets.QFormLayout.LabelRole, self.label)
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.lineEdit_FileTitle = QtWidgets.QLineEdit(ExportToWebDialog)
        self.lineEdit_FileTitle.setObjectName("lineEdit_FileTitle")
        self.horizontalLayout_2.addWidget(self.lineEdit_FileTitle)
        self.label_4 = QtWidgets.QLabel(ExportToWebDialog)
        self.label_4.setObjectName("label_4")
        self.horizontalLayout_2.addWidget(self.label_4)
        self.formLayout.setLayout(5, QtWidgets.QFormLayout.FieldRole, self.horizontalLayout_2)
        self.label_3 = QtWidgets.QLabel(ExportToWebDialog)
        self.label_3.setObjectName("label_3")
        self.formLayout.setWidget(5, QtWidgets.QFormLayout.LabelRole, self.label_3)
        self.horizontalLayout_3 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_3.setObjectName("horizontalLayout_3")
        spacerItem = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.horizontalLayout_3.addItem(spacerItem)
        self.pushButton_Export = QtWidgets.QPushButton(ExportToWebDialog)
        self.pushButton_Export.setObjectName("pushButton_Export")
        self.horizontalLayout_3.addWidget(self.pushButton_Export)
        self.pushButton_Cancel = QtWidgets.QPushButton(ExportToWebDialog)
        self.pushButton_Cancel.setObjectName("pushButton_Cancel")
        self.horizontalLayout_3.addWidget(self.pushButton_Cancel)
        self.formLayout.setLayout(7, QtWidgets.QFormLayout.FieldRole, self.horizontalLayout_3)
        self.checkBox_openPage = QtWidgets.QCheckBox(ExportToWebDialog)
        self.checkBox_openPage.setChecked(True)
        self.checkBox_openPage.setObjectName("checkBox_openPage")
        self.formLayout.setWidget(6, QtWidgets.QFormLayout.FieldRole, self.checkBox_openPage)

        self.retranslateUi(ExportToWebDialog)
        QtCore.QMetaObject.connectSlotsByName(ExportToWebDialog)

    def retranslateUi(self, ExportToWebDialog):
        _translate = QtCore.QCoreApplication.translate
        ExportToWebDialog.setWindowTitle(_translate("ExportToWebDialog", "Export to Web"))
        self.label_2.setText(_translate("ExportToWebDialog", "Output Directory"))
        self.lineEdit_OutputDir.setToolTip(_translate("ExportToWebDialog", "Leave this empty to export files to temporary directory."))
        self.lineEdit_OutputDir.setPlaceholderText(_translate("ExportToWebDialog", "[Temporary directory]"))
        self.pushButton_Browse.setText(_translate("ExportToWebDialog", "Browse..."))
        self.label.setText(_translate("ExportToWebDialog", "Template"))
        self.lineEdit_FileTitle.setText(_translate("ExportToWebDialog", "index"))
        self.label_4.setText(_translate("ExportToWebDialog", ".html"))
        self.label_3.setText(_translate("ExportToWebDialog", "HTML Filename"))
        self.pushButton_Export.setText(_translate("ExportToWebDialog", "Export"))
        self.pushButton_Cancel.setText(_translate("ExportToWebDialog", "Cancel"))
        self.checkBox_openPage.setText(_translate("ExportToWebDialog", "Open exported page in web browser"))

