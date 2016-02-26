# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'D:\Users\minorua\.qgis2\python\developing_plugins\Qgis2threejs\viewer\ui\propertiesdialog.ui'
#
# Created: Wed Feb 24 10:20:53 2016
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

class Ui_PropertiesDialog(object):
    def setupUi(self, PropertiesDialog):
        PropertiesDialog.setObjectName(_fromUtf8("PropertiesDialog"))
        PropertiesDialog.resize(472, 464)
        self.verticalLayout = QtGui.QVBoxLayout(PropertiesDialog)
        self.verticalLayout.setObjectName(_fromUtf8("verticalLayout"))
        self.scrollArea = QtGui.QScrollArea(PropertiesDialog)
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.setObjectName(_fromUtf8("scrollArea"))
        self.container = QtGui.QWidget()
        self.container.setGeometry(QtCore.QRect(0, 0, 452, 415))
        self.container.setObjectName(_fromUtf8("container"))
        self.scrollArea.setWidget(self.container)
        self.verticalLayout.addWidget(self.scrollArea)
        self.buttonBox = QtGui.QDialogButtonBox(PropertiesDialog)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtGui.QDialogButtonBox.Apply|QtGui.QDialogButtonBox.Cancel|QtGui.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName(_fromUtf8("buttonBox"))
        self.verticalLayout.addWidget(self.buttonBox)

        self.retranslateUi(PropertiesDialog)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL(_fromUtf8("accepted()")), PropertiesDialog.accept)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL(_fromUtf8("rejected()")), PropertiesDialog.reject)
        QtCore.QMetaObject.connectSlotsByName(PropertiesDialog)

    def retranslateUi(self, PropertiesDialog):
        pass

