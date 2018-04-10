# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'D:\Users\minorua\.qgis3\python\developing_plugins\Qgis2threejs\ui\layerselectdialog.ui'
#
# Created by: PyQt5 UI code generator 5.5
#
# WARNING! All changes made in this file will be lost!

from PyQt5 import QtCore, QtGui, QtWidgets

class Ui_LayerSelectDialog(object):
    def setupUi(self, LayerSelectDialog):
        LayerSelectDialog.setObjectName("LayerSelectDialog")
        LayerSelectDialog.resize(439, 425)
        self.verticalLayout = QtWidgets.QVBoxLayout(LayerSelectDialog)
        self.verticalLayout.setObjectName("verticalLayout")
        self.tabWidget = QtWidgets.QTabWidget(LayerSelectDialog)
        self.tabWidget.setObjectName("tabWidget")
        self.tab_Tree = QtWidgets.QWidget()
        self.tab_Tree.setObjectName("tab_Tree")
        self.gridLayout_2 = QtWidgets.QGridLayout(self.tab_Tree)
        self.gridLayout_2.setObjectName("gridLayout_2")
        self.treeView = QgsLayerTreeView(self.tab_Tree)
        self.treeView.setObjectName("treeView")
        self.gridLayout_2.addWidget(self.treeView, 0, 0, 1, 1)
        self.tabWidget.addTab(self.tab_Tree, "")
        self.tab_Preview = QtWidgets.QWidget()
        self.tab_Preview.setObjectName("tab_Preview")
        self.gridLayout = QtWidgets.QGridLayout(self.tab_Preview)
        self.gridLayout.setObjectName("gridLayout")
        self.canvas = QgsMapCanvas(self.tab_Preview)
        self.canvas.setObjectName("canvas")
        self.gridLayout.addWidget(self.canvas, 0, 0, 1, 1)
        self.tabWidget.addTab(self.tab_Preview, "")
        self.verticalLayout.addWidget(self.tabWidget)
        self.buttonBox = QtWidgets.QDialogButtonBox(LayerSelectDialog)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Cancel|QtWidgets.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName("buttonBox")
        self.verticalLayout.addWidget(self.buttonBox)

        self.retranslateUi(LayerSelectDialog)
        self.tabWidget.setCurrentIndex(0)
        self.buttonBox.accepted.connect(LayerSelectDialog.accept)
        self.buttonBox.rejected.connect(LayerSelectDialog.reject)
        QtCore.QMetaObject.connectSlotsByName(LayerSelectDialog)

    def retranslateUi(self, LayerSelectDialog):
        _translate = QtCore.QCoreApplication.translate
        LayerSelectDialog.setWindowTitle(_translate("LayerSelectDialog", "Select layer(s)"))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_Tree), _translate("LayerSelectDialog", "Layers"))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_Preview), _translate("LayerSelectDialog", "Preview"))

from qgis.gui import QgsLayerTreeView, QgsMapCanvas
