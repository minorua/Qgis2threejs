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
import json
import struct
from PyQt5.QtCore import QByteArray, QSize
from qgis.core import QgsGeometry, QgsPoint, QgsProject

from .conf import DEBUG_MODE, DEF_SETS
from .datamanager import MaterialManager
from .buildlayer import LayerBuilder
from .geometry import VectorGeometry, LineGeometry, TINGeometry, dissolvePolygonsWithinExtent
from .mapextent import MapExtent


class DEMLayerBuilder(LayerBuilder):

    def __init__(self, settings, layer, imageManager, pathRoot=None, urlRoot=None, progress=None, logMessage=None):
        LayerBuilder.__init__(self, settings, layer, imageManager, pathRoot, urlRoot, progress, logMessage)
        self.provider = settings.demProviderByLayerId(layer.layerId)

    def build(self, build_blocks=False, cancelSignal=None):
        if self.provider is None:
            return None

        d = {
            "type": "layer",
            "id": self.layer.jsLayerId,
            "properties": self.layerProperties()
        }

        # DEM block
        if build_blocks:
            self._startBuildBlocks(cancelSignal)

            data = []
            for block in self.blocks():
                if self.canceled:
                    break
                data.append(block.build())

            self._endBuildBlocks(cancelSignal)

            d["data"] = data
            self.logMessage("DEM block count: {}".format(len(data)))
        else:
            d["data"] = []

        if self.canceled:
            return None

        if DEBUG_MODE:
            d["PROPERTIES"] = self.properties

        return d

    def layerProperties(self):
        p = LayerBuilder.layerProperties(self)
        p["type"] = "dem"
        p["shading"] = self.properties.get("checkBox_Shading", True)
        return p

    def blocks(self):
        mapTo3d = self.settings.mapTo3d()
        be = self.settings.baseExtent()

        if self.properties.get("radioButton_MapCanvas") or self.properties.get("radioButton_LayerImage"):
            # calculate extent with the same aspect ratio as map image
            tex_size = DEMPropertyReader.textureSize(self.properties, be, self.settings)
            be = MapExtent(be.center(), be.width(), be.width() * tex_size.height() / tex_size.width(), be.rotation())

        center = be.center()
        rotation = be.rotation()
        base_grid_seg = self.settings.demGridSegments(self.layer.layerId)

        # clipping
        clip_geometry = None
        clip_option = self.properties.get("checkBox_Clip", False)
        if clip_option:
            clip_layerId = self.properties.get("comboBox_ClipLayer")
            clip_layer = QgsProject.instance().mapLayer(clip_layerId) if clip_layerId else None
            if clip_layer:
                clip_geometry = dissolvePolygonsWithinExtent(clip_layer, be, self.settings.crs)

        # surroundings
        surroundings = self.properties.get("checkBox_Surroundings", False)
        roughness = self.properties.get("spinBox_Roughening", 1) if surroundings else 1
        size = self.properties.get("spinBox_Size", 1) if surroundings else 1
        size2 = size * size

        blks = []
        for i in range(size2):
            sx = i % size - (size - 1) // 2
            sy = i // size - (size - 1) // 2
            dist2 = sx * sx + sy * sy
            blks.append([dist2, i, sx, sy])

        for dist2, blockIndex, sx, sy in sorted(blks):
            # self.progress(20 * i / size2 + 10)
            is_center = (sx == 0 and sy == 0)

            if is_center:
                extent = be
                grid_seg = base_grid_seg
            else:
                block_center = QgsPoint(center.x() + sx * be.width(), center.y() + sy * be.height())
                extent = MapExtent(block_center, be.width(), be.height()).rotate(rotation, center)
                grid_seg = QSize(max(1, base_grid_seg.width() // roughness),
                                 max(1, base_grid_seg.height() // roughness))

            block = DEMBlockBuilder(self.settings,
                                    self.imageManager,
                                    self.layer,
                                    blockIndex,
                                    self.provider,
                                    grid_seg,
                                    extent,
                                    mapTo3d.planeWidth,
                                    mapTo3d.planeWidth * be.height() / be.width(),
                                    offsetX=mapTo3d.planeWidth * sx,
                                    offsetY=mapTo3d.planeHeight * sy,
                                    edgeRoughness=roughness if is_center else 1,
                                    clip_geometry=clip_geometry if is_center else None,
                                    pathRoot=self.pathRoot,
                                    urlRoot=self.urlRoot)
            yield block


class DEMBlockBuilder:

    def __init__(self, settings, imageManager, layer, blockIndex, provider, grid_seg, extent, planeWidth, planeHeight, offsetX=0, offsetY=0, edgeRoughness=1, clip_geometry=None, pathRoot=None, urlRoot=None):
        self.settings = settings
        self.materialManager = MaterialManager(imageManager, settings.materialType())

        self.layer = layer
        self.properties = layer.properties

        self.blockIndex = blockIndex
        self.provider = provider
        self.grid_seg = grid_seg
        self.extent = extent
        self.planeWidth = planeWidth
        self.planeHeight = planeHeight
        self.offsetX = offsetX
        self.offsetY = offsetY
        self.edgeRoughness = edgeRoughness
        self.clip_geometry = clip_geometry
        self.pathRoot = pathRoot
        self.urlRoot = urlRoot

    def build(self):
        mapTo3d = self.settings.mapTo3d()

        # block data
        b = {"type": "block",
             "layer": self.layer.jsLayerId,
             "block": self.blockIndex,
             "width": self.planeWidth,
             "height": self.planeHeight,
             "translate": [self.offsetX, self.offsetY, mapTo3d.verticalShift * mapTo3d.multiplierZ],
             "zShift": mapTo3d.verticalShift,
             "zScale": mapTo3d.multiplierZ,
             "material": self.material()}

        if self.clip_geometry:
            geom = self.clipped(self.clip_geometry)

            if self.settings.localMode or self.settings.isPreview:
                b["geom"] = geom
            else:
                tail = "{0}.json".format(self.blockIndex)
                with open(self.pathRoot + tail, "w", encoding="utf-8") as f:
                    json.dump(geom, f, ensure_ascii=False, indent=2 if DEBUG_MODE else None)

                b["geom"] = {"url": self.urlRoot + tail}
        else:
            grid_width, grid_height = (self.grid_seg.width() + 1, self.grid_seg.height() + 1)

            if self.edgeRoughness == 1:
                ba = self.provider.read(grid_width, grid_height, self.extent)
            else:
                grid_values = list(self.provider.readValues(grid_width, grid_height, self.extent))
                self.processEdges(grid_values, self.edgeRoughness)
                ba = struct.pack("{0}f".format(grid_width * grid_height), *grid_values)

            g = {"width": grid_width,
                 "height": grid_height}

            if self.settings.localMode:
                g["array"] = struct.unpack("f" * grid_width * grid_height, ba)
            elif self.settings.isPreview:
                g["binary"] = QByteArray(ba)
            else:
                # write grid values to an binary file
                tail = "{0}.bin".format(self.blockIndex)
                with open(self.pathRoot + tail, "wb") as f:
                    f.write(ba)
                g["url"] = self.urlRoot + tail

            b["grid"] = g

        opacity = DEMPropertyReader.opacity(self.properties)

        # sides and bottom
        if self.properties.get("checkBox_Sides"):
            mi = self.materialManager.getMeshMaterialIndex(self.properties.get("toolButton_SideColor", DEF_SETS.SIDE_COLOR), opacity)
            b["sides"] = {"mtl": self.materialManager.build(mi)}

        # edges
        if self.properties.get("checkBox_Frame") and not self.properties.get("checkBox_Clip"):
            mi = self.materialManager.getBasicLineIndex(self.properties.get("toolButton_EdgeColor", DEF_SETS.EDGE_COLOR), opacity)
            b["edges"] = {"mtl": self.materialManager.build(mi)}

        # wireframe
        if self.properties.get("checkBox_Wireframe"):
            mi = self.materialManager.getBasicLineIndex(self.properties.get("toolButton_WireframeColor", DEF_SETS.WIREFRAME_COLOR), opacity)
            b["wireframe"] = {"mtl": self.materialManager.build(mi)}

        return b

    def material(self):
        # properties
        tex_size = DEMPropertyReader.textureSize(self.properties, self.extent, self.settings)
        opacity = DEMPropertyReader.opacity(self.properties)
        transp_background = self.properties.get("checkBox_TransparentBackground", False)

        # display type
        if self.properties.get("radioButton_MapCanvas"):
            mi = self.materialManager.getMapImageIndex(tex_size.width(), tex_size.height(), self.extent,
                                                       opacity, transp_background)

        elif self.properties.get("radioButton_LayerImage"):
            layerids = self.properties.get("layerImageIds", [])
            mi = self.materialManager.getLayerImageIndex(layerids, tex_size.width(), tex_size.height(), self.extent,
                                                         opacity, transp_background)

        elif self.properties.get("radioButton_ImageFile"):
            filepath = self.properties.get("lineEdit_ImageFile", "")
            mi = self.materialManager.getImageFileIndex(filepath, opacity, transp_background, True)

        else:  # .get("radioButton_SolidColor")
            mi = self.materialManager.getMeshMaterialIndex(self.properties.get("colorButton_Color", ""), opacity, True)

        # elif self.properties.get("radioButton_Wireframe"):
        #  mi = self.materialManager.getWireframeIndex(self.properties["lineEdit_Color"], opacity)

        # build material
        filepath = None if self.pathRoot is None else "{0}{1}.png".format(self.pathRoot, self.blockIndex)
        url = None if self.urlRoot is None else "{0}{1}.png".format(self.urlRoot, self.blockIndex)
        return self.materialManager.build(mi, filepath, url, self.settings.base64)

    def clipped(self, clip_geometry):
        transform_func = self.settings.mapTo3d().transformRotatedXY

        # create a grid geometry and split polygons with the grid
        grid = self.provider.readAsGridGeometry(self.grid_seg.width() + 1, self.grid_seg.height() + 1, self.extent)

        if self.extent.rotation():
            clip_geometry = QgsGeometry(clip_geometry)
            clip_geometry.rotate(self.extent.rotation(), self.extent.center())

        bnds = grid.segmentizeBoundaries(clip_geometry)
        polys = grid.splitPolygon(clip_geometry)

        tin = TINGeometry.fromQgsGeometry(polys, None, transform_func, centroid=False, use_earcut=True)
        d = tin.toDict(flat=True)

        polygons = []
        for bnd in bnds:
            geom = LineGeometry.fromQgsGeometry(bnd, None, transform_func, useZM=VectorGeometry.UseZ)
            polygons.append(geom.toList())
        d["polygons"] = polygons
        return d

    def processEdges(self, grid_values, roughness):
        grid_width = self.grid_seg.width() + 1
        grid_height = self.grid_seg.height() + 1
        rg_grid_width = self.grid_seg.width() // roughness + 1
        rg_grid_height = self.grid_seg.height() // roughness + 1
        ii = range(roughness)[1:]

        for x0 in range(rg_grid_width - 1):
            # top edge
            ix0 = x0 * roughness
            z0 = grid_values[ix0]
            z1 = grid_values[ix0 + roughness]
            for i in ii:
                grid_values[ix0 + i] = (z1 - z0) * i / roughness + z0

            # bottom edge
            iy0 = grid_width * (grid_height - 1)
            z0 = grid_values[iy0 + ix0]
            z1 = grid_values[iy0 + ix0 + roughness]
            for i in ii:
                grid_values[iy0 + ix0 + i] = (z1 - z0) * i / roughness + z0

        rw = roughness * grid_width
        for y0 in range(rg_grid_height - 1):
            # left edge
            iy0 = y0 * grid_width
            z0 = grid_values[iy0]
            z1 = grid_values[iy0 + rw]
            for i in ii:
                grid_values[iy0 + i * grid_width] = (z1 - z0) * i / roughness + z0

            # right edge
            iy0 += grid_width - 1
            z0 = grid_values[iy0]
            z1 = grid_values[iy0 + rw]
            for i in ii:
                grid_values[iy0 + i * grid_width] = (z1 - z0) * i / roughness + z0

    def getValue(self, x, y):

        def _getValue(gx, gy):
            return self.grid_values[gx + self.grid_width * gy]

        if 0 <= x and x <= self.grid_width - 1 and 0 <= y and y <= self.grid_height - 1:
            ix, iy = int(x), int(y)
            sx, sy = x - ix, y - iy

            z11 = _getValue(ix, iy)
            z21 = 0 if x == self.grid_width - 1 else _getValue(ix + 1, iy)
            z12 = 0 if y == self.grid_height - 1 else _getValue(ix, iy + 1)
            z22 = 0 if x == self.grid_width - 1 or y == self.grid_height - 1 else _getValue(ix + 1, iy + 1)

            return (1 - sx) * ((1 - sy) * z11 + sy * z12) + sx * ((1 - sy) * z21 + sy * z22)    # bilinear interpolation

        return 0    # as safe null value

    def gridPointToPoint(self, x, y):
        x = self.rect.xMinimum() + self.rect.width() / (self.grid_width - 1) * x
        y = self.rect.yMaximum() - self.rect.height() / (self.grid_height - 1) * y
        return x, y

    def pointToGridPoint(self, x, y):
        x = (x - self.rect.xMinimum()) / self.rect.width() * (self.grid_width - 1)
        y = (self.rect.yMaximum() - y) / self.rect.height() * (self.grid_height - 1)
        return x, y


class DEMBlocks:

    def __init__(self):
        self.blocks = []

    def appendBlock(self, block):
        self.blocks.append(block)

    def appendBlocks(self, blocks):
        self.blocks += blocks

    def processEdges(self):
        """for now, this function is designed for simple resampling mode with surroundings"""
        count = len(self.blocks)
        if count < 9:
            return

        ci = (count - 1) // 2
        size = int(count ** 0.5)

        center = self.blocks[0]
        blocks = self.blocks[1:ci + 1] + [center] + self.blocks[ci + 1:]

        grid_width, grid_height, grid_values = center.grid_width, center.grid_height, center.grid_values
        for istop, neighbor in enumerate([blocks[ci - size], blocks[ci + size]]):
            if grid_width == neighbor.grid_width:
                continue

            y = grid_height - 1 if not istop else 0
            for x in range(grid_width):
                gx, gy = center.gridPointToPoint(x, y)
                gx, gy = neighbor.pointToGridPoint(gx, gy)
                grid_values[x + grid_width * y] = neighbor.getValue(gx, gy)

        for isright, neighbor in enumerate([blocks[ci - 1], blocks[ci + 1]]):
            if grid_height == neighbor.grid_height:
                continue

            x = grid_width - 1 if isright else 0
            for y in range(grid_height):
                gx, gy = center.gridPointToPoint(x, y)
                gx, gy = neighbor.pointToGridPoint(gx, gy)
                grid_values[x + grid_width * y] = neighbor.getValue(gx, gy)

    def stats(self):
        if len(self.blocks) == 0:
            return {"max": 0, "min": 0}

        block = self.blocks[0]
        stats = {"max": block.orig_stats["max"], "min": block.orig_stats["min"]}
        for block in self.blocks[1:]:
            stats["max"] = max(block.orig_stats["max"], stats["max"])
            stats["min"] = min(block.orig_stats["min"], stats["min"])
        return stats


class DEMPropertyReader:

    @staticmethod
    def opacity(properties):
        return properties.get("spinBox_Opacity", 100) / 100

    @staticmethod
    def textureSize(properties, extent, settings):
        try:
            w = int(properties.get("comboBox_TextureSize"))
        except ValueError:
            w = settings.mapSettings.outputSize().width()  # map canvas width

        return QSize(w, round(w * extent.height() / extent.width()))


def dummyProgress(percentage=None, msg=None):
    pass
