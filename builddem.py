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
from .q3dconst import DEMMtlType
from .tools import logMessage, parseFloat


class DEMLayerBuilder(LayerBuilder):

    def __init__(self, settings, layer, imageManager, pathRoot=None, urlRoot=None, progress=None, log=None):
        LayerBuilder.__init__(self, settings, layer, imageManager, pathRoot, urlRoot, progress, log)

        self.provider = settings.demProviderByLayerId(layer.layerId)
        self.mtlBuilder = DEMMaterialBuilder(settings, layer, imageManager, pathRoot, urlRoot)
        self.grdBuilder = DEMGridBuilder(self.settings, self.mtlBuilder.materialManager, self.layer, self.provider, self.pathRoot, self.urlRoot)

    def build(self, build_blocks=False, cancelSignal=None):
        if self.provider is None:
            return None

        if self.layer.opt.onlyMaterial:
            return None     # do not send "layer" data

        d = {
            "type": "layer",
            "id": self.layer.jsLayerId,
            "properties": self.layerProperties()
        }

        # DEM block
        if build_blocks:
            self._startBuildBlocks(cancelSignal)

            data = []
            for builder in self.subBuilders():
                if self.canceled:
                    break
                data.append(builder.build())

            self._endBuildBlocks(cancelSignal)

            d["data"] = data
            self.log("DEM block count: {}".format(len(data)))
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
        p["clipped"] = self.properties.get("checkBox_Clip", False)
        p["mtlNames"] = [mtl.get("name", "") for mtl in self.properties.get("materials", [])]
        return p

    def subBuilders(self):
        be = self.settings.baseExtent()

        materials = self.properties.get("materials", [])
        mtlCount = len(materials)

        if self.mtlBuilder.currentMtlType() in (DEMMtlType.LAYER, DEMMtlType.MAPCANVAS):
            # calculate extent with the same aspect ratio as current material texture image
            tex_size = DEMPropertyReader.textureSize(self.mtlBuilder.currentMtlProperties(), be, self.settings)
            be = MapExtent(be.center(), be.width(), be.width() * tex_size.height() / tex_size.width(), be.rotation())

        planeWidth, planeHeight = (be.width(), be.height())

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

        # tiles (old name: surrounding blocks)
        tiles = self.properties.get("checkBox_Tiles", False)
        roughness = self.properties.get("spinBox_Roughening", 1) if tiles else 1
        size = self.properties.get("spinBox_Size", 1) if tiles else 1
        size2 = size * size

        centerBlk = DEMGridBuilder(self.settings, self.mtlBuilder.materialManager, self.layer, self.provider, self.pathRoot, self.urlRoot)
        blks = []
        for i in range(size2):
            sx = i % size - (size - 1) // 2
            sy = i // size - (size - 1) // 2
            dist2 = sx * sx + sy * sy
            blks.append([dist2, -sy, sx, sy, i])

        for dist2, _nsy, sx, sy, blockIndex in sorted(blks):
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

            # set up material builder for first/current material
            if self.layer.opt.allMaterials and len(materials):
                self.mtlBuilder.setup(blockIndex, extent, materials[0].get("id"), useNow=False)
            else:
                self.mtlBuilder.setup(blockIndex, extent, useNow=True)
            yield self.mtlBuilder

            # set up grid builder
            if not self.layer.opt.onlyMaterial:
                if is_center:
                    grdBuilder = centerBlk
                else:
                    grdBuilder = self.grdBuilder
                    if sx * sx <= 1 and sy * sy <= 1:
                        grdBuilder.neighbors = [(sx, sy, centerBlk, 1)]

                grdBuilder.setup(blockIndex, grid_seg, extent, planeWidth, planeHeight,
                                 offsetX=planeWidth * sx,
                                 offsetY=planeHeight * sy,
                                 roughness=1 if is_center else roughness,
                                 edgeRoughness=roughness if is_center else 1,
                                 clip_geometry=clip_geometry if is_center else None)
                yield grdBuilder

            # set up material builder for remaininig materials
            if self.layer.opt.allMaterials:
                for i in range(1, mtlCount):
                    self.mtlBuilder.setup(blockIndex, extent, materials[i].get("id"), useNow=False)
                    yield self.mtlBuilder


class DEMGridBuilder:

    def __init__(self, settings, mtlManager, layer, provider, pathRoot=None, urlRoot=None):

        self.settings = settings
        self.mtlManager = mtlManager

        self.layer = layer
        self.properties = layer.properties

        self.provider = provider

        self.pathRoot = pathRoot
        self.urlRoot = urlRoot

        self.neighbors = []

    def setup(self, blockIndex, grid_seg, extent, planeWidth, planeHeight, offsetX=0, offsetY=0, roughness=1, edgeRoughness=1, clip_geometry=None):
        self.blockIndex = blockIndex
        self.grid_seg = grid_seg
        self.extent = extent
        self.planeWidth = planeWidth
        self.planeHeight = planeHeight
        self.offsetX = offsetX
        self.offsetY = offsetY
        self.roughness = roughness
        self.edgeRoughness = edgeRoughness
        self.clip_geometry = clip_geometry

        self.edges = None

    def build(self):
        mapTo3d = self.settings.mapTo3d()

        b = {"type": "block",
             "layer": self.layer.jsLayerId,
             "block": self.blockIndex,
             "width": self.planeWidth,
             "height": self.planeHeight,
             "translate": [self.offsetX, self.offsetY, 0],
             "zShift": mapTo3d.zShift,
             "zScale": mapTo3d.zScale
             }

        # geometry
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

            if self.edgeRoughness == 1 and len(self.neighbors) == 0:
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
            mi = self.mtlManager.getMeshMaterialIndex(self.properties.get("toolButton_SideColor", DEF_SETS.SIDE_COLOR), opacity)
            b["sides"] = {"mtl": self.mtlManager.build(mi),
                          "bottom": parseFloat(self.properties.get("lineEdit_Bottom"), DEF_SETS.Z_BOTTOM)}

        # edges
        if self.properties.get("checkBox_Frame") and not self.properties.get("checkBox_Clip"):
            mi = self.mtlManager.getLineIndex(self.properties.get("toolButton_EdgeColor", DEF_SETS.EDGE_COLOR), opacity)
            b["edges"] = {"mtl": self.mtlManager.build(mi)}

        # wireframe
        if self.properties.get("checkBox_Wireframe"):
            mi = self.mtlManager.getLineIndex(self.properties.get("toolButton_WireframeColor", DEF_SETS.WIREFRAME_COLOR), opacity)
            b["wireframe"] = {"mtl": self.mtlManager.build(mi)}

        return b

    def clipped(self, clip_geometry):
        transform_func = self.settings.mapTo3d().transformXY

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

        if self.offsetX == 0 and self.offsetY == 0:
            self.processEdgesCenter(grid_values, roughness)
            return

        grid_width, grid_height = (self.grid_seg.width() + 1,
                                   self.grid_seg.height() + 1)

        for sx, sy, neighbor, roughness in self.neighbors:
            if self.roughness <= roughness:
                continue
            if neighbor.edges is None:
                logMessage("Neighbor block {} holds no edge values.".format(neighbor.blockIndex))
                continue

            if (sx, sy) == (0, -1):
                # top edge
                for x in range(grid_width):
                    grid_values[x] = neighbor.edges[0][x]

            elif (sx, sy) == (0, 1):
                # bottom edge
                offset = grid_width * (grid_height - 1)
                for x in range(grid_width):
                    grid_values[offset + x] = neighbor.edges[3][x]

            elif (sx, sy) == (-1, 0):
                # right edge
                offset = grid_width - 1
                for y in range(grid_height):
                    grid_values[offset + grid_width * y] = neighbor.edges[1][y]

            elif (sx, sy) == (1, 0):
                # left edge
                for y in range(grid_height):
                    grid_values[grid_width * y] = neighbor.edges[2][y]

            elif (sx, sy) == (-1, -1):
                # top-right corner
                grid_values[grid_width - 1] = neighbor.edges[0][0]

            elif (sx, sy) == (1, -1):
                # top-left corner
                grid_values[0] = neighbor.edges[0][grid_width - 1]

            elif (sx, sy) == (-1, 1):
                # bottom-right corner
                grid_values[grid_width * grid_height - 1] = neighbor.edges[3][0]

            elif (sx, sy) == (1, 1):
                # bottom-left corner
                grid_values[grid_width * (grid_height - 1)] = neighbor.edges[3][grid_width - 1]

            else:
                logMessage("Edge processing: invalid sx and sy ({}, {})".format(sx, sy))

    def processEdgesCenter(self, grid_values, roughness):

        grid_width, grid_height = (self.grid_seg.width() + 1,
                                   self.grid_seg.height() + 1)
        rg_grid_width, rg_grid_height = (self.grid_seg.width() // roughness + 1,
                                         self.grid_seg.height() // roughness + 1)
        ii = range(roughness)[1:]

        iy0 = grid_width * (grid_height - 1)
        e_top = [grid_values[0]]
        e_bottom = [grid_values[iy0]]

        for x0 in range(rg_grid_width - 1):
            # top edge
            ix0 = x0 * roughness
            z0 = grid_values[ix0]
            z1 = grid_values[ix0 + roughness]
            s = (z1 - z0) / roughness
            for i in ii:
                grid_values[ix0 + i] = z0 + s * i

            e_top.append(z1)

            # bottom edge
            z0 = grid_values[iy0 + ix0]
            z1 = grid_values[iy0 + ix0 + roughness]
            s = (z1 - z0) / roughness
            for i in ii:
                grid_values[iy0 + ix0 + i] = z0 + s * i

            e_bottom.append(z1)

        e_left = [grid_values[0]]
        e_right = [grid_values[grid_width - 1]]

        rw = roughness * grid_width
        for y0 in range(rg_grid_height - 1):
            # left edge
            iy0 = y0 * rw
            z0 = grid_values[iy0]
            z1 = grid_values[iy0 + rw]
            s = (z1 - z0) / roughness
            for i in ii:
                grid_values[iy0 + i * grid_width] = z0 + s * i

            e_left.append(z1)

            # right edge
            iy0 += grid_width - 1
            z0 = grid_values[iy0]
            z1 = grid_values[iy0 + rw]
            s = (z1 - z0) / roughness
            for i in ii:
                grid_values[iy0 + i * grid_width] = z0 + s * i

            e_right.append(z1)

        self.edges = [e_bottom, e_left, e_right, e_top]

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


class DEMMaterialBuilder:

    def __init__(self, settings, layer, imageManager, pathRoot, urlRoot):
        self.settings = settings
        self.materialManager = MaterialManager(imageManager, settings.materialType())

        self.layer = layer

        self.pathRoot = pathRoot
        self.urlRoot = urlRoot

        self.mtlId = None

    def setup(self, blockIndex, extent, mtlId=None, asBlock=True, useNow=True):
        self.blockIndex = blockIndex
        self.extent = extent
        self.mtlId = mtlId
        self.asBlock = asBlock
        self.useNow = useNow

    def build(self):
        # properties
        mtlId = self.mtlId or self.layer.properties.get("mtlId")
        m = self.layer.material(mtlId)
        if m:
            mtlIndex = self.layer.mtlIndex(mtlId)

        else:   # fallback to materials[0]
            m = self.layer.properties.get("materials", [])
            m = m[0] if len(m) else {}
            mtlIndex = 0

        p = m.get("properties", {})
        tex_size = DEMPropertyReader.textureSize(p, self.extent, self.settings)
        opacity = DEMPropertyReader.opacity(p)
        transp_background = p.get("checkBox_TransparentBackground", False)

        # material type
        mtype = m.get("type", DEMMtlType.MAPCANVAS)
        if mtype == DEMMtlType.MAPCANVAS:
            mi = self.materialManager.getMapImageIndex(tex_size.width(), tex_size.height(), self.extent,
                                                       opacity, transp_background)

        elif mtype == DEMMtlType.LAYER:
            layerids = m.get("layerIds", [])
            mi = self.materialManager.getLayerImageIndex(layerids, tex_size.width(), tex_size.height(), self.extent,
                                                         opacity, transp_background)

        elif mtype == DEMMtlType.FILE:
            filepath = p.get("lineEdit_ImageFile", "")
            mi = self.materialManager.getImageFileIndex(filepath, opacity, transp_background, True)

        else:  # q3dconst.MTL_COLOR
            mi = self.materialManager.getMeshMaterialIndex(p.get("colorButton_Color", ""), opacity, True)

        # build material
        filepath = None if self.pathRoot is None else "{}{}{}.png".format(self.pathRoot, self.blockIndex, "_{}".format(mtlIndex) if mtlIndex else "")
        url = None if self.urlRoot is None else "{}{}{}.png".format(self.urlRoot, self.blockIndex, "_{}".format(mtlIndex) if mtlIndex else "")

        d = self.materialManager.build(mi, filepath, url, self.settings.base64)
        d["mtlIndex"] = mtlIndex
        d["useNow"] = self.useNow
        if self.asBlock:
            return {
                "type": "block",
                "layer": self.layer.jsLayerId,
                "block": self.blockIndex,
                "materials": [d]
            }
        return d

    def currentMtl(self):
        mtlId = self.mtlId or self.layer.properties.get("mtlId")
        return self.layer.material(mtlId)

    def currentMtlType(self):
        return self.currentMtl().get("type", DEMMtlType.MAPCANVAS)

    def currentMtlProperties(self):
        return self.currentMtl().get("properties", {})


class DEMPropertyReader:

    @staticmethod
    def opacity(properties):
        return properties.get("spinBox_Opacity", 100) / 100

    @staticmethod
    def textureSize(properties, extent, settings):
        try:
            w = int(properties.get("comboBox_TextureSize", DEF_SETS.TEXTURE_SIZE))
        except ValueError:
            w = DEF_SETS.TEXTURE_SIZE

        return QSize(w, round(w * extent.height() / extent.width()))


def dummyProgress(percentage=None, msg=None):
    pass
