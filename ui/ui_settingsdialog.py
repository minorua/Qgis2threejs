# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'D:\Users\minorua\.qgis2\python\developing_plugins\Qgis2threejs\ui\settingsdialog.ui'
#
# Created: Wed May 27 11:29:05 2015
#      by: PyQt4 UI code generator 4.10.2
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    def _fromUtf8(s):
        return s

try:
    _encoding = QtGui.QApplication.UnicodeUTF8
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig, _encoding)
except AttributeError:
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig)

class Ui_SettingsDialog(object):
    def setupUi(self, SettingsDialog):
        SettingsDialog.setObjectName(_fromUtf8("SettingsDialog"))
        SettingsDialog.resize(475, 389)
        self.gridLayout = QtGui.QGridLayout(SettingsDialog)
        self.gridLayout.setObjectName(_fromUtf8("gridLayout"))
        self.buttonBox = QtGui.QDialogButtonBox(SettingsDialog)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtGui.QDialogButtonBox.Cancel|QtGui.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName(_fromUtf8("buttonBox"))
        self.gridLayout.addWidget(self.buttonBox, 4, 0, 1, 1)
        self.groupBox_2 = QtGui.QGroupBox(SettingsDialog)
        self.groupBox_2.setObjectName(_fromUtf8("groupBox_2"))
        self.verticalLayout = QtGui.QVBoxLayout(self.groupBox_2)
        self.verticalLayout.setObjectName(_fromUtf8("verticalLayout"))
        self.tableWidget_Plugins = QtGui.QTableWidget(self.groupBox_2)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.tableWidget_Plugins.sizePolicy().hasHeightForWidth())
        self.tableWidget_Plugins.setSizePolicy(sizePolicy)
        self.tableWidget_Plugins.setMaximumSize(QtCore.QSize(16777215, 100))
        self.tableWidget_Plugins.setObjectName(_fromUtf8("tableWidget_Plugins"))
        self.tableWidget_Plugins.setColumnCount(0)
        self.tableWidget_Plugins.setRowCount(0)
        self.verticalLayout.addWidget(self.tableWidget_Plugins)
        self.label_2 = QtGui.QLabel(self.groupBox_2)
        self.label_2.setObjectName(_fromUtf8("label_2"))
        self.verticalLayout.addWidget(self.label_2)
        self.textBrowser_Plugin = QtGui.QTextBrowser(self.groupBox_2)
        self.textBrowser_Plugin.setOpenExternalLinks(True)
        self.textBrowser_Plugin.setObjectName(_fromUtf8("textBrowser_Plugin"))
        self.verticalLayout.addWidget(self.textBrowser_Plugin)
        self.gridLayout.addWidget(self.groupBox_2, 1, 0, 1, 1)
        self.groupBox = QtGui.QGroupBox(SettingsDialog)
        self.groupBox.setObjectName(_fromUtf8("groupBox"))
        self.horizontalLayout_2 = QtGui.QHBoxLayout(self.groupBox)
        self.horizontalLayout_2.setObjectName(_fromUtf8("horizontalLayout_2"))
        self.label = QtGui.QLabel(self.groupBox)
        self.label.setObjectName(_fromUtf8("label"))
        self.horizontalLayout_2.addWidget(self.label)
        self.lineEdit_BrowserPath = QtGui.QLineEdit(self.groupBox)
        self.lineEdit_BrowserPath.setObjectName(_fromUtf8("lineEdit_BrowserPath"))
        self.horizontalLayout_2.addWidget(self.lineEdit_BrowserPath)
        self.toolButton_Browse = QtGui.QToolButton(self.groupBox)
        self.toolButton_Browse.setObjectName(_fromUtf8("toolButton_Browse"))
        self.horizontalLayout_2.addWidget(self.toolButton_Browse)
        self.gridLayout.addWidget(self.groupBox, 0, 0, 1, 1)

        self.retranslateUi(SettingsDialog)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL(_fromUtf8("accepted()")), SettingsDialog.accept)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL(_fromUtf8("rejected()")), SettingsDialog.reject)
        QtCore.QMetaObject.connectSlotsByName(SettingsDialog)

    def retranslateUi(self, SettingsDialog):
        SettingsDialog.setWindowTitle(_translate("SettingsDialog", "Settings", None))
        self.groupBox_2.setTitle(_translate("SettingsDialog", "Optional Features (Plugins)", None))
        self.label_2.setText(_translate("SettingsDialog", "Description", None))
        self.groupBox.setTitle(_translate("SettingsDialog", "General", None))
        self.label.setText(_translate("SettingsDialog", "Browser path", None))
        self.toolButton_Browse.setText(_translate("SettingsDialog", "Browse", None))

