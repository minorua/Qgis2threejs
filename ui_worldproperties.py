# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'D:\Users\minorua\.qgis2\python\developing_plugins\Qgis2threejs\worldproperties.ui'
#
# Created: Thu Mar 27 10:52:07 2014
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

class Ui_WorldPropertiesWidget(object):
    def setupUi(self, WorldPropertiesWidget):
        WorldPropertiesWidget.setObjectName(_fromUtf8("WorldPropertiesWidget"))
        WorldPropertiesWidget.resize(286, 159)
        self.gridLayout = QtGui.QGridLayout(WorldPropertiesWidget)
        self.gridLayout.setObjectName(_fromUtf8("gridLayout"))
        self.formLayout = QtGui.QFormLayout()
        self.formLayout.setObjectName(_fromUtf8("formLayout"))
        self.label = QtGui.QLabel(WorldPropertiesWidget)
        self.label.setObjectName(_fromUtf8("label"))
        self.formLayout.setWidget(0, QtGui.QFormLayout.LabelRole, self.label)
        self.lineEdit_zFactor = QtGui.QLineEdit(WorldPropertiesWidget)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.lineEdit_zFactor.sizePolicy().hasHeightForWidth())
        self.lineEdit_zFactor.setSizePolicy(sizePolicy)
        self.lineEdit_zFactor.setMaximumSize(QtCore.QSize(16777215, 16777215))
        self.lineEdit_zFactor.setInputMethodHints(QtCore.Qt.ImhDigitsOnly)
        self.lineEdit_zFactor.setAlignment(QtCore.Qt.AlignLeading|QtCore.Qt.AlignLeft|QtCore.Qt.AlignVCenter)
        self.lineEdit_zFactor.setObjectName(_fromUtf8("lineEdit_zFactor"))
        self.formLayout.setWidget(0, QtGui.QFormLayout.FieldRole, self.lineEdit_zFactor)
        self.label_2 = QtGui.QLabel(WorldPropertiesWidget)
        self.label_2.setObjectName(_fromUtf8("label_2"))
        self.formLayout.setWidget(1, QtGui.QFormLayout.LabelRole, self.label_2)
        self.horizontalLayout = QtGui.QHBoxLayout()
        self.horizontalLayout.setObjectName(_fromUtf8("horizontalLayout"))
        self.lineEdit = QtGui.QLineEdit(WorldPropertiesWidget)
        self.lineEdit.setObjectName(_fromUtf8("lineEdit"))
        self.horizontalLayout.addWidget(self.lineEdit)
        self.toolButton = QtGui.QToolButton(WorldPropertiesWidget)
        self.toolButton.setObjectName(_fromUtf8("toolButton"))
        self.horizontalLayout.addWidget(self.toolButton)
        self.formLayout.setLayout(1, QtGui.QFormLayout.FieldRole, self.horizontalLayout)
        self.gridLayout.addLayout(self.formLayout, 0, 0, 1, 1)

        self.retranslateUi(WorldPropertiesWidget)
        QtCore.QMetaObject.connectSlotsByName(WorldPropertiesWidget)

    def retranslateUi(self, WorldPropertiesWidget):
        WorldPropertiesWidget.setWindowTitle(_translate("WorldPropertiesWidget", "Form", None))
        self.label.setText(_translate("WorldPropertiesWidget", "Vertical exaggeration", None))
        self.lineEdit_zFactor.setText(_translate("WorldPropertiesWidget", "1.5", None))
        self.label_2.setText(_translate("WorldPropertiesWidget", "Vertical shift", None))
        self.toolButton.setText(_translate("WorldPropertiesWidget", "Calculate", None))

