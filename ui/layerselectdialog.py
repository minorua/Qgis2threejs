# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'D:\Users\minorua\.qgis2\python\developing_plugins\Qgis2threejs\ui\layerselectdialog.ui'
#
# Created: Fri Sep 18 10:25:04 2015
#      by: PyQt4 UI code generator 4.10.2
#
# WARNING! All changes made in this file will be lost!

from PyQt import QtCore, QtGui

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

class Ui_LayerSelectDialog(object):
    def setupUi(self, LayerSelectDialog):
        LayerSelectDialog.setObjectName(_fromUtf8("LayerSelectDialog"))
        LayerSelectDialog.resize(439, 425)
        self.verticalLayout = QtGui.QVBoxLayout(LayerSelectDialog)
        self.verticalLayout.setObjectName(_fromUtf8("verticalLayout"))
        self.tabWidget = QtGui.QTabWidget(LayerSelectDialog)
        self.tabWidget.setObjectName(_fromUtf8("tabWidget"))
        self.tab_Tree = QtGui.QWidget()
        self.tab_Tree.setObjectName(_fromUtf8("tab_Tree"))
        self.gridLayout_2 = QtGui.QGridLayout(self.tab_Tree)
        self.gridLayout_2.setObjectName(_fromUtf8("gridLayout_2"))
        self.treeView = QgsLayerTreeView(self.tab_Tree)
        self.treeView.setObjectName(_fromUtf8("treeView"))
        self.gridLayout_2.addWidget(self.treeView, 0, 0, 1, 1)
        self.tabWidget.addTab(self.tab_Tree, _fromUtf8(""))
        self.tab_Preview = QtGui.QWidget()
        self.tab_Preview.setObjectName(_fromUtf8("tab_Preview"))
        self.gridLayout = QtGui.QGridLayout(self.tab_Preview)
        self.gridLayout.setObjectName(_fromUtf8("gridLayout"))
        self.canvas = QgsMapCanvas(self.tab_Preview)
        self.canvas.setObjectName(_fromUtf8("canvas"))
        self.gridLayout.addWidget(self.canvas, 0, 0, 1, 1)
        self.tabWidget.addTab(self.tab_Preview, _fromUtf8(""))
        self.verticalLayout.addWidget(self.tabWidget)
        self.buttonBox = QtGui.QDialogButtonBox(LayerSelectDialog)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(QtGui.QDialogButtonBox.Cancel|QtGui.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName(_fromUtf8("buttonBox"))
        self.verticalLayout.addWidget(self.buttonBox)

        self.retranslateUi(LayerSelectDialog)
        self.tabWidget.setCurrentIndex(0)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL(_fromUtf8("accepted()")), LayerSelectDialog.accept)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL(_fromUtf8("rejected()")), LayerSelectDialog.reject)
        QtCore.QMetaObject.connectSlotsByName(LayerSelectDialog)

    def retranslateUi(self, LayerSelectDialog):
        LayerSelectDialog.setWindowTitle(_translate("LayerSelectDialog", "Select layer(s)", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_Tree), _translate("LayerSelectDialog", "Layers", None))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab_Preview), _translate("LayerSelectDialog", "Preview", None))

from qgis.gui import QgsLayerTreeView, QgsMapCanvas
