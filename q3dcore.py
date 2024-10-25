# -*- coding: utf-8 -*-
# (C) 2014 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later
# begin: 2014-01-16

import os
import struct

from copy import deepcopy
from math import floor
from osgeo import gdal
from PyQt5.QtCore import QSize, QUrl

from qgis.core import Qgis, QgsMapLayer, QgsProject, QgsWkbTypes

from .geometry import GridGeometry
from .q3dconst import LayerType
from .utils import logMessage


class MapTo3D:

    def __init__(self, mapExtent, origin, zScale=1):
        # map
        self.mapExtent = mapExtent

        rect = mapExtent.unrotatedRect()
        self._xmin, self._ymin = (rect.xMinimum(), rect.yMinimum())
        self._width, self._height = (rect.width(), rect.height())

        # 3d
        self.origin = origin            # coordinates of 3D world origin in project CRS
        self.zScale = zScale

        self._originX, self._originY, self._originZ = (origin.x(), origin.y(), origin.z())

    def transform(self, x, y, z=0):
        return [x - self._originX,
                y - self._originY,
                (z - self._originZ) * self.zScale]

    def transformXY(self, x, y, z=0):
        return [x - self._originX,
                y - self._originY,
                z]

    def __repr__(self):
        origin = "({}, {}, {})".format(self.origin.x(), self.origin.y(), self.origin.z())
        return "MapTo3D(extent:{}, origin:{}, zScale:{})".format(str(self.mapExtent), origin, self.zScale)


class BuildOptions:

    def __init__(self):
        self.onlyMaterial = False
        self.allMaterials = False


class Layer:

    def __init__(self, layerId, name, layerType, properties=None, visible=True):
        self.layerId = layerId
        self.name = name
        self.type = layerType           # q3dconst.LayerType
        self.properties = properties or {}
        self.visible = visible

        # internal use
        self.jsLayerId = None
        self.mapLayer = None
        self.opt = BuildOptions()

    def material(self, mtlId):
        for mtl in self.properties.get("materials", []):
            if mtl.get("id") == mtlId:
                return mtl
        return {}

    def mtlIndex(self, mtlId):
        for i, mtl in enumerate(self.properties.get("materials", [])):
            if mtl.get("id") == mtlId:
                return i
        return None

    def clone(self):
        c = Layer(self.layerId, self.name, self.type, deepcopy(self.properties), self.visible)
        c.jsLayerId = self.jsLayerId
        c.mapLayer = self.mapLayer
        return c

    def copyTo(self, t):
        t.layerId = self.layerId
        t.name = self.name
        t.type = self.type
        t.properties = deepcopy(self.properties)
        t.visible = self.visible

        t.jsLayerId = self.jsLayerId
        t.mapLayer = self.mapLayer

    def toDict(self):
        return {"layerId": self.layerId,
                "name": self.name,
                "geomType": self.type,      # TODO: rename geomType to type (low priority)
                "properties": self.properties,
                "visible": self.visible}

    @classmethod
    def fromDict(self, obj):
        id = obj["layerId"]
        t = obj["geomType"]

        lyr = Layer(id, obj["name"], t, obj["properties"], obj["visible"])
        lyr.mapLayer = QgsProject.instance().mapLayer(id)

        return lyr

    @classmethod
    def fromQgsMapLayer(cls, mapLayer):
        geomType = layerTypeFromMapLayer(mapLayer)
        lyr = Layer(mapLayer.id(), mapLayer.name(), geomType, visible=False)
        lyr.mapLayer = mapLayer

        if geomType == LayerType.POINTCLOUD:
            lyr.properties["url"] = urlFromPCLayer(mapLayer)

        return lyr

    def __deepcopy__(self, memo):
        return self.clone()


class GDALDEMProvider:

    def __init__(self, filename, dest_wkt, source_wkt=None):
        self.filename = filename
        self.dest_wkt = dest_wkt
        self.source_wkt = source_wkt

        self.mem_driver = gdal.GetDriverByName("MEM")

        filename_utf8 = filename.encode("utf-8") if isinstance(filename, str) else filename
        self.ds = gdal.Open(filename_utf8, gdal.GA_ReadOnly)

        if self.ds is None:
            logMessage("Cannot open file: " + filename, error=True)
            self.ds = self.mem_driver.Create("", 1, 1, 1, gdal.GDT_Float32)

        self.width = self.ds.RasterXSize
        self.height = self.ds.RasterYSize

    def _read(self, width, height, geotransform):
        # create a memory dataset
        warped_ds = self.mem_driver.Create("", width, height, 1, gdal.GDT_Float32)
        warped_ds.SetProjection(self.dest_wkt)
        warped_ds.SetGeoTransform(geotransform)

        # reproject image
        gdal.ReprojectImage(self.ds, warped_ds, self.source_wkt, None, gdal.GRA_Bilinear)

        band = warped_ds.GetRasterBand(1)
        return band.ReadRaster(0, 0, width, height, buf_type=gdal.GDT_Float32)

    def read(self, width, height, extent):
        """read data into a byte array"""
        return self._read(width, height, extent.geotransform(width, height))

    def readValues(self, width, height, extent):
        """read data into a list"""
        return struct.unpack("f" * width * height, self.read(width, height, extent))

    def readAsGridGeometry(self, width, height, extent):
        return GridGeometry(extent,
                            width - 1, height - 1,
                            self.readValues(width, height, extent))

    def readValue(self, x, y):
        """get value at specified position using 1px * 1px memory raster"""
        res = 0.1
        geotransform = [x - res / 2, res, 0, y + res / 2, 0, -res]
        return struct.unpack("f", self._read(1, 1, geotransform))[0]

    def readValueOnTriangles(self, x, y, xmin, ymin, xres, yres):
        mx0 = floor((x - xmin) / xres)
        my0 = floor((y - ymin) / yres)
        px0 = xmin + xres * mx0
        py0 = ymin + yres * my0
        geotransform = [px0, xres, 0, py0 + yres, 0, -yres]
        z = struct.unpack("f" * 4, self._read(2, 2, geotransform))

        sdx = (x - px0) / xres
        sdy = (y - py0) / yres

        if sdx <= sdy:
            return z[0] + (z[1] - z[0]) * sdx + (z[2] - z[0]) * (1 - sdy)
        return z[3] + (z[2] - z[3]) * (1 - sdx) + (z[1] - z[3]) * sdy


class FlatDEMProvider:

    def __init__(self, value=0):
        self.value = value

    def name(self):
        return "Flat Plane"

    def read(self, width, height, extent):
        return struct.pack("{0}f".format(width * height), *([self.value] * width * height))

    def readValues(self, width, height, extent):
        return [self.value] * width * height

    def readAsGridGeometry(self, width, height, extent):
        return GridGeometry(extent,
                            width - 1, height - 1,
                            [self.value] * width * height)

    def readValue(self, x, y):
        return self.value


def calculateGridSegments(extent, sizeLevel, roughness=0):
    width, height = extent.width(), extent.height()
    size = 100 * sizeLevel
    s = (size * size / (width * height)) ** 0.5
    width = round(width * s)
    height = round(height * s)

    if roughness:
        if width % roughness != 0:
            width = int(width / roughness + 0.9999) * roughness
        if height % roughness != 0:
            height = int(height / roughness + 0.9999) * roughness

    return QSize(width, height)


def layerTypeFromMapLayer(mapLayer):
    """mapLayer: QgsMapLayer sub-class object"""
    layerType = mapLayer.type()
    if layerType == QgsMapLayer.VectorLayer:
        return {QgsWkbTypes.PointGeometry: LayerType.POINT,
                QgsWkbTypes.LineGeometry: LayerType.LINESTRING,
                QgsWkbTypes.PolygonGeometry: LayerType.POLYGON}.get(mapLayer.geometryType())

    elif layerType == QgsMapLayer.RasterLayer and mapLayer.providerType() == "gdal" and mapLayer.bandCount() == 1:
        return LayerType.DEM

    elif Qgis.QGIS_VERSION_INT >= 31800 and layerType == QgsMapLayer.PointCloudLayer:
        return LayerType.POINTCLOUD

    return None


def urlFromPCLayer(mapLayer):
    src = mapLayer.source()
    if src.startswith("http"):
        return ""       # not supported yet

    if mapLayer.providerType() == "ept":
        f = src
    else:       # assume provider type is pdal
        f = os.path.join(os.path.split(src)[0],
                         "ept_" + os.path.splitext(os.path.basename(src))[0],
                         "ept.json")

    return QUrl.fromLocalFile(f).toString()
