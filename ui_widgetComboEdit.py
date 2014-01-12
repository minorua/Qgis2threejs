# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'D:\Users\lenovo\.qgis2\python\developing_plugins\Qgis2threejs\widgetComboEdit.ui'
#
# Created: Mon Jan 06 18:11:49 2014
#      by: PyQt4 UI code generator 4.8.3
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    _fromUtf8 = lambda s: s

class Ui_ComboEditWidget(object):
    def setupUi(self, ComboEditWidget):
        ComboEditWidget.setObjectName(_fromUtf8("ComboEditWidget"))
        ComboEditWidget.resize(191, 65)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(ComboEditWidget.sizePolicy().hasHeightForWidth())
        ComboEditWidget.setSizePolicy(sizePolicy)
        self.gridLayout = QtGui.QGridLayout(ComboEditWidget)
        self.gridLayout.setContentsMargins(0, 3, 0, 8)
        self.gridLayout.setHorizontalSpacing(6)
        self.gridLayout.setVerticalSpacing(2)
        self.gridLayout.setObjectName(_fromUtf8("gridLayout"))
        self.formLayout = QtGui.QFormLayout()
        self.formLayout.setFieldGrowthPolicy(QtGui.QFormLayout.AllNonFixedFieldsGrow)
        self.formLayout.setLabelAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.formLayout.setObjectName(_fromUtf8("formLayout"))
        self.label_1 = QtGui.QLabel(ComboEditWidget)
        self.label_1.setMinimumSize(QtCore.QSize(60, 0))
        self.label_1.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_1.setObjectName(_fromUtf8("label_1"))
        self.formLayout.setWidget(1, QtGui.QFormLayout.LabelRole, self.label_1)
        self.comboBox = QtGui.QComboBox(ComboEditWidget)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.comboBox.sizePolicy().hasHeightForWidth())
        self.comboBox.setSizePolicy(sizePolicy)
        self.comboBox.setMinimumSize(QtCore.QSize(100, 0))
        self.comboBox.setObjectName(_fromUtf8("comboBox"))
        self.formLayout.setWidget(1, QtGui.QFormLayout.FieldRole, self.comboBox)
        self.label_2 = QtGui.QLabel(ComboEditWidget)
        self.label_2.setMinimumSize(QtCore.QSize(60, 0))
        self.label_2.setInputMethodHints(QtCore.Qt.ImhDigitsOnly)
        self.label_2.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_2.setMargin(0)
        self.label_2.setIndent(-1)
        self.label_2.setObjectName(_fromUtf8("label_2"))
        self.formLayout.setWidget(2, QtGui.QFormLayout.LabelRole, self.label_2)
        self.lineEdit = QtGui.QLineEdit(ComboEditWidget)
        self.lineEdit.setObjectName(_fromUtf8("lineEdit"))
        self.formLayout.setWidget(2, QtGui.QFormLayout.FieldRole, self.lineEdit)
        self.gridLayout.addLayout(self.formLayout, 0, 0, 1, 1)

        self.retranslateUi(ComboEditWidget)
        QtCore.QMetaObject.connectSlotsByName(ComboEditWidget)

    def retranslateUi(self, ComboEditWidget):
        ComboEditWidget.setWindowTitle(QtGui.QApplication.translate("ComboEditWidget", "Form", None, QtGui.QApplication.UnicodeUTF8))
        self.label_1.setText(QtGui.QApplication.translate("ComboEditWidget", "Name", None, QtGui.QApplication.UnicodeUTF8))
        self.label_2.setText(QtGui.QApplication.translate("ComboEditWidget", "Size", None, QtGui.QApplication.UnicodeUTF8))

