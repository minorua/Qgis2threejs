# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Qgis2threejs
                                 A QGIS plugin
 export terrain data, map canvas image and vector data to web browser
                              -------------------
        begin                : 2014-01-16
        copyright            : (C) 2014 Minoru Akagi
        email                : akaginch@gmail.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
import struct

from PyQt4.QtCore import QSize
from qgis.core import QGis, QgsMapLayer, QgsRectangle

try:
  from osgeo import gdal
except ImportError:
  import gdal

from .gdal2threejs import Raster
from .geometry import Point
from .rotatedrect import RotatedRect
from .quadtree import DEMQuadTree


class ObjectTreeItem:

  ITEM_WORLD = "WORLD"
  ITEM_CONTROLS = "CTRL"
  ITEM_DEM = "DEM"
  ITEM_OPTDEM = "OPTDEM"
  ITEM_POINT = "POINT"
  ITEM_LINE = "LINE"
  ITEM_POLYGON = "POLYGON"
  topItemIds = [ITEM_WORLD, ITEM_CONTROLS, ITEM_DEM, ITEM_OPTDEM, ITEM_POINT, ITEM_LINE, ITEM_POLYGON]
  topItemNames = ["World", "Controls", "DEM", "Additional DEM", "Point", "Line", "Polygon"]
  geomType2id = {QGis.Point: ITEM_POINT, QGis.Line: ITEM_LINE, QGis.Polygon: ITEM_POLYGON}

  @classmethod
  def topItemIndex(cls, id):
    return cls.topItemIds.index(id)

  @classmethod
  def idByGeomType(cls, geomType):
    return cls.geomType2id.get(geomType)

  @classmethod
  def geomTypeById(cls, id):
    for geomType in cls.geomType2id:
      if cls.geomType2id[geomType] == id:
        return geomType
    return None

  @classmethod
  def parentIdByLayer(cls, layer):
    layerType = layer.type()
    if layerType == QgsMapLayer.VectorLayer:
      return cls.idByGeomType(layer.geometryType())

    if layerType == QgsMapLayer.RasterLayer and layer.providerType() == "gdal" and layer.bandCount() == 1:
      return cls.ITEM_OPTDEM

    return None


class MapTo3D:

  def __init__(self, mapSettings, planeWidth=100, verticalExaggeration=1, verticalShift=0):
    # map canvas
    self.rotation = mapSettings.rotation() if QGis.QGIS_VERSION_INT >= 20700 else 0
    self.mapExtent = RotatedRect.fromMapSettings(mapSettings)

    # 3d
    canvas_size = mapSettings.outputSize()
    self.planeWidth = planeWidth
    self.planeHeight = planeWidth * canvas_size.height() / float(canvas_size.width())

    self.verticalExaggeration = verticalExaggeration
    self.verticalShift = verticalShift

    self.multiplier = planeWidth / self.mapExtent.width()
    self.multiplierZ = self.multiplier * verticalExaggeration

  def transform(self, x, y, z=0):
    n = self.mapExtent.normalizePoint(x, y)
    return Point((n.x() - 0.5) * self.planeWidth,
                 (n.y() - 0.5) * self.planeHeight,
                 (z + self.verticalShift) * self.multiplierZ)

  def transformPoint(self, pt):
    return self.transform(pt.x, pt.y, pt.z)


class GDALDEMProvider(Raster):

  def __init__(self, filename, dest_wkt, source_wkt=None):
    Raster.__init__(self, filename)
    self.driver = gdal.GetDriverByName("MEM")
    self.dest_wkt = dest_wkt
    self.source_wkt = source_wkt
    if source_wkt:
      self.ds.SetProjection(str(source_wkt))

  def _read(self, width, height, geotransform):
    # create a memory dataset
    warped_ds = self.driver.Create("", width, height, 1, gdal.GDT_Float32)
    warped_ds.SetProjection(self.dest_wkt)
    warped_ds.SetGeoTransform(geotransform)

    # reproject image
    gdal.ReprojectImage(self.ds, warped_ds, None, None, gdal.GRA_Bilinear)

    # load values into an array
    band = warped_ds.GetRasterBand(1)
    fs = "f" * width * height
    return struct.unpack(fs, band.ReadRaster(0, 0, width, height, buf_type=gdal.GDT_Float32))

  def read(self, width, height, extent):
    return self._read(width, height, extent.geotransform(width, height))

  def readValue(self, x, y):
    """get value at the position using 1px * 1px memory raster"""
    res = 0.1
    geotransform = [x - res / 2, res, 0, y + res / 2, 0, -res]
    return self._read(1, 1, geotransform)[0]


class FlatDEMProvider:

  def __init__(self, value=0):
    self.value = value

  def name(self):
    return "Flat Plane"

  def read(self, width, height, extent):
    return [self.value] * width * height

  def readValue(self, x, y):
    return self.value


def calculateDEMSize(canvasSize, sizeLevel, roughening=0):
  width, height = canvasSize.width(), canvasSize.height()
  size = 100 * sizeLevel
  s = (size * size / float(width * height)) ** 0.5
  if s < 1:
    width = int(width * s)
    height = int(height * s)

  if roughening:
    if width % roughening != 0:
      width = int(float(width) / roughening + 0.9) * roughening
    if height % roughening != 0:
      height = int(float(height) / roughening + 0.9) * roughening

  return QSize(width + 1, height + 1)


def createQuadTree(extent, p):
  """
  args:
    p -- demProperties
  """
  try:
    cx, cy, w, h = list(map(float, [p["lineEdit_centerX"], p["lineEdit_centerY"], p["lineEdit_rectWidth"], p["lineEdit_rectHeight"]]))
  except ValueError:
    return None

  # normalize
  c = extent.normalizePoint(cx, cy)
  hw = 0.5 * w / extent.width()
  hh = 0.5 * h / extent.height()

  quadtree = DEMQuadTree()
  if not quadtree.buildTreeByRect(QgsRectangle(c.x() - hw, c.y() - hh, c.x() + hw, c.y() + hh), p["spinBox_Height"]):
    return None

  return quadtree
