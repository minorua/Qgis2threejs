# -*- coding: utf-8 -*-
# (C) 2014 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later
# begin: 2014-01-16

import json
import random
from PyQt5.QtCore import QVariant
from PyQt5.QtGui import QColor
from qgis.core import (QgsCoordinateTransform, QgsExpression, QgsFeatureRequest, QgsGeometry, QgsProject, QgsRenderContext)

from .conf import DEF_SETS, FEATURES_PER_BLOCK, DEBUG_MODE
from .buildlayer import LayerBuilder
from .datamanager import MaterialManager, ModelManager
from .geometry import VectorGeometry, PointGeometry, LineGeometry, PolygonGeometry, TINGeometry
from .q3dconst import LayerType, PropertyID as PID
from .utils import css_color, hex_color, int_color, logMessage, parseFloat, parseInt
from .propwidget import PropertyWidget, ColorWidgetFunc, OpacityWidgetFunc, ColorTextureWidgetFunc
from .vectorobject import ObjectType


LayerType2GeomClass = {
    LayerType.POINT: PointGeometry,
    LayerType.LINESTRING: LineGeometry,
    LayerType.POLYGON: PolygonGeometry
}


def json_default(o):
    if isinstance(o, QVariant):
        return repr(o)
    raise TypeError(repr(o) + " is not JSON serializable")


class Feature:

    def __init__(self, vlayer, geom, props, attrs=None):

        self.layerType = vlayer.type
        self.ot = vlayer.ot

        self.geom = geom            # an instance of QgsGeometry
        self.props = props          # a dict
        self.attributes = attrs     # a list or None

        self.material = self.model = None

    def clipGeometry(self, extent):
        r = extent.rotation()
        if r:
            self.geom.rotate(r, extent.center())

        self.geom = self.geom.clipped(extent.unrotatedRect())
        if r:
            self.geom.rotate(-r, extent.center())

        return self.geom

    def geometry(self, z_func, mapTo3d, useZM=VectorGeometry.NotUseZM, baseExtent=None, grid=None):
        alt = self.prop(PID.ALT, 0)
        zf = lambda x, y: z_func(x, y) + alt

        transform_func = mapTo3d.transform

        if self.layerType != LayerType.POLYGON:
            return LayerType2GeomClass[self.layerType].fromQgsGeometry(self.geom, zf, transform_func, useZM=useZM)

        objType = type(self.ot)
        if objType == ObjectType.Polygon:
            return TINGeometry.fromQgsGeometry(self.geom, zf, transform_func,
                                               drop_z=(useZM == VectorGeometry.NotUseZM))

        if objType == ObjectType.Extruded:
            return PolygonGeometry.fromQgsGeometry(self.geom, zf, transform_func,
                                                   useCentroidHeight=True,
                                                   centroidPerPolygon=True)

        # Overlay
        border = bool(self.prop(PID.C2) is not None)
        if grid is None:
            # absolute z coordinate
            g = TINGeometry.fromQgsGeometry(self.geom, zf, transform_func, drop_z=True)
            if border:
                g.bnds_list = PolygonGeometry.fromQgsGeometry(self.geom, zf, transform_func).toLineGeometryList()
            return g

        # relative to DEM
        transform_func = mapTo3d.transform

        if baseExtent.rotation():
            self.geom.rotate(baseExtent.rotation(), baseExtent.center())

        polys = grid.splitPolygon(self.geom)
        g = TINGeometry.fromQgsGeometry(polys, zf, transform_func, use_earcut=True)

        if border:
            bnds = grid.segmentizeBoundaries(self.geom)
            g.bnds_list = [LineGeometry.fromQgsGeometry(bnd, zf, transform_func, useZM=VectorGeometry.UseZ) for bnd in bnds]
        return g

    def prop(self, pid, def_val=None):
        return self.props.get(pid, def_val)

    def hasProp(self, pid):
        return pid in self.props


class VectorLayer:

    def __init__(self, settings, layer, materialManager, modelManager):
        """layer: Layer object"""
        self.settings = settings
        self.renderContext = QgsRenderContext.fromMapSettings(settings.mapSettings)

        self.type = layer.type
        self.mapLayer = layer.mapLayer
        self.name = layer.name
        self.properties = layer.properties

        self.expressionContext = self.mapLayer.createExpressionContext()

        otc = ObjectType.typeByName(self.properties.get("comboBox_ObjectType"), layer.type)
        if otc == ObjectType.ModelFile:
            self.ot = otc(settings, modelManager)
        elif otc:
            self.ot = otc(settings, materialManager)
        else:
            self.ot = None
            logMessage("Shape type not found: {} ({})".format(self.properties.get("comboBox_ObjectType"), self.name), error=True)

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
                logMessage("[{}] Null geometry skipped.".format(self.name))
                continue

            geom = QgsGeometry(geom)

            # coordinate transformation - layer crs to project crs
            if geom.transform(self.transform) != 0:
                logMessage("[{}] Failed to transform a geometry.".format(self.name), warning=True)
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

    def evaluateExpression(self, expr_str, f):
        if expr_str not in self._exprs:
            self._exprs[expr_str] = QgsExpression(expr_str)

        self.expressionContext.setFeature(f)
        return self._exprs[expr_str].evaluate(self.expressionContext)

    def evaluatePropertyWidget(self, name, feat):
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
                logMessage("[{}] Failed to evaluate expression: {}".format(self.name, expr), warning=True)

            elif isinstance(val, str):
                val = parseFloat(val)
                if val is None:
                    logMessage("[{}] Cannot parse '{}' as a float value.".format(self.name, expr), warning=True)

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
                    logMessage("[{}] Failed to evaluate expression: {}".format(self.name, expr), warning=True)
                else:
                    logMessage("[{}] There is an empty file path.".format(self.name), warning=True)

            return val or ""

        if t == PropertyWidget.COLOR_TEXTURE:
            comboData = wv.get("comboData")
            if comboData == ColorTextureWidgetFunc.MAP_CANVAS:
                return comboData

            if comboData == ColorTextureWidgetFunc.LAYER:
                return wv.get("layerIds", [])

            return self.readFillColor(wv, feat)

        logMessage("Widget type {} not found.".format(t), error=True)
        return None

    def readFillColor(self, vals, f):
        return self._readColor(vals, f)

    def readBorderColor(self, vals, f):
        return self._readColor(vals, f, isBorder=True)

    # read color from COLOR or OPTIONAL_COLOR widget
    def _readColor(self, wv, f, isBorder=False):
        mode = wv["comboData"]
        if mode is None:
            return None

        if mode == ColorWidgetFunc.EXPRESSION:
            val = self.evaluateExpression(wv["editText"], f)
            try:
                if isinstance(val, str):
                    a = val.split(",")
                    if len(a) >= 3:
                        a = [max(0, min(int(c), 255)) for c in a[:3]]
                        return "0x{:02x}{:02x}{:02x}".format(a[0], a[1], a[2])
                    return val.replace("#", "0x")

                raise
            except:
                logMessage("[{}] Wrong color value: {}".format(self.name, val), warning=True)
                return "0"

        if mode == ColorWidgetFunc.RANDOM or f is None:
            self.colorNames = self.colorNames or QColor.colorNames()
            color = random.choice(self.colorNames)
            self.colorNames.remove(color)
            return hex_color(QColor(color).name(), prefix="0x")

        # feature color
        symbols = self.renderer.symbolsForFeature(f, self.renderContext)
        if not symbols:
            logMessage("[{}] Symbol for feature not found. Please use a simple renderer.".format(self.name), warning=True)
            return "0"

        symbol = symbols[0]
        if isBorder:
            sl = symbol.symbolLayer(0)
            if sl:
                return sl.strokeColor().name().replace("#", "0x")

        return symbol.color().name().replace("#", "0x")

    def readOpacity(self, wv, f):

        if wv["comboData"] == OpacityWidgetFunc.EXPRESSION:
            try:
                val = self.evaluateExpression(wv["editText"], f)
                return min(max(0, val), 100) / 100
            except:
                logMessage("[{}] Wrong opacity value: {}".format(self.name, val), warning=True)
                return 1

        symbols = self.renderer.symbolsForFeature(f, self.renderContext)
        if not symbols:
            logMessage("[{}] Symbol for feature not found. Please use a simple renderer.".format(self.name), warning=True)
            return 1

        symbol = symbols[0]
        return self.mapLayer.opacity() * symbol.opacity()

    @classmethod
    def toFloat(cls, val):
        try:
            return float(val)
        except Exception as e:
            logMessage('{0} (value: {1})'.format(e.message, str(val)), warning=True)
            return 0

    # functions to read values from height widget (z coordinate)
    def useZ(self):
        return self.properties.get("radioButton_zValue", False)

    def useM(self):
        return self.properties.get("radioButton_mValue", False)

    def isHeightRelativeToDEM(self):
        return self.properties.get("comboBox_altitudeMode") is not None


class FeatureBlockBuilder:

    def __init__(self, settings, vlayer, jsLayerId, pathRoot=None, urlRoot=None, useZM=VectorGeometry.NotUseZM, z_func=None, grid=None):
        self.settings = settings
        self.vlayer = vlayer
        self.jsLayerId = jsLayerId
        self.pathRoot = pathRoot
        self.urlRoot = urlRoot
        self.useZM = useZM
        self.z_func = z_func
        self.grid = grid

        self.blockIndex = None
        self.startFIdx = None
        self.features = []

    def clone(self):
        return FeatureBlockBuilder(self.settings, self.vlayer, self.jsLayerId,
                                   self.pathRoot, self.urlRoot,
                                   self.useZM, self.z_func, self.grid)

    def setBlockIndex(self, index):
        self.blockIndex = index

    def setFeatures(self, features):
        self.features = features

    def build(self):
        be = self.settings.baseExtent()
        obj_geom_func = self.vlayer.ot.geometry
        mapTo3d = self.settings.mapTo3d()

        feats = []
        for f in self.features:
            d = {}
            d["geom"] = obj_geom_func(f, f.geometry(self.z_func, mapTo3d, self.useZM, be, self.grid))

            if f.material is not None:
                d["mtl"] = f.material
            elif f.model is not None:
                d["model"] = f.model

            if f.attributes is not None:
                d["prop"] = f.attributes

            text = f.prop(PID.LBLTXT)
            if text is not None and text != "":
                d["lbl"] = str(text)
                d["lh"] = f.prop(PID.LBLH)

            if f.hasProp(PID.DLY):
                d["anim"] = {
                    "delay": parseInt(f.prop(PID.DLY)),
                    "duration": parseInt(f.prop(PID.DUR))
                }
                if DEBUG_MODE:
                    logMessage("dly: {}, dur: {}".format(d["anim"]["delay"], d["anim"]["duration"]))

            feats.append(d)

        data = {
            "type": "block",
            "layer": self.jsLayerId,
            "block": self.blockIndex,
            "features": feats,
            "featureCount": len(feats),
            "startIndex": self.startFIdx
        }

        if self.pathRoot is not None:
            with open(self.pathRoot + "{0}.json".format(self.blockIndex), "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2 if DEBUG_MODE else None, default=json_default)

            url = self.urlRoot + "{0}.json".format(self.blockIndex)
            return {"url": url, "featureCount": len(feats)}

        else:
            return data


class VectorLayerBuilder(LayerBuilder):

    type2str = {
        LayerType.POINT: "point",
        LayerType.LINESTRING: "line",
        LayerType.POLYGON: "polygon"
    }

    def __init__(self, settings, layer, imageManager, pathRoot=None, urlRoot=None, progress=None, log=None):
        LayerBuilder.__init__(self, settings, layer, imageManager, pathRoot, urlRoot, progress, log)

        self.materialManager = MaterialManager(imageManager, settings.materialType())
        self.modelManager = ModelManager(settings)

        self.clipExtent = None

        vl = VectorLayer(settings, layer, self.materialManager, self.modelManager)
        if vl.ot:
            self.log("Object type is {}.".format(vl.ot.name))
        else:
            logMessage("Object type not found", error=True)

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
        p = LayerBuilder.layerProperties(self)
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
                    logMessage("empty/null geometry skipped")
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
