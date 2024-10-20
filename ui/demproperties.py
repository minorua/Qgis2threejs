# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'demproperties.ui'
#
# Created by: PyQt5 UI code generator 5.15.4
#
# WARNING: Any manual changes made to this file will be lost when pyuic5 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_DEMPropertiesWidget(object):
    def setupUi(self, DEMPropertiesWidget):
        DEMPropertiesWidget.setObjectName("DEMPropertiesWidget")
        DEMPropertiesWidget.resize(451, 686)
        self.verticalLayout = QtWidgets.QVBoxLayout(DEMPropertiesWidget)
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout.setObjectName("verticalLayout")
        self.tabWidget = QtWidgets.QTabWidget(DEMPropertiesWidget)
        self.tabWidget.setTabPosition(QtWidgets.QTabWidget.West)
        self.tabWidget.setObjectName("tabWidget")
        self.tab = QtWidgets.QWidget()
        self.tab.setObjectName("tab")
        self.verticalLayout_2 = QtWidgets.QVBoxLayout(self.tab)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.groupBox_Geometry = QtWidgets.QGroupBox(self.tab)
        self.groupBox_Geometry.setObjectName("groupBox_Geometry")
        self.verticalLayout_6 = QtWidgets.QVBoxLayout(self.groupBox_Geometry)
        self.verticalLayout_6.setObjectName("verticalLayout_6")
        self.horizontalLayout_Resampling = QtWidgets.QHBoxLayout()
        self.horizontalLayout_Resampling.setObjectName("horizontalLayout_Resampling")
        self.label_Resampling = QtWidgets.QLabel(self.groupBox_Geometry)
        self.label_Resampling.setMinimumSize(QtCore.QSize(110, 0))
        self.label_Resampling.setObjectName("label_Resampling")
        self.horizontalLayout_Resampling.addWidget(self.label_Resampling)
        self.horizontalSlider_DEMSize = QtWidgets.QSlider(self.groupBox_Geometry)
        self.horizontalSlider_DEMSize.setEnabled(True)
        self.horizontalSlider_DEMSize.setMinimum(1)
        self.horizontalSlider_DEMSize.setMaximum(6)
        self.horizontalSlider_DEMSize.setSingleStep(1)
        self.horizontalSlider_DEMSize.setPageStep(1)
        self.horizontalSlider_DEMSize.setProperty("value", 2)
        self.horizontalSlider_DEMSize.setOrientation(QtCore.Qt.Horizontal)
        self.horizontalSlider_DEMSize.setTickPosition(QtWidgets.QSlider.TicksBelow)
        self.horizontalSlider_DEMSize.setTickInterval(1)
        self.horizontalSlider_DEMSize.setObjectName("horizontalSlider_DEMSize")
        self.horizontalLayout_Resampling.addWidget(self.horizontalSlider_DEMSize)
        self.label_ResamplingLevel = QtWidgets.QLabel(self.groupBox_Geometry)
        self.label_ResamplingLevel.setMinimumSize(QtCore.QSize(10, 0))
        self.label_ResamplingLevel.setObjectName("label_ResamplingLevel")
        self.horizontalLayout_Resampling.addWidget(self.label_ResamplingLevel)
        self.verticalLayout_6.addLayout(self.horizontalLayout_Resampling)
        self.formLayout_Altitude = QtWidgets.QFormLayout()
        self.formLayout_Altitude.setObjectName("formLayout_Altitude")
        self.label_Altitude = QtWidgets.QLabel(self.groupBox_Geometry)
        self.label_Altitude.setMinimumSize(QtCore.QSize(110, 0))
        self.label_Altitude.setObjectName("label_Altitude")
        self.formLayout_Altitude.setWidget(0, QtWidgets.QFormLayout.LabelRole, self.label_Altitude)
        self.lineEdit_Altitude = QtWidgets.QLineEdit(self.groupBox_Geometry)
        self.lineEdit_Altitude.setObjectName("lineEdit_Altitude")
        self.formLayout_Altitude.setWidget(0, QtWidgets.QFormLayout.FieldRole, self.lineEdit_Altitude)
        self.verticalLayout_6.addLayout(self.formLayout_Altitude)
        self.verticalLayout_Tiles = QtWidgets.QVBoxLayout()
        self.verticalLayout_Tiles.setObjectName("verticalLayout_Tiles")
        self.verticalLayout_6.addLayout(self.verticalLayout_Tiles)
        self.verticalLayout_Clip = QtWidgets.QVBoxLayout()
        self.verticalLayout_Clip.setObjectName("verticalLayout_Clip")
        self.checkBox_Clip = QtWidgets.QCheckBox(self.groupBox_Geometry)
        self.checkBox_Clip.setObjectName("checkBox_Clip")
        self.verticalLayout_Clip.addWidget(self.checkBox_Clip)
        self.comboBox_ClipLayer = QtWidgets.QComboBox(self.groupBox_Geometry)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.comboBox_ClipLayer.sizePolicy().hasHeightForWidth())
        self.comboBox_ClipLayer.setSizePolicy(sizePolicy)
        self.comboBox_ClipLayer.setMaximumSize(QtCore.QSize(220, 16777215))
        self.comboBox_ClipLayer.setObjectName("comboBox_ClipLayer")
        self.verticalLayout_Clip.addWidget(self.comboBox_ClipLayer)
        self.verticalLayout_6.addLayout(self.verticalLayout_Clip)
        self.verticalLayout_2.addWidget(self.groupBox_Geometry)
        self.groupBox_Material = QtWidgets.QGroupBox(self.tab)
        self.groupBox_Material.setObjectName("groupBox_Material")
        self.verticalLayout_4 = QtWidgets.QVBoxLayout(self.groupBox_Material)
        self.verticalLayout_4.setObjectName("verticalLayout_4")
        self.gridLayout_MtlBtns = QtWidgets.QGridLayout()
        self.gridLayout_MtlBtns.setObjectName("gridLayout_MtlBtns")
        self.toolButton_RemoveMtl = QtWidgets.QToolButton(self.groupBox_Material)
        self.toolButton_RemoveMtl.setObjectName("toolButton_RemoveMtl")
        self.gridLayout_MtlBtns.addWidget(self.toolButton_RemoveMtl, 0, 1, 1, 1)
        self.toolButton_AddMtl = QtWidgets.QToolButton(self.groupBox_Material)
        self.toolButton_AddMtl.setObjectName("toolButton_AddMtl")
        self.gridLayout_MtlBtns.addWidget(self.toolButton_AddMtl, 0, 0, 1, 1)
        spacerItem = QtWidgets.QSpacerItem(40, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        self.gridLayout_MtlBtns.addItem(spacerItem, 0, 2, 1, 1)
        self.verticalLayout_4.addLayout(self.gridLayout_MtlBtns)
        self.listWidget_Materials = QtWidgets.QListWidget(self.groupBox_Material)
        self.listWidget_Materials.setObjectName("listWidget_Materials")
        self.verticalLayout_4.addWidget(self.listWidget_Materials)
        self.gridLayout_Mtl = QtWidgets.QGridLayout()
        self.gridLayout_Mtl.setObjectName("gridLayout_Mtl")
        self.label_ImageFile = QtWidgets.QLabel(self.groupBox_Material)
        self.label_ImageFile.setObjectName("label_ImageFile")
        self.gridLayout_Mtl.addWidget(self.label_ImageFile, 4, 0, 1, 1)
        self.lineEdit_ImageFile = QtWidgets.QLineEdit(self.groupBox_Material)
        self.lineEdit_ImageFile.setObjectName("lineEdit_ImageFile")
        self.gridLayout_Mtl.addWidget(self.lineEdit_ImageFile, 4, 1, 1, 1)
        self.horizontalSlider_Opacity = QtWidgets.QSlider(self.groupBox_Material)
        self.horizontalSlider_Opacity.setMaximum(100)
        self.horizontalSlider_Opacity.setProperty("value", 100)
        self.horizontalSlider_Opacity.setOrientation(QtCore.Qt.Horizontal)
        self.horizontalSlider_Opacity.setObjectName("horizontalSlider_Opacity")
        self.gridLayout_Mtl.addWidget(self.horizontalSlider_Opacity, 8, 1, 1, 1)
        self.label_17 = QtWidgets.QLabel(self.groupBox_Material)
        self.label_17.setObjectName("label_17")
        self.gridLayout_Mtl.addWidget(self.label_17, 8, 0, 1, 1)
        self.spinBox_Opacity = QtWidgets.QSpinBox(self.groupBox_Material)
        self.spinBox_Opacity.setEnabled(True)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.spinBox_Opacity.sizePolicy().hasHeightForWidth())
        self.spinBox_Opacity.setSizePolicy(sizePolicy)
        self.spinBox_Opacity.setPrefix("")
        self.spinBox_Opacity.setMinimum(0)
        self.spinBox_Opacity.setMaximum(100)
        self.spinBox_Opacity.setSingleStep(1)
        self.spinBox_Opacity.setProperty("value", 100)
        self.spinBox_Opacity.setObjectName("spinBox_Opacity")
        self.gridLayout_Mtl.addWidget(self.spinBox_Opacity, 8, 2, 1, 1)
        self.toolButton_ImageFile = QtWidgets.QToolButton(self.groupBox_Material)
        self.toolButton_ImageFile.setObjectName("toolButton_ImageFile")
        self.gridLayout_Mtl.addWidget(self.toolButton_ImageFile, 4, 2, 1, 1)
        self.colorButton_Color = QgsColorButton(self.groupBox_Material)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.colorButton_Color.sizePolicy().hasHeightForWidth())
        self.colorButton_Color.setSizePolicy(sizePolicy)
        self.colorButton_Color.setObjectName("colorButton_Color")
        self.gridLayout_Mtl.addWidget(self.colorButton_Color, 5, 1, 1, 2)
        self.toolButton_SelectLayer = QtWidgets.QToolButton(self.groupBox_Material)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.toolButton_SelectLayer.sizePolicy().hasHeightForWidth())
        self.toolButton_SelectLayer.setSizePolicy(sizePolicy)
        self.toolButton_SelectLayer.setObjectName("toolButton_SelectLayer")
        self.gridLayout_Mtl.addWidget(self.toolButton_SelectLayer, 1, 2, 1, 1)
        self.label_LayerImage = QtWidgets.QLabel(self.groupBox_Material)
        self.label_LayerImage.setText("")
        self.label_LayerImage.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_LayerImage.setObjectName("label_LayerImage")
        self.gridLayout_Mtl.addWidget(self.label_LayerImage, 1, 1, 1, 1)
        self.checkBox_Shading = QtWidgets.QCheckBox(self.groupBox_Material)
        self.checkBox_Shading.setChecked(True)
        self.checkBox_Shading.setObjectName("checkBox_Shading")
        self.gridLayout_Mtl.addWidget(self.checkBox_Shading, 10, 0, 1, 3)
        self.label_TextureSize = QtWidgets.QLabel(self.groupBox_Material)
        self.label_TextureSize.setMinimumSize(QtCore.QSize(110, 0))
        self.label_TextureSize.setObjectName("label_TextureSize")
        self.gridLayout_Mtl.addWidget(self.label_TextureSize, 2, 0, 1, 1)
        self.label_Color = QtWidgets.QLabel(self.groupBox_Material)
        self.label_Color.setObjectName("label_Color")
        self.gridLayout_Mtl.addWidget(self.label_Color, 5, 0, 1, 1)
        self.label_Layers = QtWidgets.QLabel(self.groupBox_Material)
        self.label_Layers.setObjectName("label_Layers")
        self.gridLayout_Mtl.addWidget(self.label_Layers, 1, 0, 1, 1)
        self.checkBox_TransparentBackground = QtWidgets.QCheckBox(self.groupBox_Material)
        self.checkBox_TransparentBackground.setObjectName("checkBox_TransparentBackground")
        self.gridLayout_Mtl.addWidget(self.checkBox_TransparentBackground, 9, 0, 1, 3)
        self.comboBox_TextureSize = QtWidgets.QComboBox(self.groupBox_Material)
        self.comboBox_TextureSize.setEditable(True)
        self.comboBox_TextureSize.setObjectName("comboBox_TextureSize")
        self.gridLayout_Mtl.addWidget(self.comboBox_TextureSize, 2, 1, 1, 2)
        self.label_Format = QtWidgets.QLabel(self.groupBox_Material)
        self.label_Format.setObjectName("label_Format")
        self.gridLayout_Mtl.addWidget(self.label_Format, 3, 0, 1, 1)
        self.gridLayout_2 = QtWidgets.QGridLayout()
        self.gridLayout_2.setObjectName("gridLayout_2")
        self.radioButton_PNG = QtWidgets.QRadioButton(self.groupBox_Material)
        self.radioButton_PNG.setChecked(True)
        self.radioButton_PNG.setObjectName("radioButton_PNG")
        self.gridLayout_2.addWidget(self.radioButton_PNG, 0, 0, 1, 1)
        self.radioButton_JPEG = QtWidgets.QRadioButton(self.groupBox_Material)
        self.radioButton_JPEG.setObjectName("radioButton_JPEG")
        self.gridLayout_2.addWidget(self.radioButton_JPEG, 0, 1, 1, 1)
        self.gridLayout_Mtl.addLayout(self.gridLayout_2, 3, 1, 1, 2)
        self.verticalLayout_4.addLayout(self.gridLayout_Mtl)
        self.verticalLayout_2.addWidget(self.groupBox_Material)
        self.groupBox_Tiles = QtWidgets.QGroupBox(self.tab)
        self.groupBox_Tiles.setObjectName("groupBox_Tiles")
        self.verticalLayout_3 = QtWidgets.QVBoxLayout(self.groupBox_Tiles)
        self.verticalLayout_3.setObjectName("verticalLayout_3")
        self.checkBox_Tiles = QtWidgets.QCheckBox(self.groupBox_Tiles)
        self.checkBox_Tiles.setObjectName("checkBox_Tiles")
        self.verticalLayout_3.addWidget(self.checkBox_Tiles)
        self.gridLayout_Tiles = QtWidgets.QGridLayout()
        self.gridLayout_Tiles.setObjectName("gridLayout_Tiles")
        self.label_Roughness = QtWidgets.QLabel(self.groupBox_Tiles)
        self.label_Roughness.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_Roughness.setObjectName("label_Roughness")
        self.gridLayout_Tiles.addWidget(self.label_Roughness, 0, 2, 1, 1)
        self.spinBox_Roughening = QtWidgets.QSpinBox(self.groupBox_Tiles)
        self.spinBox_Roughening.setMinimumSize(QtCore.QSize(70, 0))
        self.spinBox_Roughening.setMaximum(64)
        self.spinBox_Roughening.setProperty("value", 1)
        self.spinBox_Roughening.setObjectName("spinBox_Roughening")
        self.gridLayout_Tiles.addWidget(self.spinBox_Roughening, 0, 3, 1, 1)
        self.spinBox_Size = QtWidgets.QSpinBox(self.groupBox_Tiles)
        self.spinBox_Size.setMinimumSize(QtCore.QSize(70, 0))
        self.spinBox_Size.setMinimum(3)
        self.spinBox_Size.setMaximum(99)
        self.spinBox_Size.setSingleStep(2)
        self.spinBox_Size.setProperty("value", 3)
        self.spinBox_Size.setObjectName("spinBox_Size")
        self.gridLayout_Tiles.addWidget(self.spinBox_Size, 0, 1, 1, 1)
        self.label_2 = QtWidgets.QLabel(self.groupBox_Tiles)
        self.label_2.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_2.setObjectName("label_2")
        self.gridLayout_Tiles.addWidget(self.label_2, 0, 0, 1, 1)
        self.verticalLayout_3.addLayout(self.gridLayout_Tiles)
        self.verticalLayout_2.addWidget(self.groupBox_Tiles)
        spacerItem1 = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.verticalLayout_2.addItem(spacerItem1)
        self.tabWidget.addTab(self.tab, "")
        self.tabOthers = QtWidgets.QWidget()
        self.tabOthers.setObjectName("tabOthers")
        self.gridLayout = QtWidgets.QGridLayout(self.tabOthers)
        self.gridLayout.setObjectName("gridLayout")
        self.colorButton_Edge = QgsColorButton(self.tabOthers)
        self.colorButton_Edge.setEnabled(False)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.colorButton_Edge.sizePolicy().hasHeightForWidth())
        self.colorButton_Edge.setSizePolicy(sizePolicy)
        self.colorButton_Edge.setObjectName("colorButton_Edge")
        self.gridLayout.addWidget(self.colorButton_Edge, 2, 1, 1, 1)
        self.checkBox_Sides = QtWidgets.QCheckBox(self.tabOthers)
        self.checkBox_Sides.setObjectName("checkBox_Sides")
        self.gridLayout.addWidget(self.checkBox_Sides, 0, 0, 1, 1)
        self.lineEdit_Bottom = QtWidgets.QLineEdit(self.tabOthers)
        self.lineEdit_Bottom.setObjectName("lineEdit_Bottom")
        self.gridLayout.addWidget(self.lineEdit_Bottom, 1, 1, 1, 1)
        self.colorButton_Side = QgsColorButton(self.tabOthers)
        self.colorButton_Side.setEnabled(False)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.colorButton_Side.sizePolicy().hasHeightForWidth())
        self.colorButton_Side.setSizePolicy(sizePolicy)
        self.colorButton_Side.setObjectName("colorButton_Side")
        self.gridLayout.addWidget(self.colorButton_Side, 0, 1, 1, 1)
        self.checkBox_Wireframe = QtWidgets.QCheckBox(self.tabOthers)
        self.checkBox_Wireframe.setObjectName("checkBox_Wireframe")
        self.gridLayout.addWidget(self.checkBox_Wireframe, 3, 0, 1, 1)
        self.checkBox_Frame = QtWidgets.QCheckBox(self.tabOthers)
        self.checkBox_Frame.setObjectName("checkBox_Frame")
        self.gridLayout.addWidget(self.checkBox_Frame, 2, 0, 1, 1)
        self.label_Bottom = QtWidgets.QLabel(self.tabOthers)
        self.label_Bottom.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.label_Bottom.setObjectName("label_Bottom")
        self.gridLayout.addWidget(self.label_Bottom, 1, 0, 1, 1)
        self.label = QtWidgets.QLabel(self.tabOthers)
        self.label.setMinimumSize(QtCore.QSize(110, 0))
        self.label.setObjectName("label")
        self.gridLayout.addWidget(self.label, 5, 0, 1, 1)
        self.lineEdit_Name = QtWidgets.QLineEdit(self.tabOthers)
        self.lineEdit_Name.setObjectName("lineEdit_Name")
        self.gridLayout.addWidget(self.lineEdit_Name, 5, 1, 1, 1)
        self.colorButton_Wireframe = QgsColorButton(self.tabOthers)
        self.colorButton_Wireframe.setEnabled(False)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.colorButton_Wireframe.sizePolicy().hasHeightForWidth())
        self.colorButton_Wireframe.setSizePolicy(sizePolicy)
        self.colorButton_Wireframe.setObjectName("colorButton_Wireframe")
        self.gridLayout.addWidget(self.colorButton_Wireframe, 3, 1, 1, 1)
        self.checkBox_Visible = QtWidgets.QCheckBox(self.tabOthers)
        self.checkBox_Visible.setChecked(True)
        self.checkBox_Visible.setObjectName("checkBox_Visible")
        self.gridLayout.addWidget(self.checkBox_Visible, 6, 0, 1, 2)
        self.checkBox_Clickable = QtWidgets.QCheckBox(self.tabOthers)
        self.checkBox_Clickable.setChecked(True)
        self.checkBox_Clickable.setObjectName("checkBox_Clickable")
        self.gridLayout.addWidget(self.checkBox_Clickable, 7, 0, 1, 2)
        spacerItem2 = QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
        self.gridLayout.addItem(spacerItem2, 8, 0, 1, 2)
        self.line = QtWidgets.QFrame(self.tabOthers)
        self.line.setFrameShape(QtWidgets.QFrame.HLine)
        self.line.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.line.setObjectName("line")
        self.gridLayout.addWidget(self.line, 4, 0, 1, 2)
        self.tabWidget.addTab(self.tabOthers, "")
        self.verticalLayout.addWidget(self.tabWidget)

        self.retranslateUi(DEMPropertiesWidget)
        self.tabWidget.setCurrentIndex(0)
        self.checkBox_Clip.toggled['bool'].connect(self.comboBox_ClipLayer.setVisible)
        self.checkBox_Clip.toggled['bool'].connect(self.checkBox_Frame.setDisabled)
        self.horizontalSlider_DEMSize.valueChanged['int'].connect(self.label_ResamplingLevel.setNum)
        self.horizontalSlider_Opacity.valueChanged['int'].connect(self.spinBox_Opacity.setValue)
        self.spinBox_Opacity.valueChanged['int'].connect(self.horizontalSlider_Opacity.setValue)
        self.checkBox_Sides.toggled['bool'].connect(self.colorButton_Side.setEnabled)
        self.checkBox_Clip.toggled['bool'].connect(self.checkBox_Wireframe.setDisabled)
        self.checkBox_Frame.toggled['bool'].connect(self.colorButton_Edge.setEnabled)
        self.checkBox_Wireframe.toggled['bool'].connect(self.colorButton_Wireframe.setEnabled)
        self.checkBox_Sides.toggled['bool'].connect(self.label_Bottom.setVisible)
        self.checkBox_Sides.toggled['bool'].connect(self.lineEdit_Bottom.setVisible)
        self.radioButton_PNG.toggled['bool'].connect(self.checkBox_TransparentBackground.setEnabled)
        QtCore.QMetaObject.connectSlotsByName(DEMPropertiesWidget)
        DEMPropertiesWidget.setTabOrder(self.tabWidget, self.horizontalSlider_DEMSize)
        DEMPropertiesWidget.setTabOrder(self.horizontalSlider_DEMSize, self.lineEdit_Altitude)
        DEMPropertiesWidget.setTabOrder(self.lineEdit_Altitude, self.checkBox_Clip)
        DEMPropertiesWidget.setTabOrder(self.checkBox_Clip, self.comboBox_ClipLayer)
        DEMPropertiesWidget.setTabOrder(self.comboBox_ClipLayer, self.toolButton_AddMtl)
        DEMPropertiesWidget.setTabOrder(self.toolButton_AddMtl, self.toolButton_RemoveMtl)
        DEMPropertiesWidget.setTabOrder(self.toolButton_RemoveMtl, self.listWidget_Materials)
        DEMPropertiesWidget.setTabOrder(self.listWidget_Materials, self.toolButton_SelectLayer)
        DEMPropertiesWidget.setTabOrder(self.toolButton_SelectLayer, self.comboBox_TextureSize)
        DEMPropertiesWidget.setTabOrder(self.comboBox_TextureSize, self.radioButton_PNG)
        DEMPropertiesWidget.setTabOrder(self.radioButton_PNG, self.radioButton_JPEG)
        DEMPropertiesWidget.setTabOrder(self.radioButton_JPEG, self.lineEdit_ImageFile)
        DEMPropertiesWidget.setTabOrder(self.lineEdit_ImageFile, self.toolButton_ImageFile)
        DEMPropertiesWidget.setTabOrder(self.toolButton_ImageFile, self.colorButton_Color)
        DEMPropertiesWidget.setTabOrder(self.colorButton_Color, self.horizontalSlider_Opacity)
        DEMPropertiesWidget.setTabOrder(self.horizontalSlider_Opacity, self.spinBox_Opacity)
        DEMPropertiesWidget.setTabOrder(self.spinBox_Opacity, self.checkBox_TransparentBackground)
        DEMPropertiesWidget.setTabOrder(self.checkBox_TransparentBackground, self.checkBox_Shading)
        DEMPropertiesWidget.setTabOrder(self.checkBox_Shading, self.checkBox_Tiles)
        DEMPropertiesWidget.setTabOrder(self.checkBox_Tiles, self.spinBox_Size)
        DEMPropertiesWidget.setTabOrder(self.spinBox_Size, self.spinBox_Roughening)
        DEMPropertiesWidget.setTabOrder(self.spinBox_Roughening, self.checkBox_Sides)
        DEMPropertiesWidget.setTabOrder(self.checkBox_Sides, self.colorButton_Side)
        DEMPropertiesWidget.setTabOrder(self.colorButton_Side, self.lineEdit_Bottom)
        DEMPropertiesWidget.setTabOrder(self.lineEdit_Bottom, self.checkBox_Frame)
        DEMPropertiesWidget.setTabOrder(self.checkBox_Frame, self.colorButton_Edge)
        DEMPropertiesWidget.setTabOrder(self.colorButton_Edge, self.checkBox_Wireframe)
        DEMPropertiesWidget.setTabOrder(self.checkBox_Wireframe, self.colorButton_Wireframe)
        DEMPropertiesWidget.setTabOrder(self.colorButton_Wireframe, self.lineEdit_Name)
        DEMPropertiesWidget.setTabOrder(self.lineEdit_Name, self.checkBox_Visible)
        DEMPropertiesWidget.setTabOrder(self.checkBox_Visible, self.checkBox_Clickable)

    def retranslateUi(self, DEMPropertiesWidget):
        _translate = QtCore.QCoreApplication.translate
        DEMPropertiesWidget.setWindowTitle(_translate("DEMPropertiesWidget", "Form"))
        self.groupBox_Geometry.setTitle(_translate("DEMPropertiesWidget", "&Geometry"))
        self.label_Resampling.setText(_translate("DEMPropertiesWidget", "Resampling level"))
        self.label_ResamplingLevel.setText(_translate("DEMPropertiesWidget", "2"))
        self.label_Altitude.setText(_translate("DEMPropertiesWidget", "Altitude"))
        self.lineEdit_Altitude.setText(_translate("DEMPropertiesWidget", "0"))
        self.checkBox_Clip.setText(_translate("DEMPropertiesWidget", "Clip DEM with polygon layer"))
        self.groupBox_Material.setTitle(_translate("DEMPropertiesWidget", "&Material"))
        self.toolButton_RemoveMtl.setToolTip(_translate("DEMPropertiesWidget", "Remove selected material."))
        self.toolButton_RemoveMtl.setText(_translate("DEMPropertiesWidget", "-"))
        self.toolButton_AddMtl.setToolTip(_translate("DEMPropertiesWidget", "Add a material to this layer."))
        self.toolButton_AddMtl.setText(_translate("DEMPropertiesWidget", "+"))
        self.label_ImageFile.setText(_translate("DEMPropertiesWidget", "Image file"))
        self.label_17.setText(_translate("DEMPropertiesWidget", "Opacity (%)"))
        self.toolButton_ImageFile.setText(_translate("DEMPropertiesWidget", "Browse..."))
        self.toolButton_SelectLayer.setText(_translate("DEMPropertiesWidget", "Select..."))
        self.checkBox_Shading.setText(_translate("DEMPropertiesWidget", "Enable shading"))
        self.label_TextureSize.setText(_translate("DEMPropertiesWidget", "Image width (px)"))
        self.label_Color.setText(_translate("DEMPropertiesWidget", "Color"))
        self.label_Layers.setText(_translate("DEMPropertiesWidget", "Layers"))
        self.checkBox_TransparentBackground.setText(_translate("DEMPropertiesWidget", "Transparent background"))
        self.label_Format.setText(_translate("DEMPropertiesWidget", "Image format"))
        self.radioButton_PNG.setText(_translate("DEMPropertiesWidget", "PNG"))
        self.radioButton_JPEG.setText(_translate("DEMPropertiesWidget", "JPEG"))
        self.groupBox_Tiles.setTitle(_translate("DEMPropertiesWidget", "Tiles"))
        self.checkBox_Tiles.setText(_translate("DEMPropertiesWidget", "Tiles"))
        self.label_Roughness.setText(_translate("DEMPropertiesWidget", "Roughness"))
        self.spinBox_Roughening.setToolTip(_translate("DEMPropertiesWidget", "Grid roughness of tiles other than center tile"))
        self.spinBox_Size.setToolTip(_translate("DEMPropertiesWidget", "Number of tiles is square of this value. Should be an odd number."))
        self.label_2.setText(_translate("DEMPropertiesWidget", "Size"))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tab), _translate("DEMPropertiesWidget", "Main"))
        self.checkBox_Sides.setText(_translate("DEMPropertiesWidget", "Build sides"))
        self.checkBox_Wireframe.setText(_translate("DEMPropertiesWidget", "Add quad wireframe"))
        self.checkBox_Frame.setText(_translate("DEMPropertiesWidget", "Add edge lines"))
        self.label_Bottom.setText(_translate("DEMPropertiesWidget", "Altitude of bottom"))
        self.label.setText(_translate("DEMPropertiesWidget", "Name"))
        self.checkBox_Visible.setText(_translate("DEMPropertiesWidget", "Visible on load"))
        self.checkBox_Clickable.setText(_translate("DEMPropertiesWidget", "Clickable"))
        self.tabWidget.setTabText(self.tabWidget.indexOf(self.tabOthers), _translate("DEMPropertiesWidget", "Others"))
from qgis.gui import QgsColorButton
