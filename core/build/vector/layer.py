# -*- coding: utf-8 -*-
# (C) 2014 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later

import random
from qgis.PyQt.QtGui import QColor
from qgis.core import (QgsCoordinateTransform, QgsExpression, QgsFeatureRequest, QgsGeometry, QgsProject, QgsRenderContext)

from .feature import Feature
from .object import ObjectType
from ...const import LayerType, PropertyID as PID
from ....conf import DEF_SETS
from ....gui.propwidget import PropertyWidget, ColorWidgetFunc, OpacityWidgetFunc, ColorTextureWidgetFunc
from ....utils import hex_color, logger, parseFloat


class VectorLayer:
    """Represents a vector layer associated with a selected 3D object type.

    This class wraps a QGIS vector layer together with exporter settings and the material/model managers,
    and provides methods for iterating over its features.
    """

    # (Layer, ExportSettings, MaterialManager, ModelManager)
    def __init__(self, layer, settings, materialManager, modelManager):
        """
        Args:
            layer: Layer object.
            settings: ExportSettings object.
            materialManager: Manager used to create/get material indices for features.
            modelManager: Manager used to identify external 3D models.
        """
        self.type = layer.type
        self.mapLayer = layer.mapLayer
        self.name = layer.name
        self.properties = layer.properties

        self.settings = settings
        self.renderContext = QgsRenderContext.fromMapSettings(settings.mapSettings)

        self.expressionContext = self.mapLayer.createExpressionContext()

        otc = ObjectType.typeByName(self.properties.get("comboBox_ObjectType"), layer.type)
        if otc == ObjectType.ModelFile:
            self.ot = otc(settings, modelManager)
        elif otc:
            self.ot = otc(settings, materialManager)
        else:
            self.ot = None
            logger.error("Shape type not found: {} ({})".format(self.properties.get("comboBox_ObjectType"), self.name))

        self.materialManager = materialManager
        self.modelManager = modelManager
        self.colorNames = []        # for random color

        self.transform = QgsCoordinateTransform(self.mapLayer.crs(), settings.crs, QgsProject.instance())
        self.onlyIntersecting = self.properties.get("radioButton_IntersectingFeatures", False)

        # attributes
        self.writeAttrs = self.properties.get("checkBox_ExportAttrs", False)
        self.hasLabel = self.properties.get("checkBox_Label", False)

        self.fieldIndices = []
        self.fieldNames = []

        if self.writeAttrs:
            for index, field in enumerate(self.mapLayer.fields()):
                if field.editorWidgetSetup().type() != "Hidden":
                    self.fieldIndices.append(index)
                    self.fieldNames.append(field.displayName())

        # expressions
        self._exprs = {}

        self.pids = [PID.ALT] + self.ot.pids
        if self.hasLabel:
            self.pids += [PID.LBLH, PID.LBLTXT]

        # animation
        self.anim_exprs = None
        if self.type == LayerType.LINESTRING and otc in [ObjectType.Line, ObjectType.ThickLine]:
            groups = list(self.settings.groupsWithExpressions(layer.layerId))
            if groups:
                kf = groups[0].get("keyframes", [{}])[0]
                self.anim_exprs = {
                    PID.DLY: QgsExpression(str(kf.get("delay", 0))),
                    PID.DUR: QgsExpression(str(kf.get("duration", DEF_SETS.ANM_DURATION)))
                }

    def features(self, request=None):
        """Yield Feature objects for export.

        Iterates over features from the underlying `mapLayer`, performs CRS
        transformation, optional intersection filtering with the base extent,
        evaluates property values, and yields `Feature` instances that the
        exporter consumes.

        Args:
            request: Optional `QgsFeatureRequest` to filter which features to iterate.

        Yields:
            `Feature` instances containing geometry, evaluated properties and attributes.
        """

        mapTo3d = self.settings.mapTo3d()
        be = self.settings.baseExtent()
        beGeom = be.geometry()
        rotation = be.rotation()
        fields = self.mapLayer.fields()
        attrs = None

        # initialize symbol rendering, and then get features (geometry, attributes, color, etc.)
        self.renderer = self.mapLayer.renderer().clone()
        self.renderer.startRender(self.renderContext, self.mapLayer.fields())

        for f in self.mapLayer.getFeatures(request or QgsFeatureRequest()):
            # geometry
            geom = f.geometry()
            if geom is None:
                logger.info("[{}] Null geometry skipped.".format(self.name))
                continue

            geom = QgsGeometry(geom)

            # coordinate transformation - layer crs to project crs
            if geom.transform(self.transform) != 0:
                logger.warning("[{}] Failed to transform a geometry.".format(self.name))
                continue

            if rotation and self.onlyIntersecting:
                # if map is rotated, check whether geometry intersects with the base extent
                if not beGeom.intersects(geom):
                    continue

            # set feature to expression context
            self.expressionContext.setFeature(f)

            # properties
            props = self.evaluateProperties(f, self.pids)

            if self.anim_exprs:
                for pid, expr in self.anim_exprs.items():
                    props[pid] = expr.evaluate(self.expressionContext)

            # attributes
            if self.writeAttrs:
                attrs = [fields[i].displayString(f.attribute(i)) for i in self.fieldIndices]

            # label
            if self.hasLabel:
                props[PID.LBLH] *= mapTo3d.zScale

            yield Feature(self, geom, props, attrs)

        self.renderer.stopRender(self.renderContext)

    def evaluateProperties(self, feat, pids):
        """Evaluate a set of property IDs for a feature.

        This collects values for the requested property IDs (`pids`) by looking up
        the corresponding property configuration in `self.properties`.

        Args:
            feat: `QgsFeature` being evaluated.
            pids: List of `PropertyID` constants to evaluate.

        Returns:
            dict mapping property ID to evaluated value.
        """

        d = {}

        for pid in pids:
            name = PID.PID_NAME_DICT[pid]
            p = self.properties.get(name)
            if p is None:
                continue

            val = None
            if isinstance(p, str):
                val = self.evaluateExpression(p, feat)

            elif isinstance(p, dict):
                val = self.evaluatePropertyWidget(name, feat)

            if val is not None:
                d[pid] = val

        return d

    def evaluateExpression(self, expr_str, feat):
        """Evaluate a QGIS expression string in the context of feature `feat`.

        Args:
            expr_str: Expression string to evaluate.
            feat: `QgsFeature` used as the expression context.

        Returns:
            The evaluated result.
        """

        if expr_str not in self._exprs:
            self._exprs[expr_str] = QgsExpression(expr_str)

        self.expressionContext.setFeature(feat)
        return self._exprs[expr_str].evaluate(self.expressionContext)

    def evaluatePropertyWidget(self, name, feat):
        """Evaluate property widget values for a feature.

        Args:
            name: Property name.
            feat: `QgsFeature` used for expression evaluation or symbol lookup.

        Returns:
            Evaluated value appropriate for the widget type.
        """

        wv = self.properties.get(name)
        if not wv:
            return None

        t = wv["type"]
        if t == PropertyWidget.COLOR:
            return self.readFillColor(wv, feat)

        if t == PropertyWidget.OPACITY:
            return self.readOpacity(wv, feat)

        if t in (PropertyWidget.EXPRESSION, PropertyWidget.LABEL_HEIGHT):
            expr = wv["editText"] or "0"
            val = self.evaluateExpression(expr, feat)

            if val is None:
                logger.warning("[{}] Failed to evaluate expression: {}".format(self.name, expr))

            elif isinstance(val, str):
                val = parseFloat(val)
                if val is None:
                    logger.warning("[{}] Cannot parse '{}' as a float value.".format(self.name, expr))

            return val or 0

        if t == PropertyWidget.OPTIONAL_COLOR:
            return self.readBorderColor(wv, feat)

        if t == PropertyWidget.CHECKBOX:
            return wv["checkBox"]

        if t == PropertyWidget.COMBOBOX:
            return wv["comboData"]

        if t == PropertyWidget.FILEPATH:
            expr = wv["editText"]
            val = self.evaluateExpression(expr, feat)
            if val is None:
                if expr:
                    logger.warning("[{}] Failed to evaluate expression: {}".format(self.name, expr))
                else:
                    logger.warning("[{}] There is an empty file path.".format(self.name))

            return val or ""

        if t == PropertyWidget.COLOR_TEXTURE:
            comboData = wv.get("comboData")
            if comboData == ColorTextureWidgetFunc.MAP_CANVAS:
                return comboData

            if comboData == ColorTextureWidgetFunc.LAYER:
                return wv.get("layerIds", [])

            return self.readFillColor(wv, feat)

        logger.error("Widget type {} not found.".format(t))
        return None

    def readFillColor(self, vals, feat):
        """Read a fill color value from color widget values.

        Returns a hex color string prefixed with `0x`, or `None` when there is
        no color selection.
        """
        return self._readColor(vals, feat)

    def readBorderColor(self, vals, feat):
        """Read a border color value from optional color widget values.

        Returns a hex color string prefixed with `0x`, or `None` when there is
        no color selection."""
        return self._readColor(vals, feat, isBorder=True)

    def _readColor(self, wv, feat, isBorder=False):
        """Internal helper to read color from widget values.

        Args:
            wv: Widget values dict
            feat: `QgsFeature` used when reading feature-derived color
            isBorder: If True, read stroke/border color from renderer

        Returns:
            Color string in `0xRRGGBB` format, `0` when wrong value specified or `None` when not available.
        """

        mode = wv["comboData"]
        if mode is None:
            return None

        if mode == ColorWidgetFunc.EXPRESSION:
            val = self.evaluateExpression(wv["editText"], feat)
            try:
                if isinstance(val, str):
                    a = val.split(",")
                    if len(a) >= 3:
                        a = [max(0, min(int(c), 255)) for c in a[:3]]
                        return "0x{:02x}{:02x}{:02x}".format(a[0], a[1], a[2])
                    return val.replace("#", "0x")

                raise
            except:
                logger.warning("[{}] Wrong color value: {}".format(self.name, val))
                return "0"

        if mode == ColorWidgetFunc.RANDOM or feat is None:
            self.colorNames = self.colorNames or QColor.colorNames()
            color = random.choice(self.colorNames)
            self.colorNames.remove(color)
            return hex_color(QColor(color).name(), prefix="0x")

        # feature color from renderer
        symbols = self.renderer.symbolsForFeature(feat, self.renderContext)
        if not symbols:
            logger.warning("[{}] Symbol for feature not found. Please use a simple renderer.".format(self.name))
            return "0"

        symbol = symbols[0]
        if isBorder:
            sl = symbol.symbolLayer(0)
            if sl:
                return sl.strokeColor().name().replace("#", "0x")

        return symbol.color().name().replace("#", "0x")

    def readOpacity(self, wv, feat):
        """Read opacity value from opacity widget values.

        Args:
            wv: Widget values dict
            feat: `QgsFeature` used when reading feature-derived opacity

        Returns:
            Float value between 0.0 and 1.0
        """

        if wv["comboData"] == OpacityWidgetFunc.EXPRESSION:
            try:
                val = self.evaluateExpression(wv["editText"], feat)
                return min(max(0, val), 100) / 100
            except:
                logger.warning("[{}] Wrong opacity value: {}".format(self.name, val))
                return 1

        symbols = self.renderer.symbolsForFeature(feat, self.renderContext)
        if not symbols:
            logger.warning("[{}] Symbol for feature not found. Please use a simple renderer.".format(self.name))
            return 1

        symbol = symbols[0]
        return self.mapLayer.opacity() * symbol.opacity()

    # functions to read values from height widget (z coordinate)
    def useZ(self):
        """Return whether Z values should be used for height."""
        return self.properties.get("radioButton_zValue", False)

    def useM(self):
        """Return whether M values should be used for height."""
        return self.properties.get("radioButton_mValue", False)

    def isHeightRelativeToDEM(self):
        """Return True if altitude mode is set relative to DEM."""
        return self.properties.get("comboBox_altitudeMode") is not None
