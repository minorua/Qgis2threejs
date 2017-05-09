# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'D:\Users\minorua\.qgis2\python\developing_plugins\Qgis2threejs\ui\settingsdialog.ui'
#
# Created by: PyQt5 UI code generator 5.5
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_SettingsDialog(object):
    def setupUi(self, SettingsDialog):
        SettingsDialog.setObjectName("SettingsDialog")
        SettingsDialog.resize(475, 389)
        self.gridLayout = QtWidgets.QGridLayout(SettingsDialog)
        self.gridLayout.setObjectName("gridLayout")
        self.buttonBox = QtWidgets.QDialogButtonBox(SettingsDialog)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Cancel|QtWidgets.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName("buttonBox")
        self.gridLayout.addWidget(self.buttonBox, 4, 0, 1, 1)
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
        self.gridLayout.addWidget(self.groupBox_2, 1, 0, 1, 1)
        self.groupBox = QtWidgets.QGroupBox(SettingsDialog)
        self.groupBox.setObjectName("groupBox")
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout(self.groupBox)
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.label = QtWidgets.QLabel(self.groupBox)
        self.label.setObjectName("label")
        self.horizontalLayout_2.addWidget(self.label)
        self.lineEdit_BrowserPath = QtWidgets.QLineEdit(self.groupBox)
        self.lineEdit_BrowserPath.setObjectName("lineEdit_BrowserPath")
        self.horizontalLayout_2.addWidget(self.lineEdit_BrowserPath)
        self.toolButton_Browse = QtWidgets.QToolButton(self.groupBox)
        self.toolButton_Browse.setObjectName("toolButton_Browse")
        self.horizontalLayout_2.addWidget(self.toolButton_Browse)
        self.gridLayout.addWidget(self.groupBox, 0, 0, 1, 1)

        self.retranslateUi(SettingsDialog)
        self.buttonBox.accepted.connect(SettingsDialog.accept)
        self.buttonBox.rejected.connect(SettingsDialog.reject)
        QtCore.QMetaObject.connectSlotsByName(SettingsDialog)

    def retranslateUi(self, SettingsDialog):
        _translate = QtCore.QCoreApplication.translate
        SettingsDialog.setWindowTitle(_translate("SettingsDialog", "Settings"))
        self.groupBox_2.setTitle(_translate("SettingsDialog", "Optional Features (Plugins)"))
        self.label_2.setText(_translate("SettingsDialog", "Description"))
        self.groupBox.setTitle(_translate("SettingsDialog", "General"))
        self.label.setText(_translate("SettingsDialog", "Browser path"))
        self.toolButton_Browse.setText(_translate("SettingsDialog", "Browse"))

