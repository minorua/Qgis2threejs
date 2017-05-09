# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'D:\Users\minorua\.qgis2\python\developing_plugins\Qgis2threejs\ui\widgetComboEdit.ui'
#
# Created by: PyQt5 UI code generator 5.5
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_ComboEditWidget(object):
    def setupUi(self, ComboEditWidget):
        ComboEditWidget.setObjectName("ComboEditWidget")
        ComboEditWidget.resize(400, 32)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(ComboEditWidget.sizePolicy().hasHeightForWidth())
        ComboEditWidget.setSizePolicy(sizePolicy)
        ComboEditWidget.setMinimumSize(QtCore.QSize(50, 0))
        self.formLayout = QtWidgets.QFormLayout(ComboEditWidget)
        self.formLayout.setContentsMargins(0, 2, 0, 2)
        self.formLayout.setHorizontalSpacing(0)
        self.formLayout.setObjectName("formLayout")
        self.horizontalLayout_1 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_1.setSpacing(3)
        self.horizontalLayout_1.setObjectName("horizontalLayout_1")
        self.label_1 = QtWidgets.QLabel(ComboEditWidget)
        self.label_1.setMinimumSize(QtCore.QSize(80, 0))
        self.label_1.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_1.setObjectName("label_1")
        self.horizontalLayout_1.addWidget(self.label_1)
        self.comboBox = QtWidgets.QComboBox(ComboEditWidget)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.comboBox.sizePolicy().hasHeightForWidth())
        self.comboBox.setSizePolicy(sizePolicy)
        self.comboBox.setMinimumSize(QtCore.QSize(125, 0))
        self.comboBox.setMaximumSize(QtCore.QSize(125, 16777215))
        self.comboBox.setObjectName("comboBox")
        self.horizontalLayout_1.addWidget(self.comboBox)
        self.checkBox = QtWidgets.QCheckBox(ComboEditWidget)
        self.checkBox.setObjectName("checkBox")
        self.horizontalLayout_1.addWidget(self.checkBox)
        self.formLayout.setLayout(0, QtWidgets.QFormLayout.LabelRole, self.horizontalLayout_1)
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_2.setSpacing(3)
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.label_2 = QtWidgets.QLabel(ComboEditWidget)
        self.label_2.setMinimumSize(QtCore.QSize(45, 0))
        self.label_2.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_2.setObjectName("label_2")
        self.horizontalLayout_2.addWidget(self.label_2)
        self.lineEdit = QtWidgets.QLineEdit(ComboEditWidget)
        self.lineEdit.setObjectName("lineEdit")
        self.horizontalLayout_2.addWidget(self.lineEdit)
        self.toolButton = QtWidgets.QToolButton(ComboEditWidget)
        self.toolButton.setObjectName("toolButton")
        self.horizontalLayout_2.addWidget(self.toolButton)
        self.formLayout.setLayout(0, QtWidgets.QFormLayout.FieldRole, self.horizontalLayout_2)

        self.retranslateUi(ComboEditWidget)
        QtCore.QMetaObject.connectSlotsByName(ComboEditWidget)

    def retranslateUi(self, ComboEditWidget):
        _translate = QtCore.QCoreApplication.translate
        ComboEditWidget.setWindowTitle(_translate("ComboEditWidget", "Form"))
        self.label_1.setText(_translate("ComboEditWidget", "Name"))
        self.label_2.setText(_translate("ComboEditWidget", "Value"))
        self.toolButton.setText(_translate("ComboEditWidget", "..."))

