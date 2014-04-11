# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'D:\Users\minorua\.qgis2\python\developing_plugins\Qgis2threejs\ui\vectorproperties.ui'
#
# Created: Fri Apr 11 17:08:24 2014
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

class Ui_VectorPropertiesWidget(object):
    def setupUi(self, VectorPropertiesWidget):
        VectorPropertiesWidget.setObjectName(_fromUtf8("VectorPropertiesWidget"))
        VectorPropertiesWidget.resize(278, 300)
        self.verticalLayout_2 = QtGui.QVBoxLayout(VectorPropertiesWidget)
        self.verticalLayout_2.setObjectName(_fromUtf8("verticalLayout_2"))
        self.scrollArea = QtGui.QScrollArea(VectorPropertiesWidget)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.scrollArea.sizePolicy().hasHeightForWidth())
        self.scrollArea.setSizePolicy(sizePolicy)
        self.scrollArea.setMinimumSize(QtCore.QSize(240, 0))
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.setObjectName(_fromUtf8("scrollArea"))
        self.scrollAreaWidgetContents = QtGui.QWidget()
        self.scrollAreaWidgetContents.setGeometry(QtCore.QRect(0, 0, 258, 280))
        self.scrollAreaWidgetContents.setObjectName(_fromUtf8("scrollAreaWidgetContents"))
        self.gridLayout_10 = QtGui.QGridLayout(self.scrollAreaWidgetContents)
        self.gridLayout_10.setObjectName(_fromUtf8("gridLayout_10"))
        self.groupBox_zCoordinate = QtGui.QGroupBox(self.scrollAreaWidgetContents)
        self.groupBox_zCoordinate.setObjectName(_fromUtf8("groupBox_zCoordinate"))
        self.gridLayout_9 = QtGui.QGridLayout(self.groupBox_zCoordinate)
        self.gridLayout_9.setMargin(3)
        self.gridLayout_9.setObjectName(_fromUtf8("gridLayout_9"))
        self.verticalLayout_zCoordinate = QtGui.QVBoxLayout()
        self.verticalLayout_zCoordinate.setObjectName(_fromUtf8("verticalLayout_zCoordinate"))
        self.gridLayout_9.addLayout(self.verticalLayout_zCoordinate, 1, 0, 1, 1)
        self.gridLayout_10.addWidget(self.groupBox_zCoordinate, 0, 0, 1, 1)
        self.groupBox_Styles = QtGui.QGroupBox(self.scrollAreaWidgetContents)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.groupBox_Styles.sizePolicy().hasHeightForWidth())
        self.groupBox_Styles.setSizePolicy(sizePolicy)
        self.groupBox_Styles.setMinimumSize(QtCore.QSize(0, 0))
        self.groupBox_Styles.setObjectName(_fromUtf8("groupBox_Styles"))
        self.gridLayout_8 = QtGui.QGridLayout(self.groupBox_Styles)
        self.gridLayout_8.setMargin(3)
        self.gridLayout_8.setObjectName(_fromUtf8("gridLayout_8"))
        self.verticalLayout_Styles = QtGui.QVBoxLayout()
        self.verticalLayout_Styles.setObjectName(_fromUtf8("verticalLayout_Styles"))
        self.formLayout_4 = QtGui.QFormLayout()
        self.formLayout_4.setContentsMargins(2, -1, 2, -1)
        self.formLayout_4.setObjectName(_fromUtf8("formLayout_4"))
        self.label_ObjectType = QtGui.QLabel(self.groupBox_Styles)
        self.label_ObjectType.setMinimumSize(QtCore.QSize(70, 0))
        self.label_ObjectType.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_ObjectType.setObjectName(_fromUtf8("label_ObjectType"))
        self.formLayout_4.setWidget(0, QtGui.QFormLayout.LabelRole, self.label_ObjectType)
        self.comboBox_ObjectType = QtGui.QComboBox(self.groupBox_Styles)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.comboBox_ObjectType.sizePolicy().hasHeightForWidth())
        self.comboBox_ObjectType.setSizePolicy(sizePolicy)
        self.comboBox_ObjectType.setObjectName(_fromUtf8("comboBox_ObjectType"))
        self.formLayout_4.setWidget(0, QtGui.QFormLayout.FieldRole, self.comboBox_ObjectType)
        self.verticalLayout_Styles.addLayout(self.formLayout_4)
        self.gridLayout_8.addLayout(self.verticalLayout_Styles, 0, 0, 1, 1)
        self.gridLayout_10.addWidget(self.groupBox_Styles, 1, 0, 1, 1)
        self.groupBox_Attrs = QtGui.QGroupBox(self.scrollAreaWidgetContents)
        self.groupBox_Attrs.setObjectName(_fromUtf8("groupBox_Attrs"))
        self.gridLayout = QtGui.QGridLayout(self.groupBox_Attrs)
        self.gridLayout.setObjectName(_fromUtf8("gridLayout"))
        self.verticalLayout = QtGui.QVBoxLayout()
        self.verticalLayout.setObjectName(_fromUtf8("verticalLayout"))
        self.checkBox_ExportAttrs = QtGui.QCheckBox(self.groupBox_Attrs)
        self.checkBox_ExportAttrs.setChecked(True)
        self.checkBox_ExportAttrs.setObjectName(_fromUtf8("checkBox_ExportAttrs"))
        self.verticalLayout.addWidget(self.checkBox_ExportAttrs)
        self.gridLayout.addLayout(self.verticalLayout, 0, 0, 1, 1)
        self.formLayout_Label = QtGui.QFormLayout()
        self.formLayout_Label.setObjectName(_fromUtf8("formLayout_Label"))
        self.label = QtGui.QLabel(self.groupBox_Attrs)
        self.label.setMinimumSize(QtCore.QSize(70, 0))
        self.label.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label.setObjectName(_fromUtf8("label"))
        self.formLayout_Label.setWidget(0, QtGui.QFormLayout.LabelRole, self.label)
        self.comboBox_Label = QtGui.QComboBox(self.groupBox_Attrs)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.comboBox_Label.sizePolicy().hasHeightForWidth())
        self.comboBox_Label.setSizePolicy(sizePolicy)
        self.comboBox_Label.setObjectName(_fromUtf8("comboBox_Label"))
        self.formLayout_Label.setWidget(0, QtGui.QFormLayout.FieldRole, self.comboBox_Label)
        self.gridLayout.addLayout(self.formLayout_Label, 1, 0, 1, 1)
        self.gridLayout_10.addWidget(self.groupBox_Attrs, 2, 0, 1, 1)
        spacerItem = QtGui.QSpacerItem(20, 40, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding)
        self.gridLayout_10.addItem(spacerItem, 3, 0, 1, 1)
        self.scrollArea.setWidget(self.scrollAreaWidgetContents)
        self.verticalLayout_2.addWidget(self.scrollArea)

        self.retranslateUi(VectorPropertiesWidget)
        QtCore.QMetaObject.connectSlotsByName(VectorPropertiesWidget)

    def retranslateUi(self, VectorPropertiesWidget):
        VectorPropertiesWidget.setWindowTitle(_translate("VectorPropertiesWidget", "Form", None))
        self.groupBox_zCoordinate.setTitle(_translate("VectorPropertiesWidget", "Z coordinate", None))
        self.groupBox_Styles.setTitle(_translate("VectorPropertiesWidget", "Styles", None))
        self.label_ObjectType.setText(_translate("VectorPropertiesWidget", "Object type", None))
        self.groupBox_Attrs.setTitle(_translate("VectorPropertiesWidget", "Attributes", None))
        self.checkBox_ExportAttrs.setText(_translate("VectorPropertiesWidget", "Export attributes", None))
        self.label.setText(_translate("VectorPropertiesWidget", "Label", None))

