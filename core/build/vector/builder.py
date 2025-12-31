# -*- coding: utf-8 -*-
# (C) 2014 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later
# begin: 2014-01-16

import math
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
    """Generates the export data structure from a vector layer.

    This builder coordinates per-layer material/model managers and
    block builders to produce vector feature blocks.
    """

    type2str = {
        LayerType.POINT: "point",
        LayerType.LINESTRING: "line",
        LayerType.POLYGON: "polygon"
    }

    def __init__(self, layer, settings, imageManager, pathRoot=None, urlRoot=None, progress=None, log=None):
        """See `LayerBuilderBase.__init__()` for argument details."""
        super().__init__(layer, settings, imageManager, pathRoot, urlRoot, progress, log)

        self.materialManager = MaterialManager(imageManager, settings.materialType())
        self.modelManager = ModelManager(settings)

        self.clipExtent = None

        self.vlayer = VectorLayer(layer, settings, self.materialManager, self.modelManager)
        if self.vlayer.ot:
            self.log("Object type is {}.".format(self.vlayer.ot.name))
        else:
            logger.error("Object type not found")

        self.features = []

        self._objTypeClass = type(self.vlayer.ot)
        self._onePerBlock = (self._objTypeClass == ObjectType.Overlay
                             and self.vlayer.isHeightRelativeToDEM()
                             and self.settings.isPreview)

    def build(self, build_blocks=False):
        """Generate the export data structure for this vector layer.

        Args:
            build_blocks (bool): If True, construct and return feature blocks under `data['body']['blocks']`.

        Returns:
            dict: Layer export data.
        """
        if self.layer.mapLayer is None or self.vlayer.ot is None:
            return

        vlayer = self.vlayer
        be = self.settings.baseExtent()
        p = self.layer.properties

        # feature request
        request = QgsFeatureRequest()
        if p.get("radioButton_IntersectingFeatures", False):
            request.setFilterRect(vlayer.transform.transformBoundingBox(be.boundingBox(),
                                                                        QgsCoordinateTransform.ReverseTransform))

            # geometry for clipping
            if p.get("checkBox_Clip") and self._objTypeClass != ObjectType.Polygon:
                self.clipExtent = be.clone().scale(0.9999)    # clip to slightly smaller extent than map canvas extent
        self.features = []
        data = {}

        # materials/models
        if self._objTypeClass == ObjectType.ModelFile:
            for feat in vlayer.features(request):
                feat.model = vlayer.ot.model(feat)
                self.features.append(feat)

            data["models"] = self.modelManager.build(self.pathRoot is not None,
                                                     base64=self.settings.requiresJsonSerializable)

            self.log("This layer has reference to 3D model file(s). If there are relevant files, you need to copy them to data directory for this export.", warning=True)
        else:
            for feat in vlayer.features(request):
                feat.material = vlayer.ot.material(feat)
                self.features.append(feat)

            data["materials"] = self.materialManager.buildAll(self.pathRoot, self.urlRoot,
                                                              base64=self.settings.requiresJsonSerializable)

        if build_blocks:
            data["blocks"] = self._buildBlocks()

        d = {
            "type": "layer",
            "id": self.layer.jsLayerId,
            "properties": self.layerProperties(),
            "body": data
        }

        if DEBUG_MODE:
            d["PROPERTIES"] = p

        return d

    def blockCount(self):
        if self._onePerBlock:
            return len(self.features)

        return math.ceil(len(self.features) / FEATURES_PER_BLOCK)

    def _buildBlocks(self):
        nf = 0
        blocks = []
        for builder in self.blockBuilders():
            b = builder.build()
            nf += b["featureCount"]

            blocks.append(b)

        nb = len(blocks)
        if nb > 1:
            self.log(f"{nf} features were splitted into {nb} parts.")
        else:
            self.log(f"{nf} feature(s).")

        return blocks

    def layerProperties(self):
        """Return layer properties such as layer type and object type.

        When attributes or labels are enabled, the corresponding configuration
        is also included.
        """
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

    def blockBuilders(self):
        """Yield `FeatureBlockBuilder` instances for the current features.

        This splits features into blocks of size `FEATURES_PER_BLOCK`.
        """
        if self.vlayer.ot is None:
            return

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

            if self._objTypeClass == ObjectType.Overlay:
                # get the grid segments of the DEM layer which polygons overlay
                dem_seg = self.settings.demGridSegments(demLayerId)

                # prepare a grid geometry
                grid = demProvider.readAsGridGeometry(dem_seg.width() + 1, dem_seg.height() + 1, self.settings.baseExtent())

            else:
                z_func = demProvider.readValue      # readValue(x, y)

        builder = FeatureBlockBuilder(self.settings, self.vlayer, self.layer.jsLayerId, self.pathRoot, self.urlRoot,
                                      useZM, z_func, grid)

        feats = []
        bIndex = startFIdx = 0
        blockCount = self.blockCount()

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

            if len(feats) == FEATURES_PER_BLOCK or self._onePerBlock:
                b = builder.clone()
                b.setBlockIndex(bIndex)
                b.setFeatures(feats)
                b.startFIdx = startFIdx
                yield b

                bIndex += 1
                startFIdx += len(feats)
                feats = []

                self.progress(bIndex, blockCount)

        if len(feats) or bIndex == 0:
            builder.setBlockIndex(bIndex)
            builder.setFeatures(feats)
            builder.startFIdx = startFIdx
            yield builder

            self.progress(bIndex + 1, blockCount)
