# -*- coding: utf-8 -*-
# (C) 2024 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later
# MapLibre GL builder for web preview

import json
from qgis.core import Qgis, QgsApplication, QgsVectorLayer, QgsRasterLayer, QgsFeatureRequest, QgsGeometry
from qgis.PyQt.QtCore import Qt

from .layerbuilderbase import LayerBuilderBase
from ..const import LayerType
from ...utils import int_color, noop


class MapLibreGLBuilder:
    """Builder for MapLibre GL web preview using GeoJSON format."""

    def __init__(self, settings, progress=None, log=None):
        self.settings = settings
        self.progress = progress or noop
        self.log = log or noop
        self._canceled = False

    def buildScene(self, cancelSignal=None):
        """Build scene data compatible with MapLibre GL."""
        self.progress(5, "Building MapLibre GL scene...")
        be = self.settings.baseExtent()
        mapTo3d = self.settings.mapTo3d()

        p = {
            "baseExtent": {
                "cx": be.center().x(),
                "cy": be.center().y(),
                "width": be.width(),
                "height": be.height(),
                "rotation": be.rotation()
            },
            "origin": {
                "x": mapTo3d.origin.x(),
                "y": mapTo3d.origin.y(),
                "z": mapTo3d.origin.z()
            },
            "zScale": mapTo3d.zScale
        }

        obj = {
            "type": "scene",
            "properties": p
        }

        obj["layers"] = self.buildLayers(cancelSignal)

        return obj

    def buildLayers(self, cancelSignal=None):
        """Build all visible layers as GeoJSON."""
        if cancelSignal:
            cancelSignal.connect(self.cancel)

        layers = []
        layer_list = [layer for layer in self.settings.layers() if layer.visible]
        total = len(layer_list)

        for i, layer in enumerate(layer_list):
            self.progress(int(i / total * 80) + 10, "Building {} layer...".format(layer.name))

            if self.canceled:
                break

            obj = self.buildLayer(layer, cancelSignal)
            if obj:
                layers.append(obj)

        if cancelSignal:
            cancelSignal.disconnect(self.cancel)

        return layers

    def buildLayer(self, layer, cancelSignal=None):
        """Build a single layer as GeoJSON."""
        if layer.mapLayer is None:
            return None

        mapLayer = layer.mapLayer

        # Get layer geometry type
        geomType = layer.type

        if geomType == LayerType.POINT or geomType == LayerType.LINESTRING or geomType == LayerType.POLYGON:
            return self.buildVectorLayer(layer, mapLayer)
        elif geomType == LayerType.DEM:
            return self.buildDEMLayer(layer, mapLayer)
        elif geomType == LayerType.POINTCLOUD:
            return self.buildPointCloudLayer(layer, mapLayer)

        return None

    def buildVectorLayer(self, layer, mapLayer):
        """Convert a vector layer to GeoJSON format."""
        features = []

        # Get all features from the vector layer
        request = QgsFeatureRequest()
        for feature in mapLayer.getFeatures(request):
            if self.canceled:
                break

            geom = feature.geometry()
            if geom is None or geom.isEmpty():
                continue

            geom_dict = self.geometryToGeoJSON(geom)
            if geom_dict is None:
                continue

            # Get feature properties
            properties = {}
            fields = mapLayer.fields()
            for field_idx in range(fields.count()):
                field_name = fields[field_idx].name()
                field_value = feature.attribute(field_name)
                properties[field_name] = field_value if field_value is not None else ""

            # Create GeoJSON feature
            feature_dict = {
                "type": "Feature",
                "geometry": geom_dict,
                "properties": properties
            }
            features.append(feature_dict)

        if not features:
            return None

        # Get layer properties
        properties = layer.properties
        color = int_color(properties.get("Color", "#0088ff"))
        color_hex = "#{:06x}".format(color)

        layer_obj = {
            "type": "layer",
            "id": layer.jsLayerId,
            "geomType": self.geomTypeToString(layer.type),
            "features": features,
            "properties": {
                "name": layer.name,
                "color": color_hex,
                "opacity": properties.get("Opacity", 0.8),
                "lineWidth": properties.get("LineWidth", 2),
                "pointSize": properties.get("PointSize", 5),
                "materials": properties.get("materials", []),
                "visible": layer.visible
            }
        }

        return layer_obj

    def buildDEMLayer(self, layer, mapLayer):
        """Handle DEM layer (simplified for MapLibre GL)."""
        # For now, return a minimal structure
        # Full DEM support would require more complex handling
        return {
            "type": "layer",
            "id": layer.jsLayerId,
            "geomType": "dem",
            "properties": {
                "name": layer.name,
                "type": "dem",
                "visible": layer.visible
            }
        }

    def buildPointCloudLayer(self, layer, mapLayer):
        """Handle point cloud layer."""
        # Minimal point cloud support
        return {
            "type": "layer",
            "id": layer.jsLayerId,
            "geomType": "pointcloud",
            "properties": {
                "name": layer.name,
                "type": "pointcloud",
                "visible": layer.visible
            }
        }

    def geometryToGeoJSON(self, geom):
        """Convert QGIS geometry to GeoJSON format."""
        geomType = geom.type()

        if geomType == QgsGeometry.PointGeometry:
            pt = geom.asPoint()
            return {
                "type": "Point",
                "coordinates": [pt.x(), pt.y()]
            }
        elif geomType == QgsGeometry.LineGeometry:
            line = geom.asPolyline()
            if not line:
                return None
            coords = [[pt.x(), pt.y()] for pt in line]
            return {
                "type": "LineString",
                "coordinates": coords
            }
        elif geomType == QgsGeometry.PolygonGeometry:
            polygon = geom.asPolygon()
            if not polygon:
                return None
            rings = [[[pt.x(), pt.y()] for pt in ring] for ring in polygon]
            return {
                "type": "Polygon",
                "coordinates": rings
            }
        elif geomType == QgsGeometry.MultiPointGeometry:
            points = geom.asMultiPoint()
            coords = [[pt.x(), pt.y()] for pt in points]
            return {
                "type": "MultiPoint",
                "coordinates": coords
            }
        elif geomType == QgsGeometry.MultiLineGeometry:
            lines = geom.asMultiPolyline()
            coords = [[[pt.x(), pt.y()] for pt in line] for line in lines]
            return {
                "type": "MultiLineString",
                "coordinates": coords
            }
        elif geomType == QgsGeometry.MultiPolygonGeometry:
            polygons = geom.asMultiPolygon()
            coords = [[[[pt.x(), pt.y()] for pt in ring] for ring in polygon] for polygon in polygons]
            return {
                "type": "MultiPolygon",
                "coordinates": coords
            }

        return None

    def geomTypeToString(self, layerType):
        """Convert LayerType to geometry type string."""
        if layerType == LayerType.POINT:
            return "point"
        elif layerType == LayerType.LINESTRING:
            return "linestring"
        elif layerType == LayerType.POLYGON:
            return "polygon"
        elif layerType == LayerType.DEM:
            return "dem"
        elif layerType == LayerType.POINTCLOUD:
            return "pointcloud"
        return "unknown"

    @property
    def canceled(self):
        if not self._canceled:
            QgsApplication.processEvents()
        return self._canceled

    @canceled.setter
    def canceled(self, value):
        self._canceled = value

    def cancel(self):
        self._canceled = True
