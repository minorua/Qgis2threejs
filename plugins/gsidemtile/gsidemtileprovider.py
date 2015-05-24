# -*- coding: utf-8 -*-
"""
/***************************************************************************
 GSIDEMTileProvider

   DEM provider that downloads GSI Tiles (elevation) from the web server of
 Geospatial Information Authority of Japan, and provides elevation data to
 Qgis2threejs. Based on GSIElevTileProvider.py of Simple WCS Server project.
                              -------------------
        begin                : 2015-05-22
        copyright            : (C) 2015 Minoru Akagi
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
import math
import numpy
import struct

from PyQt4.QtCore import QObject, QSettings
from qgis.core import QGis, QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsRectangle

try:
  from osgeo import gdal
except ImportError:
  import gdal

from downloader import Downloader
from Qgis2threejs.qgis2threejstools import logMessage

TILE_SIZE = 256
TSIZE1 = 20037508.342789244
NODATA_VALUE = 0
ZMAX = 14

class GSIDEMTileProvider:

  def __init__(self, dest_wkt=None):
    self.dest_wkt = dest_wkt

    # crs transformer, which aims to calculate bbox in EPSG:3857
    self.crs3857 = QgsCoordinateReferenceSystem(3857)
    self.dest_crs = QgsCoordinateReferenceSystem()
    if dest_wkt and not self.dest_crs.createFromWkt(dest_wkt):
      logMessage("Failed to create CRS from WKT: {0}".format(dest_wkt))
    self.transform = QgsCoordinateTransform(self.dest_crs, self.crs3857)

    # approximate bbox of this data
    self.boundingbox = QgsRectangle(13667807, 2320477, 17230031, 5713298)

    self.downloader = Downloader()
    self.downloader.userAgent = "QGIS/{0} Qgis2threejs GSIDEMTileProvider".format(QGis.QGIS_VERSION) # not written since QGIS 2.2
    self.downloader.DEFAULT_CACHE_EXPIRATION = QSettings().value("/qgis/defaultTileExpiry", 24, type=int)

    self.driver = gdal.GetDriverByName("MEM")

  def name(self):
    return "GSI DEM Tile"

  def read(self, width, height, geotransform, dest_wkt=None):
    xmin, ymax = geotransform[0], geotransform[3]
    xmax, ymin = xmin + geotransform[1] * width, ymax + geotransform[5] * height
    rect = QgsRectangle(xmin, ymin, xmax, ymax)

    # calculate bounding box in EPSG:3857 and check if the bounding box intersects the bounding box of this data
    if dest_wkt is None:
      dest_wkt = self.dest_wkt
      transform = self.transform
    else:
      dest_crs = QgsCoordinateReferenceSystem(dest_wkt)
      transform = QgsCoordinateTransform(dest_crs, self.crs3857)

    merc_rect = transform.transform(rect)
    if not merc_rect.intersects(self.boundingbox):
      return [NODATA_VALUE] * width * height

    # get tiles
    over_smpl = 1
    mapUnitsPerPixel = geotransform[1] / over_smpl
    ds = self.getDataset(merc_rect.xMinimum(), merc_rect.yMinimum(), merc_rect.xMaximum(), merc_rect.yMaximum(), mapUnitsPerPixel)

    # create a memory dataset
    warped_ds = self.driver.Create("", width, height, 1, gdal.GDT_Float32)
    warped_ds.SetProjection(dest_wkt)
    warped_ds.SetGeoTransform(geotransform)

    # reproject image
    gdal.ReprojectImage(ds, warped_ds, None, None, gdal.GRA_Bilinear)

    # load values into an array
    band = warped_ds.GetRasterBand(1)
    fs = "f" * width * height
    return struct.unpack(fs, band.ReadRaster(buf_type=gdal.GDT_Float32))

  def readValue(self, x, y, dest_wkt=None):
    """Get value at the position using 1px * 1px memory raster. The value is calculated using a tile of max zoom level"""
    res = 0.1
    geotransform = [x - res / 2, res, 0, y + res / 2, 0, -res]
    return self.read(1, 1, geotransform, dest_wkt)[0]

  def getDataset(self, xmin, ymin, xmax, ymax, mapUnitsPerPixel):
    # calculate zoom level
    mpp1 = TSIZE1 / TILE_SIZE
    zoom = int(math.ceil(math.log(mpp1 / mapUnitsPerPixel, 2) + 1))
    zoom = max(0, min(zoom, ZMAX))

    # calculate tile range (yOrigin is top)
    size = TSIZE1 / 2 ** (zoom - 1)
    matrixSize = 2 ** zoom
    ulx = max(0, int((xmin + TSIZE1) / size))
    uly = max(0, int((TSIZE1 - ymax) / size))
    lrx = min(int((xmax + TSIZE1) / size), matrixSize - 1)
    lry = min(int((TSIZE1 - ymin) / size), matrixSize - 1)

    cols = lrx - ulx + 1
    rows = lry - uly + 1

    # download count limit
    if cols * rows > 128:
      logMessage("Number of tiles to fetch is too large!")
      width = height = 1
      return self.driver.Create("", width, height, 1, gdal.GDT_Float32, [])

    urltmpl = "http://cyberjapandata.gsi.go.jp/xyz/dem/{z}/{x}/{y}.txt"
    #urltmpl = "http://localhost/xyz/dem/{z}/{x}/{y}.txt"
    tiles = self.fetchFiles(urltmpl, zoom, ulx, uly, lrx, lry)

    # create a memory dataset
    width = cols * TILE_SIZE
    height = rows * TILE_SIZE
    res = size / TILE_SIZE
    geotransform = [ulx * size - TSIZE1, res, 0, TSIZE1 - uly * size, 0, -res]

    #mem_driver = gdal.GetDriverByName("GTiff")
    #ds = mem_driver.Create("D:/fetched_tile.tif", width, height, 1, gdal.GDT_Float32, [])

    ds = self.driver.Create("", width, height, 1, gdal.GDT_Float32, [])
    ds.SetProjection(str(self.crs3857.toWkt()))
    ds.SetGeoTransform(geotransform)

    band = ds.GetRasterBand(1)
    for i, tile in enumerate(tiles):
      if tile:
        col = i % cols
        row = i / cols
        band.WriteRaster(col * TILE_SIZE, row * TILE_SIZE, TILE_SIZE, TILE_SIZE, tile)

    ds.FlushCache()
    return ds

  def fetchFiles(self, urltmpl, zoom, xmin, ymin, xmax, ymax):
    downloadTimeout = 60

    urls = []
    for y in range(ymin, ymax + 1):
      for x in range(xmin, xmax + 1):
        urls.append(urltmpl.replace("{x}", str(x)).replace("{y}", str(y)).replace("{z}", str(zoom)))
    files = self.downloader.fetchFiles(urls, downloadTimeout)

    for url in urls:
      data = files[url]
      if data:
        yield numpy.fromstring(data.replace("e", str(NODATA_VALUE)).replace("\n", ","), dtype=numpy.float32, sep=",").tostring()   # to byte array
      else:
        array = numpy.empty(TILE_SIZE * TILE_SIZE, dtype=numpy.float32)
        array.fill(NODATA_VALUE)
        yield array.tostring()
