# -*- coding: utf-8 -*-
# (C) 2014 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later

import struct
from math import floor
from osgeo import gdal
from qgis.core import QgsPointXY, QgsRectangle

try:
    import numpy
except ImportError:
    numpy = None

from .geometry import GridGeometry
from .mapextent import MapExtent, GridRectangle
from ..utils import logger


class GDALDEMProvider:

    CanUseOriginalValues = True

    def __init__(self, filename, dest_wkt, source_wkt=None):
        self.filename = filename
        self.dest_wkt = dest_wkt
        self.source_wkt = source_wkt

        self.mem_driver = gdal.GetDriverByName("MEM")

        filename_utf8 = filename.encode("utf-8") if isinstance(filename, str) else filename
        self.ds = gdal.Open(filename_utf8, gdal.GA_ReadOnly)

        if self.ds is None:
            logger.error("Cannot open file: " + filename)
            self.ds = self.mem_driver.Create("", 1, 1, 1, gdal.GDT_Float32)

        self.width = self.ds.RasterXSize
        self.height = self.ds.RasterYSize
        self.nodata = self.ds.GetRasterBand(1).GetNoDataValue()

        self._opts = {
            "format": "MEM",
            "dstSRS": self.dest_wkt,
            "outputType": gdal.GDT_Float32,
            "resampleAlg": gdal.GRA_Bilinear
        }

        if source_wkt:
            self._opts["srcSRS"] = self.source_wkt

        if self.nodata is not None:
            self._opts["srcNodata"] = self.nodata
            self._opts["dstNodata"] = self.nodata

    def setResampleAlg(self, alg):
        self._opts["resampleAlg"] = alg

    def extent(self):
        gt = self.ds.GetGeoTransform()
        width = gt[1] * self.width
        height = -gt[5] * self.height
        return MapExtent(QgsPointXY(gt[0] + width / 2, gt[3] - height / 2), width, height)

    def geotransform(self):
        return self.ds.GetGeoTransform()

    def gridRectangle(self):
        return GridRectangle.fromGeotransform(self.ds.GetGeoTransform(), self.width, self.height)

    def _read(self, width, height, gt, asList=False):
        self._opts["width"] = width
        self._opts["height"] = height
        self._opts["outputBounds"] = [gt[0], gt[3] + gt[5] * height, gt[0] + gt[1] * width, gt[3]]

        warped_ds = gdal.Warp("", self.ds, **self._opts)
        band = warped_ds.GetRasterBand(1)

        if numpy is None:
            ba = band.ReadRaster(0, 0, width, height, buf_type=gdal.GDT_Float32)
            if asList:
                return struct.unpack("f" * width * height, ba)
            return ba

        arr = band.ReadAsArray()
        if self.nodata is not None:
            arr[arr == self.nodata] = numpy.nan

        if asList:
            return arr.flatten().tolist()
        return arr.tobytes()

    def read(self, width, height, extent):
        """read data into a byte array"""
        return self._read(width, height, extent.geotransform(width, height))

    def readValues(self, width, height, extent):
        """read data into a list"""
        return self._read(width, height, extent.geotransform(width, height), asList=True)

    def readAsGridGeometry(self, width, height, extent):
        return GridGeometry(extent,
                            width - 1, height - 1,
                            self.readValues(width, height, extent))

    def readValue(self, x, y):
        """get value at specified position using 1px * 1px memory raster"""
        res = 0.1
        geotransform = [x - res / 2, res, 0, y + res / 2, 0, -res]
        return self._read(1, 1, geotransform, asList=True)[0]

    def readValueOnTriangles(self, x, y, xmin, ymin, xres, yres):
        mx0 = floor((x - xmin) / xres)
        my0 = floor((y - ymin) / yres)
        px0 = xmin + xres * mx0
        py0 = ymin + yres * my0
        geotransform = [px0, xres, 0, py0 + yres, 0, -yres]
        z = self._read(2, 2, geotransform, asList=True)

        sdx = (x - px0) / xres
        sdy = (y - py0) / yres

        if sdx <= sdy:
            return z[0] + (z[1] - z[0]) * sdx + (z[2] - z[0]) * (1 - sdy)
        return z[3] + (z[2] - z[3]) * (1 - sdx) + (z[1] - z[3]) * sdy


class FlatDEMProvider:

    CanUseOriginalValues = False

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

    def setResampleAlg(self, _alg):
        pass
