# -*- coding: utf-8 -*-
# (C) 2014 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later
# begin: 2014-01-16

from qgis.core import QgsCoordinateTransform, QgsFeatureRequest

from .feature_block_builder import FeatureBlockBuilder
from .layer import VectorLayer
from .object import ObjectType
from ..layerbuilderbase import LayerBuilderBase
from ..datamanager import MaterialManager, ModelManager
from ...const import LayerType
from ...geometry import VectorGeometry
from ....conf import DEF_SETS, FEATURES_PER_BLOCK, DEBUG_MODE
from ....utils import css_color, int_color, logger


class VectorLayerBuilder(LayerBuilderBase):

    type2str = {
        LayerType.POINT: "point",
        LayerType.LINESTRING: "line",
        LayerType.POLYGON: "polygon"
    }

    def __init__(self, settings, layer, imageManager, pathRoot=None, urlRoot=None, progress=None, log=None):
        LayerBuilderBase.__init__(self, settings, layer, imageManager, pathRoot, urlRoot, progress, log)

        self.materialManager = MaterialManager(imageManager, settings.materialType())
        self.modelManager = ModelManager(settings)

        self.clipExtent = None

        vl = VectorLayer(settings, layer, self.materialManager, self.modelManager)
        if vl.ot:
            self.log("Object type is {}.".format(vl.ot.name))
        else:
            logger.error("Object type not found")

        self.vlayer = vl

    def build(self, build_blocks=False, cancelSignal=None):
        if self.layer.mapLayer is None or self.vlayer.ot is None:
            return

        vlayer = self.vlayer
        objType = type(vlayer.ot)
        be = self.settings.baseExtent()
        p = self.layer.properties

        # feature request
        request = QgsFeatureRequest()
        if p.get("radioButton_IntersectingFeatures", False):
            request.setFilterRect(vlayer.transform.transformBoundingBox(be.boundingBox(),
                                                                        QgsCoordinateTransform.ReverseTransform))

            # geometry for clipping
            if p.get("checkBox_Clip") and objType != ObjectType.Polygon:
                self.clipExtent = be.clone().scale(0.9999)    # clip to slightly smaller extent than map canvas extent
        self.features = []
        data = {}

        # materials/models
        if objType == ObjectType.ModelFile:
            for feat in vlayer.features(request):
                feat.model = vlayer.ot.model(feat)
                self.features.append(feat)

            data["models"] = self.modelManager.build(self.pathRoot is not None,
                                                     base64=self.settings.jsonSerializable)

            self.log("This layer has reference to 3D model file(s). If there are relevant files, you need to copy them to data directory for this export.", warning=True)
        else:
            for feat in vlayer.features(request):
                feat.material = vlayer.ot.material(feat)
                self.features.append(feat)

            data["materials"] = self.materialManager.buildAll(self.pathRoot, self.urlRoot,
                                                              base64=self.settings.jsonSerializable)

        if build_blocks:
            self._startBuildBlocks(cancelSignal)

            nf = 0
            blocks = []
            for builder in self.subBuilders():
                if self.canceled:
                    break
                b = builder.build()
                nf += b["featureCount"]

                blocks.append(b)

            self._endBuildBlocks(cancelSignal)

            nb = len(blocks)
            if nb > 1:
                self.log("{} features were splitted into {} parts.".format(nf, nb))
            else:
                self.log("{} feature{}.".format(nf, "s" if nf > 1 else ""))

            data["blocks"] = blocks

        d = {
            "type": "layer",
            "id": self.layer.jsLayerId,
            "properties": self.layerProperties(),
            "data": data
        }

        if self.canceled:
            return None

        if DEBUG_MODE:
            d["PROPERTIES"] = p

        return d

    def layerProperties(self):
        p = LayerBuilderBase.layerProperties(self)
        p["type"] = self.type2str.get(self.layer.type)
        p["objType"] = self.vlayer.ot.name

        if self.vlayer.writeAttrs:
            p["propertyNames"] = self.vlayer.fieldNames

        if self.vlayer.hasLabel:
            label = {
                "relative": bool(self.properties.get("labelHeightWidget", {}).get("comboData", 0) == 1),
                "font": self.properties.get("comboBox_FontFamily", ""),
                "size": self.properties.get("slider_FontSize", 3) - 3,
                "color": css_color(self.properties.get("colorButton_Label", DEF_SETS.LABEL_COLOR))
            }

            if self.properties.get("checkBox_Outline"):
                label["olcolor"] = css_color(self.properties.get("colorButton_OtlColor", DEF_SETS.OTL_COLOR))

            if self.properties.get("groupBox_Background"):
                label["bgcolor"] = css_color(self.properties.get("colorButton_BgColor", DEF_SETS.BG_COLOR))

            if self.properties.get("groupBox_Conn"):
                label["cncolor"] = int_color(self.properties.get("colorButton_ConnColor", DEF_SETS.CONN_COLOR))

                if self.properties.get("checkBox_Underline"):
                    label["underline"] = True

            p["label"] = label

        # object-type-specific properties
        # p.update(self.vlayer.ot.layerProperties(self.settings, self))
        return p

    def subBuilders(self):
        if self.vlayer.ot is None:
            return

        objType = type(self.vlayer.ot)
        z_func = lambda x, y: 0
        grid = None

        p = self.vlayer.properties
        if p.get("radioButton_zValue"):
            useZM = VectorGeometry.UseZ
        elif p.get("radioButton_mValue"):
            useZM = VectorGeometry.UseM
        else:
            useZM = VectorGeometry.NotUseZM

        if self.vlayer.isHeightRelativeToDEM():
            demLayerId = p.get("comboBox_altitudeMode")
            demProvider = self.settings.demProviderByLayerId(demLayerId)

            if objType == ObjectType.Overlay:
                # get the grid segments of the DEM layer which polygons overlay
                dem_seg = self.settings.demGridSegments(demLayerId)

                # prepare a grid geometry
                grid = demProvider.readAsGridGeometry(dem_seg.width() + 1, dem_seg.height() + 1, self.settings.baseExtent())

            else:
                z_func = demProvider.readValue      # readValue(x, y)

        builder = FeatureBlockBuilder(self.settings, self.vlayer, self.layer.jsLayerId, self.pathRoot, self.urlRoot,
                                      useZM, z_func, grid)

        one_per_block = (objType == ObjectType.Overlay
                         and self.vlayer.isHeightRelativeToDEM()
                         and self.settings.isPreview)
        bIndex = startFIdx = 0
        feats = []
        for f in self.features or []:
            if self.clipExtent and self.layer.type != LayerType.POINT:
                if f.clipGeometry(self.clipExtent) is None:
                    continue

            # skip if geometry is empty or null
            if f.geom.isEmpty() or f.geom.isNull():
                if not self.clipExtent:
                    logger.info("empty/null geometry skipped")
                continue

            feats.append(f)

            if len(feats) == FEATURES_PER_BLOCK or one_per_block:
                b = builder.clone()
                b.setBlockIndex(bIndex)
                b.setFeatures(feats)
                b.startFIdx = startFIdx
                yield b

                bIndex += 1
                startFIdx += len(feats)
                feats = []

        if len(feats) or bIndex == 0:
            builder.setBlockIndex(bIndex)
            builder.setFeatures(feats)
            builder.startFIdx = startFIdx
            yield builder
