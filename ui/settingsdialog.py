# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'D:\Users\minorua\.qgis3\python\developing_plugins\Qgis2threejs\ui\settingsdialog.ui'
#
# Created by: PyQt5 UI code generator 5.5
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_SettingsDialog(object):
    def setupUi(self, SettingsDialog):
        SettingsDialog.setObjectName("SettingsDialog")
        SettingsDialog.resize(475, 326)
        self.verticalLayout_3 = QtWidgets.QVBoxLayout(SettingsDialog)
        self.verticalLayout_3.setObjectName("verticalLayout_3")
        self.groupBox = QtWidgets.QGroupBox(SettingsDialog)
        self.groupBox.setObjectName("groupBox")
        self.verticalLayout_2 = QtWidgets.QVBoxLayout(self.groupBox)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.label = QtWidgets.QLabel(self.groupBox)
        self.label.setObjectName("label")
        self.verticalLayout_2.addWidget(self.label)
        self.horizontalLayout = QtWidgets.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.lineEdit_BrowserPath = QtWidgets.QLineEdit(self.groupBox)
        self.lineEdit_BrowserPath.setObjectName("lineEdit_BrowserPath")
        self.horizontalLayout.addWidget(self.lineEdit_BrowserPath)
        self.pushButton_Browse = QtWidgets.QPushButton(self.groupBox)
        self.pushButton_Browse.setObjectName("pushButton_Browse")
        self.horizontalLayout.addWidget(self.pushButton_Browse)
        self.verticalLayout_2.addLayout(self.horizontalLayout)
        self.verticalLayout_3.addWidget(self.groupBox)
        self.groupBox_2 = QtWidgets.QGroupBox(SettingsDialog)
        self.groupBox_2.setObjectName("groupBox_2")
        self.verticalLayout = QtWidgets.QVBoxLayout(self.groupBox_2)
        self.verticalLayout.setObjectName("verticalLayout")
        self.tableWidget_Plugins = QtWidgets.QTableWidget(self.groupBox_2)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.tableWidget_Plugins.sizePolicy().hasHeightForWidth())
        self.tableWidget_Plugins.setSizePolicy(sizePolicy)
        self.tableWidget_Plugins.setMaximumSize(QtCore.QSize(16777215, 100))
        self.tableWidget_Plugins.setObjectName("tableWidget_Plugins")
        self.tableWidget_Plugins.setColumnCount(0)
        self.tableWidget_Plugins.setRowCount(0)
        self.verticalLayout.addWidget(self.tableWidget_Plugins)
        self.label_2 = QtWidgets.QLabel(self.groupBox_2)
        self.label_2.setObjectName("label_2")
        self.verticalLayout.addWidget(self.label_2)
        self.textBrowser_Plugin = QtWidgets.QTextBrowser(self.groupBox_2)
        self.textBrowser_Plugin.setOpenExternalLinks(True)
        self.textBrowser_Plugin.setObjectName("textBrowser_Plugin")
        self.verticalLayout.addWidget(self.textBrowser_Plugin)
        self.verticalLayout_3.addWidget(self.groupBox_2)
        self.buttonBox = QtWidgets.QDialogButtonBox(SettingsDialog)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Cancel|QtWidgets.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName("buttonBox")
        self.verticalLayout_3.addWidget(self.buttonBox)

        self.retranslateUi(SettingsDialog)
        self.buttonBox.accepted.connect(SettingsDialog.accept)
        self.buttonBox.rejected.connect(SettingsDialog.reject)
        QtCore.QMetaObject.connectSlotsByName(SettingsDialog)

    def retranslateUi(self, SettingsDialog):
        _translate = QtCore.QCoreApplication.translate
        SettingsDialog.setWindowTitle(_translate("SettingsDialog", "Qgis2threejs Plugin Settings"))
        self.groupBox.setTitle(_translate("SettingsDialog", "General"))
        self.label.setText(_translate("SettingsDialog", "Web browser path"))
        self.pushButton_Browse.setText(_translate("SettingsDialog", "Browse..."))
        self.groupBox_2.setTitle(_translate("SettingsDialog", "Optional Features (Plugins)"))
        self.label_2.setText(_translate("SettingsDialog", "Description"))

