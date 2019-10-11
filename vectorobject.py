# -*- coding: utf-8 -*-
"""
/***************************************************************************
 Qgis2threejs
                                 A QGIS plugin
 export terrain data, map canvas image and vector data to web browser
                             -------------------
        begin                : 2014-01-11
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
from qgis.core import QgsWkbTypes

from Qgis2threejs.stylewidget import StyleWidget, OptionalColorWidgetFunc, ColorTextureWidgetFunc


class ObjectTypeBase:

    experimental = False

    @classmethod
    def displayName(cls):
        return tr(cls.name)

    @classmethod
    def setupWidgets(cls, ppage, mapTo3d, mapLayer):
        pass

    # @classmethod
    # def layerProperties(cls, settings, layer):
    #     return {}

    @classmethod
    def material(cls, settings, vlayer, feat):
        pass

    @classmethod
    def geometry(cls, settings, vlayer, feat, geom):
        pass

    @classmethod
    def defaultValue(cls, mapTo3d):
        return float("{0:.4g}".format(1.0 / mapTo3d.multiplier))

    @classmethod
    def defaultValueZ(cls, mapTo3d):
        return float("{0:.4g}".format(1.0 / mapTo3d.multiplierZ))


class PointTypeBase(ObjectTypeBase):

    geometryType = QgsWkbTypes.PointGeometry


class LineTypeBase(ObjectTypeBase):

    geometryType = QgsWkbTypes.LineGeometry


class PolygonTypeBase(ObjectTypeBase):

    geometryType = QgsWkbTypes.PolygonGeometry


# PointBasicType
class PointBasicTypeBase(PointTypeBase):

    @classmethod
    def material(cls, settings, vlayer, feat):
        return vlayer.materialManager.getMeshMaterialIndex(feat.values[0], feat.values[1])


class PointType(ObjectTypeBase):

    name = "Point"

    @classmethod
    def setupWidgets(cls, ppage, mapTo3d, mapLayer):
        ppage.initStyleWidgets()
        ppage.addStyleWidget(StyleWidget.EXPRESSION, {"name": "Size", "defaultValue": 1, "layer": mapLayer})

    @classmethod
    def material(cls, settings, vlayer, feat):
        return vlayer.materialManager.getPointMaterialIndex(feat.values[0], feat.values[1], feat.values[2])

    @classmethod
    def geometry(cls, settings, vlayer, feat, geom):
        v = []
        for pt in geom.toList():
            v.extend(pt)
        return {"pts": v}


class SphereType(PointBasicTypeBase):

    name = "Sphere"

    @classmethod
    def setupWidgets(cls, ppage, mapTo3d, mapLayer):
        ppage.initStyleWidgets()
        ppage.addStyleWidget(StyleWidget.EXPRESSION, {"name": "Radius", "defaultValue": cls.defaultValue(mapTo3d), "layer": mapLayer})

    @classmethod
    def geometry(cls, settings, vlayer, feat, geom):
        return {"pts": geom.toList(),
                "r": feat.values[2] * settings.mapTo3d().multiplier}


class CylinderType(PointBasicTypeBase):

    name = "Cylinder"

    @classmethod
    def setupWidgets(cls, ppage, mapTo3d, mapLayer):
        ppage.initStyleWidgets()
        ppage.addStyleWidget(StyleWidget.EXPRESSION, {"name": "Radius", "defaultValue": cls.defaultValue(mapTo3d), "layer": mapLayer})
        ppage.addStyleWidget(StyleWidget.EXPRESSION, {"name": "Height", "defaultValue": cls.defaultValueZ(mapTo3d), "layer": mapLayer})

    @classmethod
    def geometry(cls, settings, vlayer, feat, geom):
        mapTo3d = settings.mapTo3d()
        r = feat.values[2] * mapTo3d.multiplier
        return {"pts": geom.toList(),
                "r": r,
                "h": feat.values[3] * mapTo3d.multiplierZ}


class ConeType(CylinderType):

    name = "Cone"


class BoxType(PointBasicTypeBase):

    name = "Box"

    @classmethod
    def setupWidgets(cls, ppage, mapTo3d, mapLayer):
        ppage.initStyleWidgets()
        val = cls.defaultValue(mapTo3d)
        ppage.addStyleWidget(StyleWidget.EXPRESSION, {"name": "Width", "defaultValue": val, "layer": mapLayer})
        ppage.addStyleWidget(StyleWidget.EXPRESSION, {"name": "Depth", "defaultValue": val, "layer": mapLayer})
        ppage.addStyleWidget(StyleWidget.EXPRESSION, {"name": "Height", "defaultValue": cls.defaultValueZ(mapTo3d), "layer": mapLayer})

    @classmethod
    def geometry(cls, settings, vlayer, feat, geom):
        mapTo3d = settings.mapTo3d()
        return {"pts": geom.toList(),
                "w": feat.values[2] * mapTo3d.multiplier,
                "d": feat.values[3] * mapTo3d.multiplier,
                "h": feat.values[4] * mapTo3d.multiplierZ}


class DiskType(PointBasicTypeBase):

    name = "Disk"

    @classmethod
    def setupWidgets(cls, ppage, mapTo3d, mapLayer):
        ppage.initStyleWidgets()
        ppage.addStyleWidget(StyleWidget.EXPRESSION, {"name": "Radius", "defaultValue": cls.defaultValue(mapTo3d), "layer": mapLayer})
        ppage.addStyleWidget(StyleWidget.EXPRESSION, {"name": "Dip", "label": "Degrees", "defaultValue": 0, "label_field": None, "layer": mapLayer})
        ppage.addStyleWidget(StyleWidget.EXPRESSION, {"name": "Dip direction", "label": "Degrees", "defaultValue": 0, "label_field": None, "layer": mapLayer})

    @classmethod
    def material(cls, settings, vlayer, feat):
        return vlayer.materialManager.getMeshMaterialIndex(feat.values[0], feat.values[1], doubleSide=True)

    @classmethod
    def geometry(cls, settings, vlayer, feat, geom):
        dd = feat.values[4]
        # take map rotation into account
        rotation = settings.baseExtent.rotation()
        if rotation:
            dd = (dd + rotation) % 360

        return {"pts": geom.toList(),
                "r": feat.values[2] * settings.mapTo3d().multiplier,
                "d": feat.values[3],
                "dd": dd}


class PlaneType(PointBasicTypeBase):

    name = "Plane"

    @classmethod
    def setupWidgets(cls, ppage, mapTo3d, mapLayer):
        ppage.initStyleWidgets()
        ppage.addStyleWidget(StyleWidget.EXPRESSION, {"name": "Width", "defaultValue": cls.defaultValue(mapTo3d), "layer": mapLayer})
        ppage.addStyleWidget(StyleWidget.EXPRESSION, {"name": "Length", "defaultValue": cls.defaultValue(mapTo3d), "layer": mapLayer})
        ppage.addStyleWidget(StyleWidget.EXPRESSION, {"name": "Dip", "label": "Degrees", "defaultValue": 0, "label_field": None, "layer": mapLayer})
        ppage.addStyleWidget(StyleWidget.EXPRESSION, {"name": "Dip direction", "label": "Degrees", "defaultValue": 0, "label_field": None, "layer": mapLayer})

    @classmethod
    def material(cls, settings, vlayer, feat):
        return vlayer.materialManager.getMeshMaterialIndex(feat.values[0], feat.values[1], doubleSide=True)

    @classmethod
    def geometry(cls, settings, vlayer, feat, geom):
        dd = feat.values[5]
        # take map rotation into account
        rotation = settings.baseExtent.rotation()
        if rotation:
            dd = (dd + rotation) % 360

        return {"pts": geom.toList(),
                "w": feat.values[2] * settings.mapTo3d().multiplier,
                "l": feat.values[3] * settings.mapTo3d().multiplier,
                "d": feat.values[4],
                "dd": dd}


# LineBasicType
class LineBasicTypeBase(LineTypeBase):

    pass


class LineType(LineBasicTypeBase):

    name = "Line"

    @classmethod
    def setupWidgets(cls, ppage, mapTo3d, mapLayer):
        ppage.initStyleWidgets()
        ppage.addStyleWidget(StyleWidget.CHECKBOX, {"name": "Dashed", "defaultValue": False})

    @classmethod
    def material(cls, settings, vlayer, feat):
        try:
            if feat.values[2]:
                return vlayer.materialManager.getDashedLineIndex(feat.values[0], feat.values[1])
        except IndexError:    # for backward compatibility (dashed option was added in 2.1)
            pass

        return vlayer.materialManager.getBasicLineIndex(feat.values[0], feat.values[1])

    @classmethod
    def geometry(cls, settings, vlayer, feat, geom):
        return {"lines": geom.toList()}


class PipeType(LineBasicTypeBase):

    name = "Pipe"

    @classmethod
    def setupWidgets(cls, ppage, mapTo3d, mapLayer):
        ppage.initStyleWidgets()
        ppage.addStyleWidget(StyleWidget.EXPRESSION, {"name": "Radius", "defaultValue": cls.defaultValue(mapTo3d), "layer": mapLayer})

    @classmethod
    def material(cls, settings, vlayer, feat):
        return vlayer.materialManager.getMeshMaterialIndex(feat.values[0], feat.values[1])

    @classmethod
    def geometry(cls, settings, vlayer, feat, geom):
        r = feat.values[2] * settings.mapTo3d().multiplier
        return {"lines": geom.toList(),
                "r": r}


class ConeLineType(PipeType):

    name = "Cone"


class BoxLineType(LineBasicTypeBase):

    name = "Box"

    @classmethod
    def setupWidgets(cls, ppage, mapTo3d, mapLayer):
        ppage.initStyleWidgets()
        val = cls.defaultValue(mapTo3d)
        ppage.addStyleWidget(StyleWidget.EXPRESSION, {"name": "Width", "defaultValue": val, "layer": mapLayer})
        ppage.addStyleWidget(StyleWidget.EXPRESSION, {"name": "Height", "defaultValue": val, "layer": mapLayer})

    @classmethod
    def material(cls, settings, vlayer, feat):
        return vlayer.materialManager.getMeshMaterialIndex(feat.values[0], feat.values[1])

    @classmethod
    def geometry(cls, settings, vlayer, feat, geom):
        multiplier = settings.mapTo3d().multiplier
        return {"lines": geom.toList(),
                "w": feat.values[2] * multiplier,
                "h": feat.values[3] * multiplier}


class WallType(LineBasicTypeBase):

    name = "Wall"

    @classmethod
    def setupWidgets(cls, ppage, mapTo3d, mapLayer):
        ppage.initStyleWidgets()
        ppage.addStyleWidget(StyleWidget.EXPRESSION, {"name": "Other side Z", "layer": mapLayer})

    @classmethod
    def material(cls, settings, vlayer, feat):
        return vlayer.materialManager.getFlatMeshMaterialIndex(feat.values[0], feat.values[1], doubleSide=True)

    @classmethod
    def geometry(cls, settings, vlayer, feat, geom):
        return {"lines": geom.toList(),
                "bh": feat.values[2] * settings.mapTo3d().multiplierZ}


# PolygonBasicType
class PolygonBasicTypeBase(PolygonTypeBase):

    @classmethod
    def geometry(cls, settings, vlayer, feat, geom):
        return {"polygons": geom.toList2(),
                "centroids": geom.centroids}


class PolygonType(PolygonBasicTypeBase):

    """3d polygon support: yes"""

    name = "Polygon"

    @classmethod
    def setupWidgets(cls, ppage, mapTo3d, mapLayer):
        ppage.initStyleWidgets()

    @classmethod
    def material(cls, settings, vlayer, feat):
        return vlayer.materialManager.getFlatMeshMaterialIndex(feat.values[0], feat.values[1], True)

    @classmethod
    def geometry(cls, settings, vlayer, feat, geom):
        g = geom.toDict(flat=True)
        return g


class ExtrudedType(PolygonBasicTypeBase):

    """3d polygon support: no"""

    name = "Extruded"

    @classmethod
    def setupWidgets(cls, ppage, mapTo3d, mapLayer):
        ppage.initStyleWidgets()
        ppage.addStyleWidget(StyleWidget.EXPRESSION, {"name": "Height", "defaultValue": cls.defaultValueZ(mapTo3d), "layer": mapLayer})

        opt = {"name": "Edge color",
               "itemText": {OptionalColorWidgetFunc.NONE: "(No Edge)"},
               "defaultValue": OptionalColorWidgetFunc.NONE}
        ppage.addStyleWidget(StyleWidget.OPTIONAL_COLOR, opt)

    @classmethod
    def material(cls, settings, vlayer, feat):
        mtl = {"face": vlayer.materialManager.getMeshMaterialIndex(feat.values[0], feat.values[1])}

        # edges
        if feat.values[3] is not None:
            mtl["edge"] = vlayer.materialManager.getBasicLineIndex(feat.values[3], feat.values[1])
        return mtl

    @classmethod
    def geometry(cls, settings, vlayer, feat, geom):
        g = PolygonBasicTypeBase.geometry(settings, vlayer, feat, geom)
        g["h"] = feat.values[2] * settings.mapTo3d().multiplierZ
        return g


class OverlayType(PolygonBasicTypeBase):

    """3d polygon support: no"""

    name = "Overlay"

    @classmethod
    def setupWidgets(cls, ppage, mapTo3d, mapLayer):
        ppage.initStyleWidgets()

        opt = {"name": "Border color",
               "itemText": {OptionalColorWidgetFunc.NONE: "(No border)"},
               "defaultValue": OptionalColorWidgetFunc.NONE}
        ppage.addStyleWidget(StyleWidget.OPTIONAL_COLOR, opt)

    @classmethod
    def material(cls, settings, vlayer, feat):
        if feat.values[0] == ColorTextureWidgetFunc.MAP_CANVAS:
            m = vlayer.materialManager.getCanvasImageIndex(feat.values[1])
        elif isinstance(feat.values[0], list):   # LAYER
            size = settings.mapSettings.outputSize()
            m = vlayer.materialManager.getLayerImageIndex(feat.values[0], size.width(), size.height(),
                                                          settings.baseExtent, feat.values[1])
        else:
            m = vlayer.materialManager.getMeshMaterialIndex(feat.values[0], feat.values[1], True)
        mtl = {"face": m}

        # border
        if len(feat.values) > 2 and feat.values[2] is not None:
            mtl["brdr"] = vlayer.materialManager.getBasicLineIndex(feat.values[2], feat.values[1])
        return mtl


    @classmethod
    def geometry(cls, settings, vlayer, feat, geom):
        g = geom.toDict(flat=True)  # TINGeometry

        # border
        if len(feat.values) > 2 and feat.values[2] is not None:
            g["brdr"] = [bnds.toList(flat=True) for bnds in geom.bnds_list]

        return g


# IconType
class IconType(PointTypeBase):

    name = "Icon"

    @classmethod
    def setupWidgets(cls, ppage, mapTo3d, mapLayer):
        filterString = "Images (*.png *.jpg *.gif *.bmp);;All files (*.*)"

        ppage.initStyleWidgets(color=False)
        ppage.addStyleWidget(StyleWidget.FILEPATH, {"name": "Image file", "layer": mapLayer, "filterString": filterString, "allowURL": True})
        ppage.addStyleWidget(StyleWidget.EXPRESSION, {"name": "Scale", "defaultValue": 1, "layer": mapLayer})

    @classmethod
    def material(cls, settings, vlayer, feat):
        path_url = feat.values[1]
        if path_url:
            return vlayer.materialManager.getSpriteImageIndex(path_url, feat.values[0])
        return None

    @classmethod
    def geometry(cls, settings, vlayer, feat, geom):
        return {"pts": geom.toList(),
                "scale": feat.values[2]}


# ModelFileType
class ModelFileType(PointTypeBase):

    name = "Model File"
    experimental = True

    @classmethod
    def setupWidgets(cls, ppage, mapTo3d, mapLayer):
        filterString = "Model files (*.dae *.gltf *.glb);;All files (*.*)"

        ppage.initStyleWidgets(color=False, opacity=False)
        ppage.addStyleWidget(StyleWidget.FILEPATH, {"name": "Model file", "layer": mapLayer, "filterString": filterString, "allowURL": True})
        ppage.addStyleWidget(StyleWidget.EXPRESSION, {"name": "Scale", "defaultValue": 1, "layer": mapLayer})
        ppage.addStyleWidget(StyleWidget.EXPRESSION, {"name": "Rotation (x)", "label": "Degrees", "defaultValue": 0, "layer": mapLayer})
        ppage.addStyleWidget(StyleWidget.EXPRESSION, {"name": "Rotation (y)", "label": "Degrees", "defaultValue": 0, "layer": mapLayer})
        ppage.addStyleWidget(StyleWidget.EXPRESSION, {"name": "Rotation (z)", "label": "Degrees", "defaultValue": 0, "layer": mapLayer})
        ppage.addStyleWidget(StyleWidget.COMBOBOX, {"name": "Rotation order", "defaultValue": "XYZ",
                                                    "items": ["XYZ", "XZY", "YXZ", "YZX", "ZXY", "ZYX"]})

    @classmethod
    def model(cls, settings, vlayer, feat):
        model_path = feat.values[0]
        if model_path:
            return vlayer.modelManager.modelIndex(model_path)
        return None

    @classmethod
    def geometry(cls, settings, vlayer, feat, geom):
        rz = feat.values[4]
        # take map rotation into account
        rotation = settings.baseExtent.rotation()
        if rotation:
            rz = (rz - rotation) % 360    # map rotation is clockwise

        d = {"pts": geom.toList(),
             "rotateX": feat.values[2],
             "rotateY": feat.values[3],
             "rotateZ": rz,
             "scale": feat.values[1] * settings.mapTo3d().multiplier}

        if len(feat.values) > 5 and feat.values[5] != "XYZ":    # added in 2.4
            d["rotateO"] = feat.values[5]
        return d


class ObjectType:

    # point
    Sphere = SphereType
    Cylinder = CylinderType
    Cone = ConeType
    Box = BoxType
    Disk = DiskType
    Plane = PlaneType
    Point = PointType
    Icon = IconType
    ModelFile = ModelFileType

    # line
    Line = LineType
    Pipe = PipeType
    ConeLine = ConeLineType
    BoxLine = BoxLineType
    Wall = WallType

    # polygon
    Polygon = PolygonType
    Extruded = ExtrudedType
    Overlay = OverlayType

    Grouped = {QgsWkbTypes.PointGeometry: [SphereType, CylinderType, ConeType, BoxType, DiskType,
                                           PlaneType, PointType, IconType, ModelFileType],
               QgsWkbTypes.LineGeometry: [LineType, PipeType, ConeLineType, BoxLineType, WallType],
               QgsWkbTypes.PolygonGeometry: [PolygonType, ExtrudedType, OverlayType]
    }

    @classmethod
    def typesByGeomType(cls, geom_type):
        return cls.Grouped.get(geom_type, [])

    @classmethod
    def typeByName(cls, name, geom_type):
        for obj_type in cls.typesByGeomType(geom_type):
            if obj_type.name == name:
                return obj_type

        # for backward compatibility
        if name == "Triangular Mesh":
            return PolygonType

        if name == "Profile":
            return WallType

        return None


def tr(source):
    return source


def _():
    tr("Point"), tr("Sphere"), tr("Cylinder"), tr("Cone"), tr("Box"), tr("Disk"), tr("Plane")
    tr("Line"), tr("Pipe"), tr("Wall")
    tr("Polygon"), tr("Extruded"), tr("Overlay")
    tr("Icon"), tr("Model File")
