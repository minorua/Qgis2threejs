# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'D:\Users\minorua\.qgis2\python\developing_plugins\Qgis2threejs\ui\qgis2threejsdialog.ui'
#
# Created: Tue May 06 13:21:59 2014
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

class Ui_Qgis2threejsDialog(object):
    def setupUi(self, Qgis2threejsDialog):
        Qgis2threejsDialog.setObjectName(_fromUtf8("Qgis2threejsDialog"))
        Qgis2threejsDialog.resize(720, 513)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(Qgis2threejsDialog.sizePolicy().hasHeightForWidth())
        Qgis2threejsDialog.setSizePolicy(sizePolicy)
        self.gridLayout = QtGui.QGridLayout(Qgis2threejsDialog)
        self.gridLayout.setObjectName(_fromUtf8("gridLayout"))
        self.verticalLayout = QtGui.QVBoxLayout()
        self.verticalLayout.setObjectName(_fromUtf8("verticalLayout"))
        self.formLayout_3 = QtGui.QFormLayout()
        self.formLayout_3.setFieldGrowthPolicy(QtGui.QFormLayout.AllNonFixedFieldsGrow)
        self.formLayout_3.setObjectName(_fromUtf8("formLayout_3"))
        self.label = QtGui.QLabel(Qgis2threejsDialog)
        self.label.setObjectName(_fromUtf8("label"))
        self.formLayout_3.setWidget(0, QtGui.QFormLayout.LabelRole, self.label)
        self.comboBox_Template = QtGui.QComboBox(Qgis2threejsDialog)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.comboBox_Template.sizePolicy().hasHeightForWidth())
        self.comboBox_Template.setSizePolicy(sizePolicy)
        self.comboBox_Template.setObjectName(_fromUtf8("comboBox_Template"))
        self.formLayout_3.setWidget(0, QtGui.QFormLayout.FieldRole, self.comboBox_Template)
        self.verticalLayout.addLayout(self.formLayout_3)
        self.splitter = QtGui.QSplitter(Qgis2threejsDialog)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.splitter.sizePolicy().hasHeightForWidth())
        self.splitter.setSizePolicy(sizePolicy)
        self.splitter.setOrientation(QtCore.Qt.Horizontal)
        self.splitter.setObjectName(_fromUtf8("splitter"))
        self.treeWidget = QtGui.QTreeWidget(self.splitter)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Preferred, QtGui.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.treeWidget.sizePolicy().hasHeightForWidth())
        self.treeWidget.setSizePolicy(sizePolicy)
        self.treeWidget.setMinimumSize(QtCore.QSize(150, 0))
        self.treeWidget.setObjectName(_fromUtf8("treeWidget"))
        self.treeWidget.headerItem().setText(0, _fromUtf8("1"))
        self.treeWidget.header().setVisible(False)
        self.scrollArea = QtGui.QScrollArea(self.splitter)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(1)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.scrollArea.sizePolicy().hasHeightForWidth())
        self.scrollArea.setSizePolicy(sizePolicy)
        self.scrollArea.setMinimumSize(QtCore.QSize(300, 0))
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.setObjectName(_fromUtf8("scrollArea"))
        self.scrollAreaWidgetContents = QtGui.QWidget()
        self.scrollAreaWidgetContents.setGeometry(QtCore.QRect(0, 0, 437, 386))
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.scrollAreaWidgetContents.sizePolicy().hasHeightForWidth())
        self.scrollAreaWidgetContents.setSizePolicy(sizePolicy)
        self.scrollAreaWidgetContents.setObjectName(_fromUtf8("scrollAreaWidgetContents"))
        self.gridLayout_13 = QtGui.QGridLayout(self.scrollAreaWidgetContents)
        self.gridLayout_13.setMargin(0)
        self.gridLayout_13.setObjectName(_fromUtf8("gridLayout_13"))
        self.propertyPagesContainer = QtGui.QVBoxLayout()
        self.propertyPagesContainer.setObjectName(_fromUtf8("propertyPagesContainer"))
        self.gridLayout_13.addLayout(self.propertyPagesContainer, 0, 0, 1, 1)
        self.scrollArea.setWidget(self.scrollAreaWidgetContents)
        self.verticalLayout.addWidget(self.splitter)
        self.label_3 = QtGui.QLabel(Qgis2threejsDialog)
        self.label_3.setObjectName(_fromUtf8("label_3"))
        self.verticalLayout.addWidget(self.label_3)
        self.horizontalLayout_2 = QtGui.QHBoxLayout()
        self.horizontalLayout_2.setObjectName(_fromUtf8("horizontalLayout_2"))
        self.lineEdit_OutputFilename = QtGui.QLineEdit(Qgis2threejsDialog)
        self.lineEdit_OutputFilename.setObjectName(_fromUtf8("lineEdit_OutputFilename"))
        self.horizontalLayout_2.addWidget(self.lineEdit_OutputFilename)
        self.toolButton_Browse = QtGui.QToolButton(Qgis2threejsDialog)
        self.toolButton_Browse.setObjectName(_fromUtf8("toolButton_Browse"))
        self.horizontalLayout_2.addWidget(self.toolButton_Browse)
        self.verticalLayout.addLayout(self.horizontalLayout_2)
        self.horizontalLayout_7 = QtGui.QHBoxLayout()
        self.horizontalLayout_7.setObjectName(_fromUtf8("horizontalLayout_7"))
        self.progressBar = QtGui.QProgressBar(Qgis2threejsDialog)
        self.progressBar.setProperty("value", 24)
        self.progressBar.setAlignment(QtCore.Qt.AlignCenter)
        self.progressBar.setTextVisible(True)
        self.progressBar.setObjectName(_fromUtf8("progressBar"))
        self.horizontalLayout_7.addWidget(self.progressBar)
        spacerItem = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.horizontalLayout_7.addItem(spacerItem)
        self.pushButton_Run = QtGui.QPushButton(Qgis2threejsDialog)
        self.pushButton_Run.setDefault(True)
        self.pushButton_Run.setObjectName(_fromUtf8("pushButton_Run"))
        self.horizontalLayout_7.addWidget(self.pushButton_Run)
        self.pushButton_Close = QtGui.QPushButton(Qgis2threejsDialog)
        self.pushButton_Close.setObjectName(_fromUtf8("pushButton_Close"))
        self.horizontalLayout_7.addWidget(self.pushButton_Close)
        self.verticalLayout.addLayout(self.horizontalLayout_7)
        self.gridLayout.addLayout(self.verticalLayout, 3, 0, 1, 1)

        self.retranslateUi(Qgis2threejsDialog)
        QtCore.QMetaObject.connectSlotsByName(Qgis2threejsDialog)

    def retranslateUi(self, Qgis2threejsDialog):
        Qgis2threejsDialog.setWindowTitle(_translate("Qgis2threejsDialog", "Qgis2threejs", None))
        self.label.setText(_translate("Qgis2threejsDialog", "Template file", None))
        self.label_3.setText(_translate("Qgis2threejsDialog", "Output HTML file path", None))
        self.toolButton_Browse.setText(_translate("Qgis2threejsDialog", "Browse...", None))
        self.progressBar.setFormat(_translate("Qgis2threejsDialog", "%p%", None))
        self.pushButton_Run.setText(_translate("Qgis2threejsDialog", "Run", None))
        self.pushButton_Close.setText(_translate("Qgis2threejsDialog", "Close", None))

