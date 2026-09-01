# -*- coding: utf-8 -*-
# (C) 2014 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later

import struct
from osgeo import gdal
from qgis.core import QgsPointXY, QgsRectangle

try:
    import numpy
except ImportError:
    numpy = None

from ...geometry import GridGeometry
from ...mapextent import GridShape, MapExtent, RegularGrid
from ....utils.logging import logger

NODATA_VALUE = -3.4e38


class GDALDEMProvider:

    CanUseOriginalValues = True

    def __init__(self, filename, dest_wkt, source_wkt=None):
        self.filename = filename
        self.dest_wkt = dest_wkt
        self.source_wkt = source_wkt

        self.nodata = NODATA_VALUE

        self.mem_driver = gdal.GetDriverByName("MEM")

        filename_utf8 = filename.encode("utf-8") if isinstance(filename, str) else filename
        self.ds = gdal.Open(filename_utf8, gdal.GA_ReadOnly)

        if self.ds is None:
            logger.error("Cannot open file: " + filename)
            self.ds = self.mem_driver.Create("", 1, 1, 1, gdal.GDT_Float32)

        self.width = self.ds.RasterXSize
        self.height = self.ds.RasterYSize

        self._opts = {
            "format": "MEM",
            "dstSRS": self.dest_wkt,
            "outputType": gdal.GDT_Float32,
            "resampleAlg": gdal.GRA_Bilinear,
            "dstNodata": NODATA_VALUE
        }

        if source_wkt:
            self._opts["srcSRS"] = self.source_wkt

    def setResampleAlg(self, alg):
        self._opts["resampleAlg"] = alg

    def extent(self):
        gt = self.ds.GetGeoTransform()
        width = gt[1] * self.width
        height = -gt[5] * self.height
        return MapExtent(QgsPointXY(gt[0] + width / 2, gt[3] - height / 2), width, height)

    def geotransform(self):
        return self.ds.GetGeoTransform()

    def grid(self):
        gt = self.ds.GetGeoTransform()
        xmin = gt[0] + 0.5 * gt[1]
        ymax = gt[3] + 0.5 * gt[5]
        xmax = xmin + gt[1] * (self.width - 1)
        ymin = ymax + gt[5] * (self.height - 1)

        return RegularGrid(
            QgsRectangle(xmin, ymin, xmax, ymax),
            GridShape(self.width, self.height)
        )

    def _read(self, width, height, geotransform, asList=False, asNumpyArray=False):
        if geotransform[2]:
            warped_ds = self._readReprojectImage(width, height, geotransform)
        else:
            warped_ds = self._readWarp(width, height, geotransform)

        band = warped_ds.GetRasterBand(1)

        if numpy is None:
            ba = band.ReadRaster(0, 0, width, height, buf_type=gdal.GDT_Float32)
            if asList:
                return struct.unpack("f" * width * height, ba)
            return ba

        arr = band.ReadAsArray()
        if asNumpyArray:
            return arr

        if asList:
            return arr.flatten().tolist()

        return arr.tobytes()

    def _readWarp(self, width, height, gt):
        self._opts["width"] = width
        self._opts["height"] = height
        self._opts["outputBounds"] = [gt[0], gt[3] + gt[5] * height, gt[0] + gt[1] * width, gt[3]]

        return gdal.Warp("", self.ds, **self._opts)

    def _readReprojectImage(self, width, height, geotransform):
        warped_ds = self.mem_driver.Create("", width, height, 1, gdal.GDT_Float32)
        warped_ds.SetProjection(self.dest_wkt)
        warped_ds.SetGeoTransform(geotransform)
        warped_ds.GetRasterBand(1).SetNoDataValue(self.nodata)

        options = ["INIT_DEST=NO_DATA"]

        gdal.ReprojectImage(self.ds, warped_ds, self.source_wkt, None, self._opts["resampleAlg"], options=options)

        return warped_ds

    def read(self, width, height, extent):
        """read data into a byte array"""
        return self._read(width, height, extent.geotransform(width, height))

    def readAsArray(self, width, height, extent):
        return self._read(width, height, extent.geotransform(width, height), asNumpyArray=True)

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


class FlatDEMProvider:

    CanUseOriginalValues = False

    def __init__(self, value=0):
        self.value = value
        self.nodata = None

    def name(self):
        return "Flat Plane"

    def read(self, width, height, extent):
        return struct.pack(f"{width * height}f", *([self.value] * width * height))

    def readAsArray(self, width, height, extent):
        return numpy.full((height, width), self.value, dtype=numpy.float32)

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
