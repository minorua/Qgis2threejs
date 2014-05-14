# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'D:\Users\minorua\.qgis2\python\developing_plugins\Qgis2threejs\ui\vectorproperties.ui'
#
# Created: Wed May 14 16:02:28 2014
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
        VectorPropertiesWidget.resize(278, 271)
        self.verticalLayout_2 = QtGui.QVBoxLayout(VectorPropertiesWidget)
        self.verticalLayout_2.setObjectName(_fromUtf8("verticalLayout_2"))
        self.groupBox_zCoordinate = QtGui.QGroupBox(VectorPropertiesWidget)
        self.groupBox_zCoordinate.setObjectName(_fromUtf8("groupBox_zCoordinate"))
        self.gridLayout_9 = QtGui.QGridLayout(self.groupBox_zCoordinate)
        self.gridLayout_9.setMargin(3)
        self.gridLayout_9.setObjectName(_fromUtf8("gridLayout_9"))
        self.verticalLayout_zCoordinate = QtGui.QVBoxLayout()
        self.verticalLayout_zCoordinate.setObjectName(_fromUtf8("verticalLayout_zCoordinate"))
        self.gridLayout_9.addLayout(self.verticalLayout_zCoordinate, 1, 0, 1, 1)
        self.verticalLayout_2.addWidget(self.groupBox_zCoordinate)
        self.groupBox_Styles = QtGui.QGroupBox(VectorPropertiesWidget)
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
        self.formLayout_4.setFieldGrowthPolicy(QtGui.QFormLayout.AllNonFixedFieldsGrow)
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
        self.label_ObjectTypeMessage = QtGui.QLabel(self.groupBox_Styles)
        font = QtGui.QFont()
        font.setBold(True)
        font.setWeight(75)
        self.label_ObjectTypeMessage.setFont(font)
        self.label_ObjectTypeMessage.setStyleSheet(_fromUtf8("font-weight: bold;"))
        self.label_ObjectTypeMessage.setAlignment(QtCore.Qt.AlignCenter)
        self.label_ObjectTypeMessage.setWordWrap(True)
        self.label_ObjectTypeMessage.setObjectName(_fromUtf8("label_ObjectTypeMessage"))
        self.verticalLayout_Styles.addWidget(self.label_ObjectTypeMessage)
        self.gridLayout_8.addLayout(self.verticalLayout_Styles, 0, 0, 1, 1)
        self.verticalLayout_2.addWidget(self.groupBox_Styles)
        self.groupBox_Attrs = QtGui.QGroupBox(VectorPropertiesWidget)
        self.groupBox_Attrs.setObjectName(_fromUtf8("groupBox_Attrs"))
        self.gridLayout = QtGui.QGridLayout(self.groupBox_Attrs)
        self.gridLayout.setMargin(3)
        self.gridLayout.setObjectName(_fromUtf8("gridLayout"))
        self.formLayout_Label = QtGui.QFormLayout()
        self.formLayout_Label.setContentsMargins(2, -1, 2, -1)
        self.formLayout_Label.setObjectName(_fromUtf8("formLayout_Label"))
        self.label = QtGui.QLabel(self.groupBox_Attrs)
        self.label.setEnabled(False)
        self.label.setMinimumSize(QtCore.QSize(70, 0))
        self.label.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label.setObjectName(_fromUtf8("label"))
        self.formLayout_Label.setWidget(0, QtGui.QFormLayout.LabelRole, self.label)
        self.comboBox_Label = QtGui.QComboBox(self.groupBox_Attrs)
        self.comboBox_Label.setEnabled(False)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.comboBox_Label.sizePolicy().hasHeightForWidth())
        self.comboBox_Label.setSizePolicy(sizePolicy)
        self.comboBox_Label.setObjectName(_fromUtf8("comboBox_Label"))
        self.formLayout_Label.setWidget(0, QtGui.QFormLayout.FieldRole, self.comboBox_Label)
        self.gridLayout.addLayout(self.formLayout_Label, 5, 0, 1, 1)
        self.verticalLayout_Label = QtGui.QVBoxLayout()
        self.verticalLayout_Label.setObjectName(_fromUtf8("verticalLayout_Label"))
        self.gridLayout.addLayout(self.verticalLayout_Label, 6, 0, 1, 1)
        self.verticalLayout = QtGui.QVBoxLayout()
        self.verticalLayout.setContentsMargins(6, -1, -1, -1)
        self.verticalLayout.setObjectName(_fromUtf8("verticalLayout"))
        self.checkBox_ExportAttrs = QtGui.QCheckBox(self.groupBox_Attrs)
        self.checkBox_ExportAttrs.setChecked(False)
        self.checkBox_ExportAttrs.setObjectName(_fromUtf8("checkBox_ExportAttrs"))
        self.verticalLayout.addWidget(self.checkBox_ExportAttrs)
        self.gridLayout.addLayout(self.verticalLayout, 0, 0, 1, 1)
        self.verticalLayout_2.addWidget(self.groupBox_Attrs)
        spacerItem = QtGui.QSpacerItem(20, 40, QtGui.QSizePolicy.Minimum, QtGui.QSizePolicy.Expanding)
        self.verticalLayout_2.addItem(spacerItem)

        self.retranslateUi(VectorPropertiesWidget)
        QtCore.QMetaObject.connectSlotsByName(VectorPropertiesWidget)

    def retranslateUi(self, VectorPropertiesWidget):
        VectorPropertiesWidget.setWindowTitle(_translate("VectorPropertiesWidget", "Form", None))
        self.groupBox_zCoordinate.setTitle(_translate("VectorPropertiesWidget", "Z coordinate", None))
        self.groupBox_Styles.setTitle(_translate("VectorPropertiesWidget", "Style", None))
        self.label_ObjectType.setText(_translate("VectorPropertiesWidget", "Object type", None))
        self.label_ObjectTypeMessage.setText(_translate("VectorPropertiesWidget", "This type is experimental. JSON model loading fails with some files.", None))
        self.groupBox_Attrs.setTitle(_translate("VectorPropertiesWidget", "Attribute and label", None))
        self.label.setText(_translate("VectorPropertiesWidget", "Label field", None))
        self.checkBox_ExportAttrs.setText(_translate("VectorPropertiesWidget", "Export attributes", None))

