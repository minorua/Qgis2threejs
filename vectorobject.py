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

from .q3dconst import PropertyID as PID
from .stylewidget import StyleWidget, OptionalColorWidgetFunc, ColorTextureWidgetFunc


class ObjectTypeBase:

    experimental = False

    def __init__(self, settings, mtlManager=None):
        self.settings = settings
        self.mtlManager = mtlManager        # material manager needs to be set before calling .material()

    def setupWidgets(self, ppage):
        pass

    def material(self, feat):
        pass

    def geometry(self, feat, geom):
        pass

    def defaultValue(self):
        return float("{0:.4g}".format(1.0 / self.settings.mapTo3d().multiplier))

    def defaultValueZ(self):
        return float("{0:.4g}".format(1.0 / self.settings.mapTo3d().multiplierZ))

    @classmethod
    def displayName(cls):
        return tr(cls.name)

    # def layerProperties(self, layer):
    #     return {}


class PointTypeBase(ObjectTypeBase):

    geometryType = QgsWkbTypes.PointGeometry


class LineTypeBase(ObjectTypeBase):

    geometryType = QgsWkbTypes.LineGeometry


class PolygonTypeBase(ObjectTypeBase):

    geometryType = QgsWkbTypes.PolygonGeometry


# PointBasicType
class PointBasicTypeBase(PointTypeBase):

    def material(self, feat):
        return self.mtlManager.getMeshMaterialIndex(feat.prop(PID.C), feat.prop(PID.OP))


class PointType(ObjectTypeBase):

    name = "Point"

    def setupWidgets(self, ppage):
        ppage.setupWidgets(mtlItems=[{"name": "Size", "defaultValue": 1}])

    def material(self, feat):
        return self.mtlManager.getPointMaterialIndex(feat.prop(PID.C), feat.prop(PID.OP), feat.prop(PID.M0))

    def geometry(self, feat, geom):
        v = []
        for pt in geom.toList():
            v.extend(pt)
        return {"pts": v}


class SphereType(PointBasicTypeBase):

    name = "Sphere"

    def setupWidgets(self, ppage):
        ppage.setupWidgets(geomItems=[{"name": "Radius", "defaultValue": self.defaultValue()}])

    def geometry(self, feat, geom):
        return {"pts": geom.toList(),
                "r": feat.prop(PID.G0) * self.settings.mapTo3d().multiplier}


class CylinderType(PointBasicTypeBase):

    name = "Cylinder"

    def setupWidgets(self, ppage):
        ppage.setupWidgets(geomItems=[{"name": "Radius", "defaultValue": self.defaultValue()},
                                      {"name": "Height", "defaultValue": self.defaultValueZ()}])

    def geometry(self, feat, geom):
        mapTo3d = self.settings.mapTo3d()
        r = feat.prop(PID.G0) * mapTo3d.multiplier
        return {"pts": geom.toList(),
                "r": r,
                "h": feat.prop(PID.G1) * mapTo3d.multiplierZ}


class ConeType(CylinderType):

    name = "Cone"


class BoxType(PointBasicTypeBase):

    name = "Box"

    def setupWidgets(self, ppage):
        val = self.defaultValue()

        ppage.setupWidgets(geomItems=[{"name": "Width", "defaultValue": val},
                                      {"name": "Depth", "defaultValue": val},
                                      {"name": "Height", "defaultValue": self.defaultValueZ()}])

    def geometry(self, feat, geom):
        mapTo3d = self.settings.mapTo3d()
        return {"pts": geom.toList(),
                "w": feat.prop(PID.G0) * mapTo3d.multiplier,
                "d": feat.prop(PID.G1) * mapTo3d.multiplier,
                "h": feat.prop(PID.G2) * mapTo3d.multiplierZ}


class DiskType(PointBasicTypeBase):

    name = "Disk"

    def setupWidgets(self, ppage):
        ppage.setupWidgets(geomItems=[{"name": "Radius", "defaultValue": self.defaultValue()},
                                      {"name": "Dip", "label": "Degrees", "defaultValue": 0, "label_field": None},
                                      {"name": "Dip direction", "label": "Degrees", "defaultValue": 0, "label_field": None}])

    def material(self, feat):
        return self.mtlManager.getMeshMaterialIndex(feat.prop(PID.C), feat.prop(PID.OP), doubleSide=True)

    def geometry(self, feat, geom):
        dd = feat.prop(PID.G2)
        # take map rotation into account
        rotation = self.settings.baseExtent().rotation()
        if rotation:
            dd = (dd + rotation) % 360

        return {"pts": geom.toList(),
                "r": feat.prop(PID.G0) * self.settings.mapTo3d().multiplier,
                "d": feat.prop(PID.G1),
                "dd": dd}


class PlaneType(PointBasicTypeBase):

    name = "Plane"

    def setupWidgets(self, ppage):
        ppage.setupWidgets(geomItems=[{"name": "Width", "defaultValue": self.defaultValue()},
                                      {"name": "Length", "defaultValue": self.defaultValue()},
                                      {"name": "Dip", "label": "Degrees", "defaultValue": 0, "label_field": None},
                                      {"name": "Dip direction", "label": "Degrees", "defaultValue": 0, "label_field": None}])

    def material(self, feat):
        return self.mtlManager.getMeshMaterialIndex(feat.prop(PID.C), feat.prop(PID.OP), doubleSide=True)

    def geometry(self, feat, geom):
        dd = feat.prop(PID.G3)
        # take map rotation into account
        rotation = self.settings.baseExtent().rotation()
        if rotation:
            dd = (dd + rotation) % 360

        return {"pts": geom.toList(),
                "w": feat.prop(PID.G0) * self.settings.mapTo3d().multiplier,
                "l": feat.prop(PID.G1) * self.settings.mapTo3d().multiplier,
                "d": feat.prop(PID.G2),
                "dd": dd}


# LineBasicType
class LineBasicTypeBase(LineTypeBase):

    pass


class LineType(LineBasicTypeBase):

    name = "Line"

    def setupWidgets(self, ppage):
        ppage.setupWidgets(mtlItems=[{"name": "Dashed", "type": StyleWidget.CHECKBOX}])

    def material(self, feat):
        return self.mtlManager.getLineIndex(feat.prop(PID.C), feat.prop(PID.OP), feat.prop(PID.M0))

    def geometry(self, feat, geom):
        return {"lines": geom.toList()}


class ThickLineType(LineBasicTypeBase):

    name = "Thick Line"

    def setupWidgets(self, ppage):
        ppage.setupWidgets(mtlItems=[{"name": "Thickness", "defaultValue": 1},
                                     {"name": "Dashed", "type": StyleWidget.CHECKBOX}])

    def material(self, feat):
        return self.mtlManager.getMeshLineIndex(feat.prop(PID.C), feat.prop(PID.OP), feat.prop(PID.M0), feat.prop(PID.M1))

    def geometry(self, feat, geom):
        return {"lines": geom.toList()}


class PipeType(LineBasicTypeBase):

    name = "Pipe"

    def setupWidgets(self, ppage):
        ppage.setupWidgets(geomItems=[{"name": "Radius", "defaultValue": self.defaultValue()}])

    def material(self, feat):
        return self.mtlManager.getMeshMaterialIndex(feat.prop(PID.C), feat.prop(PID.OP))

    def geometry(self, feat, geom):
        r = feat.prop(PID.G0) * self.settings.mapTo3d().multiplier
        return {"lines": geom.toList(),
                "r": r}


class ConeLineType(PipeType):

    name = "Cone"


class BoxLineType(LineBasicTypeBase):

    name = "Box"

    def setupWidgets(self, ppage):
        val = self.defaultValue()
        ppage.setupWidgets(geomItems=[{"name": "Width", "defaultValue": val},
                                      {"name": "Height", "defaultValue": val}])

    def material(self, feat):
        return self.mtlManager.getMeshMaterialIndex(feat.prop(PID.C), feat.prop(PID.OP))

    def geometry(self, feat, geom):
        multiplier = self.settings.mapTo3d().multiplier
        return {"lines": geom.toList(),
                "w": feat.prop(PID.G0) * multiplier,
                "h": feat.prop(PID.G1) * multiplier}


class WallType(LineBasicTypeBase):

    name = "Wall"

    def setupWidgets(self, ppage):
        ppage.setupWidgets(alt2=True)

    def material(self, feat):
        return self.mtlManager.getFlatMeshMaterialIndex(feat.prop(PID.C), feat.prop(PID.OP), doubleSide=True)

    def geometry(self, feat, geom):
        return {"lines": geom.toList(),
                "bh": feat.prop(PID.ALT2) * self.settings.mapTo3d().multiplierZ}


# PolygonBasicType
class PolygonBasicTypeBase(PolygonTypeBase):

    def geometry(self, feat, geom):
        return {"polygons": geom.toList2(),
                "centroids": geom.centroids}


class PolygonType(PolygonBasicTypeBase):

    """3d polygon support: yes"""

    name = "Polygon"

    def setupWidgets(self, ppage):
        ppage.setupWidgets()

    def material(self, feat):
        return self.mtlManager.getFlatMeshMaterialIndex(feat.prop(PID.C), feat.prop(PID.OP), True)

    def geometry(self, feat, geom):
        g = geom.toDict(flat=True)
        return g


class ExtrudedType(PolygonBasicTypeBase):

    """3d polygon support: no"""

    name = "Extruded"

    def setupWidgets(self, ppage):
        ppage.setupWidgets(geomItems=[{"name": "Height", "defaultValue": self.defaultValueZ()}],
                           color2={"name": "Edge color",
                                   "itemText": {OptionalColorWidgetFunc.NONE: "(No Edge)"},
                                   "defaultValue": OptionalColorWidgetFunc.NONE})

    def material(self, feat):
        mtl = {"face": self.mtlManager.getMeshMaterialIndex(feat.prop(PID.C), feat.prop(PID.OP))}

        # edges
        if feat.prop(PID.C2) != OptionalColorWidgetFunc.NONE:
            mtl["edge"] = self.mtlManager.getLineIndex(feat.prop(PID.C2), feat.prop(PID.OP))
        return mtl

    def geometry(self, feat, geom):
        g = PolygonBasicTypeBase.geometry(feat, geom)
        g["h"] = feat.prop(PID.G0) * self.settings.mapTo3d().multiplierZ
        return g


class OverlayType(PolygonBasicTypeBase):

    """3d polygon support: no"""

    name = "Overlay"

    def setupWidgets(self, ppage):
        ppage.setupWidgets(color2={"name": "Border color",
                                   "itemText": {OptionalColorWidgetFunc.NONE: "(No border)"},
                                   "defaultValue": OptionalColorWidgetFunc.NONE})

    def material(self, feat):
        mtl = {"face": self.mtlManager.getMeshMaterialIndex(feat.prop(PID.C), feat.prop(PID.OP), True)}

        # border
        if feat.prop(PID.C2) != OptionalColorWidgetFunc.NONE:
            mtl["brdr"] = self.mtlManager.getLineIndex(feat.prop(PID.C2), feat.prop(PID.OP))
        return mtl

    def geometry(self, feat, geom):
        g = geom.toDict(flat=True)  # TINGeometry

        # border
        if feat.prop(PID.C2) != OptionalColorWidgetFunc.NONE:
            g["brdr"] = [bnds.toList(flat=True) for bnds in geom.bnds_list]

        return g


# IconType
class IconType(PointTypeBase):

    name = "Icon"

    def setupWidgets(self, ppage):
        filterString = "Images (*.png *.jpg *.gif *.bmp);;All files (*.*)"

        ppage.setupWidgets(filepath={"name": "Image file", "filterString": filterString, "allowURL": True},
                           geomItems=[{"name": "Scale", "defaultValue": 1}],
                           color=False)

    def material(self, feat):
        if feat.prop(PID.PATH):
            return self.mtlManager.getSpriteImageIndex(feat.prop(PID.PATH), feat.prop(PID.OP))
        return None

    def geometry(self, feat, geom):
        return {"pts": geom.toList(),
                "scale": feat.prop(PID.G0)}


# ModelFileType
class ModelFileType(PointTypeBase):

    name = "Model File"
    experimental = True

    def __init__(self, settings, modelManager=None):
        PointTypeBase.__init__(self, settings)
        self.modelManager = modelManager

    def setupWidgets(self, ppage):
        filterString = "Model files (*.dae *.gltf *.glb);;All files (*.*)"

        ppage.setupWidgets(filepath={"name": "Model file", "filterString": filterString, "allowURL": True},
                           geomItems=[{"name": "Scale", "defaultValue": 1},
                                      {"name": "Rotation (x)", "label": "Degrees", "defaultValue": 0},
                                      {"name": "Rotation (y)", "label": "Degrees", "defaultValue": 0},
                                      {"name": "Rotation (z)", "label": "Degrees", "defaultValue": 0},
                                      {"name": "Rotation order", "defaultValue": "XYZ", "items": ["XYZ", "XZY", "YXZ", "YZX", "ZXY", "ZYX"]}],
                           color=False,
                           opacity=False)

    def model(self, feat):
        if feat.prop(PID.PATH):
            return self.modelManager.modelIndex(feat.prop(PID.PATH))
        return None

    def geometry(self, feat, geom):
        rz = feat.prop(PID.G3)
        # take map rotation into account
        rotation = self.settings.baseExtent().rotation()
        if rotation:
            rz = (rz - rotation) % 360    # map rotation is clockwise

        d = {"pts": geom.toList(),
             "rotateX": feat.prop(PID.G1),
             "rotateY": feat.prop(PID.G2),
             "rotateZ": rz,
             "scale": feat.prop(PID.G0) * self.settings.mapTo3d().multiplier}

        if feat.prop(PID.G4) != "XYZ":    # added in 2.4
            d["rotateO"] = feat.prop(PID.G4)
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
    ThickLine = ThickLineType
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
               QgsWkbTypes.LineGeometry: [LineType, ThickLineType, PipeType, ConeLineType, BoxLineType, WallType],
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
    tr("Line"), tr("Thick Line"), tr("Pipe"), tr("Wall")
    tr("Polygon"), tr("Extruded"), tr("Overlay")
    tr("Icon"), tr("Model File")
