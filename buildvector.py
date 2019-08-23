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

    def geometry(self, z0_func, transform_func, useZM=Geometry.NotUseZM, clipGeom=None, baseExtent=None, tmesh=None):

        geom = self.geom
        # clip geometry
        if clipGeom and self.geomType in [QgsWkbTypes.LineGeometry, QgsWkbTypes.PolygonGeometry]:
            geom = geom.intersection(clipGeom)
            if geom is None:
                return None

        # skip if geometry is empty or null
        if geom.isEmpty() or geom.isNull():
            logMessage("empty/null geometry skipped")
            return None

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

    def __init__(self, settings, layer, prop, materialManager, modelManager):
        self.settings = settings
        self.layer = layer
        self.prop = prop
        self.name = layer.name() if layer else "no title"
        self.materialManager = materialManager
        self.modelManager = modelManager

        self.transform = QgsCoordinateTransform(layer.crs(), settings.crs, QgsProject.instance())
        self.geomType = layer.geometryType()

        # attributes
        self.writeAttrs = prop.properties.get("checkBox_ExportAttrs", False)
        self.labelAttrIndex = prop.properties.get("comboBox_Label", None)
        self.fieldIndices = []
        self.fieldNames = []

        if self.writeAttrs:
            for index, field in enumerate(layer.fields()):
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
        fields = self.layer.fields()

        for f in self.layer.getFeatures(request or QgsFeatureRequest()):
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

    def __init__(self, blockIndex, data, pathRoot=None, urlRoot=None):
        self.blockIndex = blockIndex
        self.data = data
        self.pathRoot = pathRoot
        self.urlRoot = urlRoot

    def build(self):
        if self.pathRoot is not None:
            with open(self.pathRoot + "{0}.json".format(self.blockIndex), "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2 if DEBUG_MODE else None, default=json_default)

            url = self.urlRoot + "{0}.json".format(self.blockIndex)
            return {"url": url}

        else:
            return self.data


class VectorLayerBuilder(LayerBuilder):

    gt2str = {QgsWkbTypes.PointGeometry: "point",
              QgsWkbTypes.LineGeometry: "line",
              QgsWkbTypes.PolygonGeometry: "polygon"}

    def __init__(self, settings, imageManager, layer, pathRoot=None, urlRoot=None, progress=None, modelManager=None):
        LayerBuilder.__init__(self, settings, imageManager, layer, pathRoot, urlRoot, progress)

        self.materialManager = MaterialManager(settings.materialType())  # TODO: takes imageManager
        self.modelManager = ModelManager(settings)

        self.geomType = self.layer.mapLayer.geometryType()

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

        layer = VectorLayer(self.settings, mapLayer, self.prop, self.materialManager, self.modelManager)
        self._layer = layer

        self.hasLabel = layer.hasLabel()
        self.clipGeom = None

        # feature request
        request = QgsFeatureRequest()
        if properties.get("radioButton_IntersectingFeatures", False):
            request.setFilterRect(layer.transform.transformBoundingBox(baseExtent.boundingBox(),
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
            for feat in layer.features(request):
                feat.material = self.prop.objType.material(self.settings, layer, feat)
                feat.model = None
                self.features.append(feat)
            data["materials"] = self.materialManager.buildAll(self.imageManager, self.pathRoot, self.urlRoot,
                                                              base64=self.settings.base64)

        else:
            for feat in layer.features(request):
                feat.material = None
                feat.model = self.prop.objType.model(self.settings, layer, feat)
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

        if self._layer.writeAttrs:
            p["propertyNames"] = self._layer.fieldNames

            if self._layer.labelAttrIndex is not None:
                p["label"] = {"index": self._layer.labelAttrIndex,
                              "relative": self.properties.get("labelHeightWidget", {}).get("comboData", 0) == 1}

        # object-type-specific properties
        # p.update(self.prop.objType.layerProperties(self.settings, self))
        return p

    def createBlockBuilder(self, blockIndex, features):
        return FeatureBlockBuilder(blockIndex, {
            "type": "block",
            "layer": self.layer.jsLayerId,
            "block": blockIndex,
            "features": features
        }, self.pathRoot, self.urlRoot)

    def blocks(self):
        baseExtent = self.settings.baseExtent

        if self.layer.properties.get("radioButton_zValue"):
            useZM = Geometry.UseZ
        elif self.layer.properties.get("radioButton_mValue"):
            useZM = Geometry.UseM
        else:
            useZM = Geometry.NotUseZM

        demProvider = tmesh = None
        if self.prop.isHeightRelativeToDEM():
            demId = self.layer.properties.get("comboBox_altitudeMode")
            demProvider = self.settings.demProviderByLayerId(demId)

            if self.prop.objType == ObjectType.Overlay:
                # get the grid size of the DEM layer which polygons overlay
                demProp = self.settings.getPropertyReaderByLayerId(demId)
                demSize = demProp.demSize(self.settings.mapSettings.outputSize())

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

        transform_func = self.settings.mapTo3d().transform
        obj_geom_func = self.prop.objType.geometry

        index = 0
        feats = []
        for feat in self.features or []:
            geom = feat.geometry(z_func, transform_func, useZM, self.clipGeom, baseExtent, tmesh)
            if geom is None:
                continue

            f = {}
            f["geom"] = obj_geom_func(self.settings, self._layer, feat, geom)

            if feat.material is not None:
                f["mtl"] = feat.material
            elif feat.model is not None:
                f["model"] = feat.model
            else:   # no material nor model
                continue

            if feat.attributes is not None:
                f["prop"] = feat.attributes

                if feat.labelHeight is not None:
                    f["lh"] = feat.labelHeight

            feats.append(f)

            if len(feats) == FEATURES_PER_BLOCK:
                yield self.createBlockBuilder(index, feats)
                index += 1
                feats = []

        if len(feats) or index == 0:
            yield self.createBlockBuilder(index, feats)
