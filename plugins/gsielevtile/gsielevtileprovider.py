# -*- coding: utf-8 -*-
# (C) 2015 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later
# 2015-05-22
"""
 GSIElevTileProvider
     DEM provider that downloads GSI Tiles (elevation) from the web server of
 Geospatial Information Authority of Japan, and provides elevation data to
 Qgis2threejs. Based on GSIElevTileProvider.py of Simple WCS Server project.
"""

import math
import numpy
import struct

from osgeo import gdal
from qgis.PyQt.QtCore import QSettings
from qgis.core import Qgis, QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsPointXY, QgsRectangle, QgsProject

from .downloader import Downloader
from Qgis2threejs.geometry import GridGeometry
from Qgis2threejs.utils import logMessage

TILE_SIZE = 256
TSIZE1 = 20037508.342789244
NODATA_VALUE = 0
NODATA_VALUE_BYTES = b"0"
ZMAX = 14


class GSIElevTileProvider:

    def __init__(self, dest_wkt):
        self.dest_wkt = dest_wkt

        # crs transformer, which aims to calculate bbox in EPSG:3857
        self.crs3857 = QgsCoordinateReferenceSystem("EPSG:3857")
        self.dest_crs = QgsCoordinateReferenceSystem()
        if not self.dest_crs.createFromWkt(dest_wkt):
            logMessage("Failed to create CRS from WKT: {0}".format(dest_wkt), error=True)
        self.transform = QgsCoordinateTransform(self.dest_crs, self.crs3857, QgsProject.instance())

        # approximate bbox of this data
        self.boundingbox = QgsRectangle(13667807, 2320477, 17230031, 5713298)

        self.downloader = Downloader()
        self.downloader.userAgent = "QGIS/{0} Qgis2threejs GSIElevTileProvider".format(Qgis.QGIS_VERSION_INT)  # will be overwritten in QgsNetworkAccessManager::createRequest() since 2.2
        self.downloader.DEFAULT_CACHE_EXPIRATION = QSettings().value("/qgis/defaultTileExpiry", 24, type=int)

        self.driver = gdal.GetDriverByName("MEM")
        self.last_dataset = None

    def name(self):
        return "GSI Elevation Tile"

    def read(self, width, height, extent):
        """read data into a byte array"""
        # calculate bounding box in EPSG:3857
        geometry = extent.geometry()
        geometry.transform(self.transform)
        merc_rect = geometry.boundingBox()

        # if the bounding box doesn't intersect with the bounding box of this data, return a list filled with nodata value
        if not self.boundingbox.intersects(merc_rect):
            return struct.pack("f", NODATA_VALUE) * width * height

        # get tiles
        over_smpl = 1
        segments_x = 1 if width == 1 else width - 1
        res = extent.width() / segments_x / over_smpl
        ds = self.getDataset(merc_rect.xMinimum(), merc_rect.yMinimum(), merc_rect.xMaximum(), merc_rect.yMaximum(), res)

        geotransform = extent.geotransform(width, height)
        return self._read(ds, width, height, geotransform)

    def readValues(self, width, height, extent):
        """read data into a list"""
        return struct.unpack("f" * width * height, self.read(width, height, extent))

    def readAsGridGeometry(self, width, height, extent):
        return GridGeometry(extent,
                            width - 1, height - 1,
                            self.readValues(width, height, extent))

    def readValue(self, x, y):
        """Get value at specified position using 1px * 1px memory raster. The value is calculated using a tile of max zoom level"""
        # coordinate transformation into EPSG:3857
        pt = self.transform.transform(QgsPointXY(x, y))

        # if the point is not within the bounding box of this data, return nodata value
        if not self.boundingbox.contains(pt):
            return NODATA_VALUE

        res = 0.1
        hres = res / 2
        ds = self.getDataset(pt.x() - hres, pt.y() - hres, pt.x() + hres, pt.y() + hres, res)

        geotransform = [x - hres, res, 0, y + hres, 0, -res]
        return struct.unpack("f", self._read(ds, 1, 1, geotransform))[0]

    def readValueOnTriangles(self, x, y, xmin, ymin, xres, yres):
        #TODO: implement
        return self.readValue(x, y)

    def _read(self, ds, width, height, geotransform):
        # create a memory dataset
        warped_ds = self.driver.Create("", width, height, 1, gdal.GDT_Float32)
        warped_ds.SetProjection(self.dest_wkt)
        warped_ds.SetGeoTransform(geotransform)

        # reproject image
        gdal.ReprojectImage(ds, warped_ds, None, None, gdal.GRA_Bilinear)

        # load values into an array
        band = warped_ds.GetRasterBand(1)
        return band.ReadRaster(0, 0, width, height, buf_type=gdal.GDT_Float32)

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

        if self.last_dataset and self.last_dataset[0] == [zoom, ulx, uly, lrx, lry]:    # if same as last tile set, return cached dataset
            return self.last_dataset[1]

        urltmpl = "https://cyberjapandata.gsi.go.jp/xyz/dem/{z}/{x}/{y}.txt"
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
                row = i // cols
                band.WriteRaster(col * TILE_SIZE, row * TILE_SIZE, TILE_SIZE, TILE_SIZE, tile)

        ds.FlushCache()

        self.last_dataset = [[zoom, ulx, uly, lrx, lry], ds]   # cache dataset
        return ds

    def fetchFiles(self, urltmpl, zoom, xmin, ymin, xmax, ymax):
        downloadTimeout = 60

        urls = []
        for y in range(ymin, ymax + 1):
            for x in range(xmin, xmax + 1):
                urls.append(urltmpl.replace("{x}", str(x)).replace("{y}", str(y)).replace("{z}", str(zoom)))
        files = self.downloader.fetchFiles(urls, downloadTimeout)

        for url in urls:
            data = files.get(url)
            if data:
                array = numpy.fromstring(data.replace(b"e", NODATA_VALUE_BYTES).replace(b"\n", b","), dtype=numpy.float32, sep=",")
            else:
                array = numpy.empty(TILE_SIZE * TILE_SIZE, dtype=numpy.float32)
                array.fill(NODATA_VALUE)

            yield array.tobytes()
