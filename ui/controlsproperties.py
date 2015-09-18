# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'D:\Users\minorua\.qgis2\python\developing_plugins\Qgis2threejs\ui\controlsproperties.ui'
#
# Created: Fri Sep 18 10:24:51 2015
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

class Ui_ControlsPropertiesWidget(object):
    def setupUi(self, ControlsPropertiesWidget):
        ControlsPropertiesWidget.setObjectName(_fromUtf8("ControlsPropertiesWidget"))
        ControlsPropertiesWidget.resize(284, 377)
        self.gridLayout = QtGui.QGridLayout(ControlsPropertiesWidget)
        self.gridLayout.setObjectName(_fromUtf8("gridLayout"))
        self.verticalLayout = QtGui.QVBoxLayout()
        self.verticalLayout.setObjectName(_fromUtf8("verticalLayout"))
        self.formLayout = QtGui.QFormLayout()
        self.formLayout.setSizeConstraint(QtGui.QLayout.SetDefaultConstraint)
        self.formLayout.setObjectName(_fromUtf8("formLayout"))
        self.label = QtGui.QLabel(ControlsPropertiesWidget)
        self.label.setObjectName(_fromUtf8("label"))
        self.formLayout.setWidget(0, QtGui.QFormLayout.LabelRole, self.label)
        self.comboBox_Controls = QtGui.QComboBox(ControlsPropertiesWidget)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.comboBox_Controls.sizePolicy().hasHeightForWidth())
        self.comboBox_Controls.setSizePolicy(sizePolicy)
        self.comboBox_Controls.setObjectName(_fromUtf8("comboBox_Controls"))
        self.formLayout.setWidget(0, QtGui.QFormLayout.FieldRole, self.comboBox_Controls)
        self.verticalLayout.addLayout(self.formLayout)
        self.textEdit = QtGui.QTextEdit(ControlsPropertiesWidget)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.textEdit.sizePolicy().hasHeightForWidth())
        self.textEdit.setSizePolicy(sizePolicy)
        self.textEdit.setMinimumSize(QtCore.QSize(0, 300))
        self.textEdit.setReadOnly(True)
        self.textEdit.setObjectName(_fromUtf8("textEdit"))
        self.verticalLayout.addWidget(self.textEdit)
        self.gridLayout.addLayout(self.verticalLayout, 0, 0, 1, 1)
        spacerItem = QtGui.QSpacerItem(20, 40, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding)
        self.gridLayout.addItem(spacerItem, 1, 0, 1, 1)

        self.retranslateUi(ControlsPropertiesWidget)
        QtCore.QMetaObject.connectSlotsByName(ControlsPropertiesWidget)

    def retranslateUi(self, ControlsPropertiesWidget):
        ControlsPropertiesWidget.setWindowTitle(_translate("ControlsPropertiesWidget", "Form", None))
        self.label.setText(_translate("ControlsPropertiesWidget", "Controls", None))

