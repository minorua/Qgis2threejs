# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'D:\Users\lenovo\.qgis2\python\developing_plugins\Qgis2threejs\settingsdialog.ui'
#
# Created: Sat Jan 11 11:27:24 2014
#      by: PyQt4 UI code generator 4.8.3
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    _fromUtf8 = lambda s: s

class Ui_SettingsDialog(object):
    def setupUi(self, SettingsDialog):
        SettingsDialog.setObjectName(_fromUtf8("SettingsDialog"))
        SettingsDialog.resize(475, 93)
        self.gridLayout = QtGui.QGridLayout(SettingsDialog)
        self.gridLayout.setObjectName(_fromUtf8("gridLayout"))
        self.buttonBox = QtGui.QDialogButtonBox(SettingsDialog)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtGui.QDialogButtonBox.Cancel|QtGui.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName(_fromUtf8("buttonBox"))
        self.gridLayout.addWidget(self.buttonBox, 2, 0, 1, 1)
        self.verticalLayout = QtGui.QVBoxLayout()
        self.verticalLayout.setObjectName(_fromUtf8("verticalLayout"))
        self.horizontalLayout = QtGui.QHBoxLayout()
        self.horizontalLayout.setObjectName(_fromUtf8("horizontalLayout"))
        self.label = QtGui.QLabel(SettingsDialog)
        self.label.setObjectName(_fromUtf8("label"))
        self.horizontalLayout.addWidget(self.label)
        self.lineEdit_BrowserPath = QtGui.QLineEdit(SettingsDialog)
        self.lineEdit_BrowserPath.setObjectName(_fromUtf8("lineEdit_BrowserPath"))
        self.horizontalLayout.addWidget(self.lineEdit_BrowserPath)
        self.toolButton_Browse = QtGui.QToolButton(SettingsDialog)
        self.toolButton_Browse.setObjectName(_fromUtf8("toolButton_Browse"))
        self.horizontalLayout.addWidget(self.toolButton_Browse)
        self.verticalLayout.addLayout(self.horizontalLayout)
        self.checkBox_directMode = QtGui.QCheckBox(SettingsDialog)
        self.checkBox_directMode.setEnabled(False)
        self.checkBox_directMode.setObjectName(_fromUtf8("checkBox_directMode"))
        self.verticalLayout.addWidget(self.checkBox_directMode)
        self.gridLayout.addLayout(self.verticalLayout, 0, 0, 1, 1)

        self.retranslateUi(SettingsDialog)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL(_fromUtf8("accepted()")), SettingsDialog.accept)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL(_fromUtf8("rejected()")), SettingsDialog.reject)
        QtCore.QMetaObject.connectSlotsByName(SettingsDialog)

    def retranslateUi(self, SettingsDialog):
        SettingsDialog.setWindowTitle(QtGui.QApplication.translate("SettingsDialog", "Settings", None, QtGui.QApplication.UnicodeUTF8))
        self.label.setText(QtGui.QApplication.translate("SettingsDialog", "Browser path", None, QtGui.QApplication.UnicodeUTF8))
        self.toolButton_Browse.setText(QtGui.QApplication.translate("SettingsDialog", "Browse", None, QtGui.QApplication.UnicodeUTF8))
        self.checkBox_directMode.setText(QtGui.QApplication.translate("SettingsDialog", "Open browser directly from toolbar button.", None, QtGui.QApplication.UnicodeUTF8))

