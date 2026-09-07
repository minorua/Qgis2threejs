# -*- coding: utf-8 -*-
# (C) 2014 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later

import struct
from osgeo import gdal
from qgis.core import QgsCoordinateTransform, QgsPointXY, QgsProject, QgsRasterProjector, QgsRectangle, Qgis

try:
    import numpy
except ImportError:
    numpy = None

from ...geometry import GridGeometry
from ...mapextent import GridShape, MapExtent, RegularGrid
from ....utils.logging import logger

NODATA_VALUE = -3.4e38


class DEMProviderBase:

    CanUseOriginalValues = True

    def geotransform(self):
        pass

    def xSize(self):
        pass

    def ySize(self):
        pass

    def _read(self, width, height, geotransform, asList=False, asNumpyArray=False):
        pass

    def setResampleAlg(self, alg):
        pass

    def extent(self):
        gt = self.geotransform()
        width = gt[1] * self.xSize()
        height = -gt[5] * self.ySize()
        return MapExtent(QgsPointXY(gt[0] + width / 2, gt[3] - height / 2), width, height)

    def grid(self):
        gt = self.geotransform()
        xSize, ySize = self.xSize(), self.ySize()

        xmin = gt[0] + 0.5 * gt[1]
        ymax = gt[3] + 0.5 * gt[5]
        xmax = xmin + gt[1] * (xSize - 1)
        ymin = ymax + gt[5] * (ySize - 1)

        return RegularGrid(QgsRectangle(xmin, ymin, xmax, ymax), GridShape(xSize, ySize))

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
        extent = MapExtent(QgsPointXY(x, y), res, res)
        return self.readValues(1, 1, extent)[0]


class GDALDEMProvider(DEMProviderBase):

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

    def geotransform(self):
        return self.ds.GetGeoTransform()

    def xSize(self):
        return self.ds.RasterXSize

    def ySize(self):
        return self.ds.RasterYSize

    def _read(self, width, height, geotransform, asList=False, asNumpyArray=False):
        if geotransform[2]:
            warped_ds = self._readReprojectImage(width, height, geotransform)
        else:
            warped_ds = self._readWarp(width, height, geotransform)

        band = warped_ds.GetRasterBand(1)

        if asNumpyArray:
            return band.ReadAsArray()

        ba = band.ReadRaster(0, 0, width, height, buf_type=gdal.GDT_Float32)

        if asList:
            return struct.unpack("f" * width * height, ba)

        return ba

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

    def setResampleAlg(self, alg):
        self._opts["resampleAlg"] = alg


# Experimental
class QGISRasterDEMProvider(DEMProviderBase):

    def __init__(self, layer, dest_crs=None):
        dataProvider = layer.dataProvider().clone()
        self.provider = dataProvider
        self.nodata = dataProvider.sourceNoDataValue(1) if dataProvider.sourceHasNoDataValue(1) else None

        src_crs = layer.crs()
        self.dest_crs = dest_crs if dest_crs else src_crs

        self._projector = None
        if src_crs != self.dest_crs:
            self._projector = QgsRasterProjector()
            self._projector.setInput(self.provider)
            self._projector.setCrs(src_crs, self.dest_crs, QgsProject.instance().transformContext())

    def extent(self):
        return MapExtent.fromRect(self.provider.extent())

    def geotransform(self):
        rect = self.provider.extent()
        return [rect.xMinimum(), rect.width() / self.provider.xSize(), 0,
                rect.yMaximum(), 0, -rect.height() / self.provider.ySize()]

    def xSize(self):
        return self.provider.xSize()

    def ySize(self):
        return self.provider.ySize()

    def _read(self, width, height, geotransform, asList=False, asNumpyArray=False):
        gt = geotransform
        rect = QgsRectangle(gt[0], gt[3] + gt[5] * height,
                            gt[0] + gt[1] * width, gt[3])

        interface = self._projector or self.provider
        block = interface.block(1, rect, width, height)

        if asNumpyArray:
            return block.as_numpy(use_masking=False).astype(numpy.float32)

        if block.dataType() != Qgis.DataType.Float32:
            block.convert(Qgis.DataType.Float32)

        ba = block.data()

        if asList:
            return struct.unpack("f" * width * height, ba)

        return ba

    def setResampleAlg(self, alg):
        if self.provider.providerCapabilities() & Qgis.RasterProviderCapability.ProviderHintCanPerformProviderResampling:
            method = Qgis.RasterResamplingMethod.Bilinear if alg == gdal.GRA_Bilinear else Qgis.RasterResamplingMethod.Nearest
            self.provider.setZoomedInResamplingMethod(method)
            self.provider.setZoomedOutResamplingMethod(method)
            self.provider.enableProviderResampling(True)
        else:
            logger.warning("Raster provider doesn't support provider resampling.")


class FlatDEMProvider:

    CanUseOriginalValues = False

    def __init__(self, value=0):
        self.value = value
        self.nodata = None

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
