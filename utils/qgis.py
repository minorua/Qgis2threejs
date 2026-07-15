# -*- coding: utf-8 -*-
# (C) 2013 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later

from qgis.PyQt.QtWidgets import QDialog, QDialogButtonBox, QVBoxLayout

from qgis.core import Qgis, QgsProject
from qgis.gui import QgsCompoundColorWidget

from ..core.const import LayerType


def getLayersInProject():
    """Return a list of layers available in the current QGIS project.

    Returns:
        list: A list of QgsMapLayer objects.
    """
    layers = []
    for tl in QgsProject.instance().layerTreeRoot().findLayers():
        if tl.layer():
            layers.append(tl.layer())
    return layers


def getDEMLayersInProject():
    """Return single-band GDAL raster layers (e.g. DEMs) from the project.

    Returns:
        list: Raster layers that match the criteria.
    """
    layers = []
    for layer in getLayersInProject():
        if layer.type() == Qgis.LayerType.Raster:
            if layer.providerType() == "gdal" and layer.bandCount() == 1:
                layers.append(layer)
    return layers


def getLayersByLayerIds(layerIds):
    """Return QgsMapLayer objects for the given layer IDs.

    Args:
        layerIds: A list of layer IDs.

    Returns:
        list: QgsMapLayer objects.
    """
    layers = []
    for id in layerIds:
        layer = QgsProject.instance().mapLayer(id)
        if layer:
            layers.append(layer)
    return layers


def shortTextFromSelectedLayerIds(layerIds):
    """Create a short textual description from selected layer IDs.

    Examples: "1 layer selected", "2 layers selected".

    Args:
        layerIds: List of layer IDs.

    Returns:
        str: Short English description.
    """
    count = len(layerIds)
    return "{0} layer{1} selected".format(count, "s" if count > 1 else "")

    #
    if count == 0:
        return "0 layer"

    layer = QgsProject.instance().mapLayer(layerIds[0])
    if layer is None:
        return "Layer not found"

    text = '"{0}"'.format(layer.name())
    if count > 1:
        text += " and {0} layer".format(count - 1)
    if count > 2:
        text += "s"
    return text


def layerTypeFromMapLayer(mapLayer):
    """mapLayer: QgsMapLayer sub-class object"""
    layerType = mapLayer.type()
    if layerType == Qgis.LayerType.Vector:
        return {
            Qgis.GeometryType.Point: LayerType.POINT,
            Qgis.GeometryType.Line: LayerType.LINESTRING,
            Qgis.GeometryType.Polygon: LayerType.POLYGON}.get(mapLayer.geometryType())

    elif layerType == Qgis.LayerType.Raster and mapLayer.providerType() == "gdal" and mapLayer.bandCount() == 1:
        return LayerType.DEM

    # elif layerType == Qgis.LayerType.PointCloud:
    #     return LayerType.POINTCLOUD

    return None


def settingsFilePath():
    """Return the export settings file path associated with the current project.

    Returns empty string if the project has not been saved yet.
    """
    proj_path = QgsProject.instance().fileName()
    return proj_path + ".qto3settings" if proj_path else ""


def selectColor(parent=None):
    dlg = QDialog(parent)
    dlg.setWindowTitle("Select a color")
    dlg.setLayout(QVBoxLayout())

    widget = QgsCompoundColorWidget()
    widget.setAllowOpacity(False)
    dlg.layout().addWidget(widget)

    buttonBox = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
    buttonBox.accepted.connect(dlg.accept)
    buttonBox.rejected.connect(dlg.reject)
    dlg.layout().addWidget(buttonBox)

    if dlg.exec():
        return widget.color()
