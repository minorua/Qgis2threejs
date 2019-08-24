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
from PyQt5.QtCore import QVariant
from qgis.core import QgsCoordinateTransform, QgsFeatureRequest, QgsGeometry, QgsProject, QgsRenderContext, QgsWkbTypes

from .conf import FEATURES_PER_BLOCK, DEBUG_MODE
from .buildlayer import LayerBuilder
from .datamanager import MaterialManager, ModelManager
from .geometry import Geometry, PointGeometry, LineGeometry, PolygonGeometry, TriangleMesh
from .propertyreader import VectorPropertyReader
from .qgis2threejstools import logMessage
from .vectorobject import ObjectType


GeomType2Class = {QgsWkbTypes.PointGeometry: PointGeometry,
                  QgsWkbTypes.LineGeometry: LineGeometry,
                  QgsWkbTypes.PolygonGeometry: PolygonGeometry}


def json_default(o):
    if isinstance(o, QVariant):
        return repr(o)
    raise TypeError(repr(o) + " is not JSON serializable")


class Feature:

    def __init__(self, layer, qGeom, altitude, propValues, attrs=None, labelHeight=None):
        self.layerProp = layer.prop
        self.geomType = layer.geomType
        self.geom = qGeom
        self.altitude = altitude
        self.values = propValues
        self.attributes = attrs
        self.labelHeight = labelHeight

        self.material = -1

    def clipGeometry(self, clip_geom):
        # clip geometry
        self.geom = self.geom.intersection(clip_geom)
        return self.geom

    def geometry(self, z0_func, transform_func, useZM=Geometry.NotUseZM, baseExtent=None, tmesh=None):
        geom = self.geom
        z_func = lambda x, y: z0_func(x, y) + self.altitude

        if self.geomType != QgsWkbTypes.PolygonGeometry or self.layerProp.objType == ObjectType.TriangularMesh:
            return GeomType2Class[self.geomType].fromQgsGeometry(geom, z_func, transform_func, useZM=useZM)

        # geometry type is polygon and object type is Overlay
        if tmesh:
            if baseExtent.rotation():
                geom.rotate(baseExtent.rotation(), baseExtent.center())
                geom = tmesh.splitPolygon(geom)
                geom.rotate(-baseExtent.rotation(), baseExtent.center())
            else:
                geom = tmesh.splitPolygon(geom)

            useCentroidHeight = False
            centroidPerPolygon = False
        else:
            useCentroidHeight = True
            centroidPerPolygon = True

        return PolygonGeometry.fromQgsGeometry(geom, z_func, transform_func, useCentroidHeight, centroidPerPolygon)


class VectorLayer:

    def __init__(self, settings, mapLayer, prop, materialManager, modelManager):
        self.settings = settings
        self.mapLayer = mapLayer
        self.prop = prop
        self.name = mapLayer.name() if mapLayer else "no title"
        self.materialManager = materialManager
        self.modelManager = modelManager

        self.transform = QgsCoordinateTransform(mapLayer.crs(), settings.crs, QgsProject.instance())
        self.geomType = mapLayer.geometryType()

        # attributes
        self.writeAttrs = prop.properties.get("checkBox_ExportAttrs", False)
        self.labelAttrIndex = prop.properties.get("comboBox_Label", None)
        self.fieldIndices = []
        self.fieldNames = []

        if self.writeAttrs:
            for index, field in enumerate(mapLayer.fields()):
                if field.editorWidgetSetup().type() != "Hidden":
                    self.fieldIndices.append(index)
                    self.fieldNames.append(field.displayName())

    def hasLabel(self):
        return bool(self.labelAttrIndex is not None)

    def features(self, request=None):
        mapTo3d = self.settings.mapTo3d()
        baseExtent = self.settings.baseExtent
        baseExtentGeom = baseExtent.geometry()
        rotation = baseExtent.rotation()
        prop = self.prop
        fields = self.mapLayer.fields()

        for f in self.mapLayer.getFeatures(request or QgsFeatureRequest()):
            geometry = f.geometry()
            if geometry is None:
                logMessage("null geometry skipped")
                continue

            # coordinate transformation - layer crs to project crs
            geom = QgsGeometry(geometry)
            if geom.transform(self.transform) != 0:
                logMessage("Failed to transform geometry")
                continue

            # check if geometry intersects with the base extent (rotated rect)
            if rotation and not baseExtentGeom.intersects(geom):
                continue

            # set feature to expression context
            prop.setContextFeature(f)

            # evaluate expression
            altitude = prop.altitude()
            propVals = prop.values(f)

            attrs = labelHeight = None
            if self.writeAttrs:
                attrs = [fields[i].displayString(f.attribute(i)) for i in self.fieldIndices]

                if self.hasLabel():
                    labelHeight = prop.labelHeight() * mapTo3d.multiplierZ

            # create a feature object
            yield Feature(self, geom, altitude, propVals, attrs, labelHeight)


class FeatureBlockBuilder:

    def __init__(self, settings, vlayer, jsLayerId, pathRoot=None, urlRoot=None, useZM=None, z_func=None, tmesh=None):
        self.settings = settings
        self.vlayer = vlayer
        self.jsLayerId = jsLayerId
        self.pathRoot = pathRoot
        self.urlRoot = urlRoot

        self.blockIndex = None
        self.features = []

        p = vlayer.prop.properties
        if useZM is None:
            if p.get("radioButton_zValue"):
                useZM = Geometry.UseZ
            elif p.get("radioButton_mValue"):
                useZM = Geometry.UseM
            else:
                useZM = Geometry.NotUseZM
        self.useZM = useZM

        if z_func is None:
            baseExtent = settings.baseExtent
            if vlayer.prop.isHeightRelativeToDEM():
                demId = p.get("comboBox_altitudeMode")
                demProvider = settings.demProviderByLayerId(demId)

                if vlayer.prop.objType == ObjectType.Overlay:
                    # get the grid size of the DEM layer which polygons overlay
                    demProp = settings.getPropertyReaderByLayerId(demId)
                    demSize = demProp.demSize(settings.mapSettings.outputSize())

                    # prepare triangle mesh
                    center = baseExtent.center()
                    half_width, half_height = (baseExtent.width() / 2,
                                               baseExtent.height() / 2)
                    xmin, ymin = (center.x() - half_width,
                                  center.y() - half_height)
                    xmax, ymax = (center.x() + half_width,
                                  center.y() + half_height)
                    xres, yres = (baseExtent.width() / (demSize.width() - 1),
                                  baseExtent.height() / (demSize.height() - 1))

                    tmesh = TriangleMesh(xmin, ymin, xmax, ymax, demSize.width() - 1, demSize.height() - 1)
                    z_func = lambda x, y: demProvider.readValueOnTriangles(x, y, xmin, ymin, xres, yres)
                else:
                    z_func = lambda x, y: demProvider.readValue(x, y)
            else:
                z_func = lambda x, y: 0

        self.z_func = z_func
        self.tmesh = tmesh

    def clone(self):
        return FeatureBlockBuilder(self.settings, self.vlayer, self.jsLayerId,
                                   self.pathRoot, self.urlRoot,
                                   self.useZM, self.z_func, self.tmesh)

    def setBlockIndex(self, index):
        self.blockIndex = index

    def setFeatures(self, features):
        self.features = features

    def build(self):
        obj_geom_func = self.vlayer.prop.objType.geometry
        transform_func = self.settings.mapTo3d().transform

        feats = []
        for f in self.features:
            d = {}
            d["geom"] = obj_geom_func(self.settings, self.vlayer, f,
                                      f.geometry(self.z_func, transform_func, self.useZM,
                                                 self.settings.baseExtent, self.tmesh))

            if f.material is not None:
                d["mtl"] = f.material
            elif f.model is not None:
                d["model"] = f.model

            if f.attributes is not None:
                d["prop"] = f.attributes

                if f.labelHeight is not None:
                    d["lh"] = f.labelHeight

            feats.append(d)

        data = {
            "type": "block",
            "layer": self.jsLayerId,
            "block": self.blockIndex,
            "features": feats
        }

        if self.pathRoot is not None:
            with open(self.pathRoot + "{0}.json".format(self.blockIndex), "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2 if DEBUG_MODE else None, default=json_default)

            url = self.urlRoot + "{0}.json".format(self.blockIndex)
            return {"url": url}

        else:
            return data


class VectorLayerBuilder(LayerBuilder):

    gt2str = {QgsWkbTypes.PointGeometry: "point",
              QgsWkbTypes.LineGeometry: "line",
              QgsWkbTypes.PolygonGeometry: "polygon"}

    def __init__(self, settings, imageManager, layer, pathRoot=None, urlRoot=None, progress=None, modelManager=None):
        LayerBuilder.__init__(self, settings, imageManager, layer, pathRoot, urlRoot, progress)

        self.materialManager = MaterialManager(settings.materialType())  # TODO: takes imageManager
        self.modelManager = ModelManager(settings)

        self.geomType = self.layer.mapLayer.geometryType()
        self.clipGeom = None

    def build(self, build_blocks=False):
        mapLayer = self.layer.mapLayer
        if mapLayer is None:
            return

        properties = self.layer.properties
        baseExtent = self.settings.baseExtent
        renderContext = QgsRenderContext.fromMapSettings(self.settings.mapSettings)
        renderer = mapLayer.renderer().clone()      # clone feature renderer

        self.prop = VectorPropertyReader(renderContext, renderer, mapLayer, properties)
        if self.prop.objType is None:
            logMessage("Object type not found")
            return

        vlayer = VectorLayer(self.settings, mapLayer, self.prop, self.materialManager, self.modelManager)
        self.vlayer = vlayer

        # feature request
        request = QgsFeatureRequest()
        if properties.get("radioButton_IntersectingFeatures", False):
            request.setFilterRect(vlayer.transform.transformBoundingBox(baseExtent.boundingBox(),
                                                                        QgsCoordinateTransform.ReverseTransform))

            # geometry for clipping
            if properties.get("checkBox_Clip") and self.prop.objType != ObjectType.TriangularMesh:
                extent = baseExtent.clone().scale(0.999999)   # clip with slightly smaller extent than map canvas extent
                self.clipGeom = extent.geometry()

        self.features = []
        data = {}

        # initialize symbol rendering, and then get features (geometry, attributes, color, etc.)
        renderer.startRender(renderContext, mapLayer.fields())

        # materials/models
        if self.prop.objType != ObjectType.ModelFile:
            for feat in vlayer.features(request):
                feat.material = self.prop.objType.material(self.settings, vlayer, feat)
                feat.model = None
                self.features.append(feat)
            data["materials"] = self.materialManager.buildAll(self.imageManager, self.pathRoot, self.urlRoot,
                                                              base64=self.settings.base64)

        else:
            for feat in vlayer.features(request):
                feat.material = None
                feat.model = self.prop.objType.model(self.settings, vlayer, feat)
                self.features.append(feat)
            data["models"] = self.modelManager.build(self.pathRoot is not None)

        renderer.stopRender(renderContext)

        if build_blocks:
            data["blocks"] = [block.build() for block in self.blocks()]

        d = {
            "type": "layer",
            "id": self.layer.jsLayerId,
            "properties": self.layerProperties(),
            "data": data
        }

        if DEBUG_MODE:
            d["PROPERTIES"] = properties
        return d

    def layerProperties(self):
        p = LayerBuilder.layerProperties(self)
        p["type"] = self.gt2str.get(self.layer.mapLayer.geometryType())
        p["objType"] = self.prop.objType.name

        if self.vlayer.writeAttrs:
            p["propertyNames"] = self.vlayer.fieldNames

            if self.vlayer.labelAttrIndex is not None:
                p["label"] = {"index": self.vlayer.labelAttrIndex,
                              "relative": self.properties.get("labelHeightWidget", {}).get("comboData", 0) == 1}

        # object-type-specific properties
        # p.update(self.prop.objType.layerProperties(self.settings, self))
        return p

    def blocks(self):
        builder = FeatureBlockBuilder(self.settings, self.vlayer, self.layer.jsLayerId, self.pathRoot, self.urlRoot)

        index = 0
        feats = []
        for f in self.features or []:
            if self.clipGeom and self.geomType != QgsWkbTypes.PointGeometry:
                if f.clipGeometry(self.clipGeom) is None:
                    continue

            # skip if geometry is empty or null
            if f.geom.isEmpty() or f.geom.isNull():
                if not self.clipGeom:
                    logMessage("empty/null geometry skipped")
                continue

            feats.append(f)

            if len(feats) == FEATURES_PER_BLOCK:
                b = builder.clone()
                b.setBlockIndex(index)
                b.setFeatures(feats)
                yield b
                index += 1
                feats = []

        if len(feats) or index == 0:
            builder.setBlockIndex(index)
            builder.setFeatures(feats)
            yield builder
