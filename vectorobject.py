# -*- coding: utf-8 -*-
# (C) 2014 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later
# begin: 2014-01-11

from .q3dconst import LayerType, PropertyID as PID
from .propwidget import PropertyWidget, WVT


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
        return float("{0:.3g}".format(self.settings.baseExtent().width() * 0.01))

    def defaultValueZ(self):
        return float("{0:.3g}".format(self.settings.baseExtent().width() * self.settings.mapTo3d().zScale * 0.01))

    @classmethod
    def displayName(cls):
        return tr(cls.name)

    # def layerProperties(self, layer):
    #     return {}


class PointTypeBase(ObjectTypeBase):

    layerType = LayerType.POINT


class LineTypeBase(ObjectTypeBase):

    layerType = LayerType.LINESTRING


class PolygonTypeBase(ObjectTypeBase):

    layerType = LayerType.POLYGON


# Point
class PointBasicTypeBase(PointTypeBase):

    def material(self, feat):
        return self.mtlManager.getMeshMaterialIndex(feat.prop(PID.C), feat.prop(PID.OP))


class PointType(PointTypeBase):

    name = "Point"

    def setupWidgets(self, ppage):
        ppage.setupWidgets(mtlItems=[{"name": "Size", "defVal": 1}])

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
        ppage.setupWidgets(geomItems=[{"name": "Radius", "defVal": self.defaultValue()}])

    def geometry(self, feat, geom):
        return {"pts": geom.toList(),
                "r": feat.prop(PID.G0)}


class CylinderType(PointBasicTypeBase):

    name = "Cylinder"

    def setupWidgets(self, ppage):
        ppage.setupWidgets(geomItems=[{"name": "Radius", "defVal": self.defaultValue()},
                                      {"name": "Height", "defVal": self.defaultValueZ()}])

    def geometry(self, feat, geom):
        r = feat.prop(PID.G0)
        return {"pts": geom.toList(),
                "r": r,
                "h": feat.prop(PID.G1) * self.settings.mapTo3d().zScale}


class ConeType(CylinderType):

    name = "Cone"


class BoxType(PointBasicTypeBase):

    name = "Box"

    def setupWidgets(self, ppage):
        val = self.defaultValue()

        ppage.setupWidgets(geomItems=[{"name": "Width", "defVal": val},
                                      {"name": "Depth", "defVal": val},
                                      {"name": "Height", "defVal": self.defaultValueZ()}])

    def geometry(self, feat, geom):
        return {"pts": geom.toList(),
                "w": feat.prop(PID.G0),
                "d": feat.prop(PID.G1),
                "h": feat.prop(PID.G2) * self.settings.mapTo3d().zScale}


class DiskType(PointTypeBase):

    name = "Disk"

    def setupWidgets(self, ppage):
        ppage.setupWidgets(geomItems=[{"name": "Radius", "defVal": self.defaultValue()},
                                      {"name": "Dip", "label": "Degrees", "valType": WVT.ANGLE, "defVal": 0, "label_field": None},
                                      {"name": "Dip direction", "label": "Degrees", "valType": WVT.ANGLE, "defVal": 0, "label_field": None}])

    def material(self, feat):
        return self.mtlManager.getMeshMaterialIndex(feat.prop(PID.C), feat.prop(PID.OP), doubleSide=True)

    def geometry(self, feat, geom):
        dd = feat.prop(PID.G2)
        # take map rotation into account
        rotation = self.settings.baseExtent().rotation()
        if rotation:
            dd = (dd + rotation) % 360

        return {"pts": geom.toList(),
                "r": feat.prop(PID.G0),
                "d": feat.prop(PID.G1),
                "dd": dd}


class PlaneType(PointTypeBase):

    name = "Plane"

    def setupWidgets(self, ppage):
        val = self.defaultValue()
        ppage.setupWidgets(geomItems=[{"name": "Width", "defVal": val},
                                      {"name": "Length", "defVal": val},
                                      {"name": "Dip", "label": "Degrees", "valType": WVT.ANGLE, "defVal": 0, "label_field": None},
                                      {"name": "Dip direction", "label": "Degrees", "valType": WVT.ANGLE, "defVal": 0, "label_field": None}])

    def material(self, feat):
        return self.mtlManager.getMeshMaterialIndex(feat.prop(PID.C), feat.prop(PID.OP), doubleSide=True)

    def geometry(self, feat, geom):
        dd = feat.prop(PID.G3)
        # take map rotation into account
        rotation = self.settings.baseExtent().rotation()
        if rotation:
            dd = (dd + rotation) % 360

        return {"pts": geom.toList(),
                "w": feat.prop(PID.G0),
                "l": feat.prop(PID.G1),
                "d": feat.prop(PID.G2),
                "dd": dd}


# Line
class LineType(LineTypeBase):

    name = "Line"

    def setupWidgets(self, ppage):
        ppage.setupWidgets(mtlItems=[{"name": "Dashed", "type": PropertyWidget.CHECKBOX}])

    def material(self, feat):
        return self.mtlManager.getLineIndex(feat.prop(PID.C), feat.prop(PID.OP), feat.prop(PID.M0))

    def geometry(self, feat, geom):
        return {"lines": geom.toList(flat=True)}


class ThickLineType(LineTypeBase):

    name = "Thick Line"

    def setupWidgets(self, ppage):
        ppage.setupWidgets(mtlItems=[{"name": "Thickness", "defVal": 1},
                                     {"name": "Dashed", "type": PropertyWidget.CHECKBOX}])

    def material(self, feat):
        return self.mtlManager.getMeshLineIndex(feat.prop(PID.C), feat.prop(PID.OP), feat.prop(PID.M0), feat.prop(PID.M1))

    def geometry(self, feat, geom):
        return {"lines": geom.toList(flat=True)}


class PipeType(LineTypeBase):

    name = "Pipe"

    def setupWidgets(self, ppage):
        ppage.setupWidgets(geomItems=[{"name": "Radius", "defVal": self.defaultValue()}])

    def material(self, feat):
        return self.mtlManager.getMeshMaterialIndex(feat.prop(PID.C), feat.prop(PID.OP))

    def geometry(self, feat, geom):
        r = feat.prop(PID.G0)
        return {"lines": geom.toList(),
                "r": r}


class ConeLineType(PipeType):

    name = "Cone"


class BoxLineType(LineTypeBase):

    name = "Box"

    def setupWidgets(self, ppage):
        val = self.defaultValue()
        ppage.setupWidgets(geomItems=[{"name": "Width", "defVal": val},
                                      {"name": "Height", "defVal": val}])

    def material(self, feat):
        return self.mtlManager.getMeshMaterialIndex(feat.prop(PID.C), feat.prop(PID.OP))

    def geometry(self, feat, geom):
        return {"lines": geom.toList(),
                "w": feat.prop(PID.G0),
                "h": feat.prop(PID.G1)}


class WallType(LineTypeBase):

    name = "Wall"

    def setupWidgets(self, ppage):
        ppage.setupWidgets(alt2=True)

    def material(self, feat):
        return self.mtlManager.getMeshFlatMaterialIndex(feat.prop(PID.C), feat.prop(PID.OP), doubleSide=True)

    def geometry(self, feat, geom):
        return {"lines": geom.toList(flat=True),
                "bh": feat.prop(PID.ALT2) * self.settings.mapTo3d().zScale}


# Polygon
class PolygonType(PolygonTypeBase):

    """3d polygon support: yes"""

    name = "Polygon"

    def setupWidgets(self, ppage):
        ppage.setupWidgets()

    def material(self, feat):
        return self.mtlManager.getMeshFlatMaterialIndex(feat.prop(PID.C), feat.prop(PID.OP), True)

    def geometry(self, feat, geom):
        g = geom.toDict(flat=True)
        return g


class ExtrudedType(PolygonTypeBase):

    """3d polygon support: no"""

    name = "Extruded"

    def setupWidgets(self, ppage):
        ppage.setupWidgets(geomItems=[{"name": "Height", "defVal": self.defaultValueZ()}],
                           color2={"name": "Edge color",
                                   "itemText": {None: "No edge"},
                                   "defVal": None})

    def material(self, feat):
        mtl = {"face": self.mtlManager.getMeshMaterialIndex(feat.prop(PID.C), feat.prop(PID.OP))}

        # edges
        if feat.prop(PID.C2) is not None:
            mtl["edge"] = self.mtlManager.getLineIndex(feat.prop(PID.C2), feat.prop(PID.OP))
        return mtl

    def geometry(self, feat, geom):
        return {
            "polygons": geom.toList2(),
            "centroids": geom.centroids,
            "h": feat.prop(PID.G0) * self.settings.mapTo3d().zScale
        }


class OverlayType(PolygonTypeBase):

    """3d polygon support: no"""

    name = "Overlay"

    def setupWidgets(self, ppage):
        ppage.setupWidgets(color2={"name": "Border color",
                                   "itemText": {None: "No border"},
                                   "defVal": None})

    def material(self, feat):
        mtl = {"face": self.mtlManager.getMeshMaterialIndex(feat.prop(PID.C), feat.prop(PID.OP), True)}

        # border
        if feat.prop(PID.C2) is not None:
            mtl["brdr"] = self.mtlManager.getLineIndex(feat.prop(PID.C2), feat.prop(PID.OP))
        return mtl

    def geometry(self, feat, geom):
        g = geom.toDict(flat=True)  # TINGeometry

        # border
        if feat.prop(PID.C2) is not None:
            g["brdr"] = [bnds.toList(flat=True) for bnds in geom.bnds_list]

        return g


# IconType
class IconType(PointTypeBase):

    name = "Icon"

    def setupWidgets(self, ppage):
        filterString = "Images (*.png *.jpg *.gif *.bmp);;All files (*.*)"

        ppage.setupWidgets(filepath={"name": "Image file", "filterString": filterString, "allowURL": True},
                           geomItems=[{"name": "Scale", "valType": WVT.OTHERS, "defVal": 1}],
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
                           geomItems=[{"name": "Scale", "defVal": 1},
                                      {"name": "Rotation (x)", "label": "Degrees", "valType": WVT.ANGLE, "defVal": 0},
                                      {"name": "Rotation (y)", "label": "Degrees", "valType": WVT.ANGLE, "defVal": 0},
                                      {"name": "Rotation (z)", "label": "Degrees", "valType": WVT.ANGLE, "defVal": 0},
                                      {"name": "Rotation order", "type": PropertyWidget.COMBOBOX,
                                       "defVal": "XYZ", "items": ["XYZ", "XZY", "YXZ", "YZX", "ZXY", "ZYX"]}],
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
             "scale": feat.prop(PID.G0)}

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

    Grouped = {LayerType.POINT: [SphereType, CylinderType, ConeType, BoxType, DiskType,
                                 PlaneType, PointType, IconType, ModelFileType],
               LayerType.LINESTRING: [LineType, ThickLineType, PipeType, ConeLineType, BoxLineType, WallType],
               LayerType.POLYGON: [PolygonType, ExtrudedType, OverlayType]
               }

    @classmethod
    def typesByGeomType(cls, geom_type):
        return cls.Grouped.get(geom_type, [])

    @classmethod
    def typeByName(cls, name, geom_type):
        for obj_type in cls.typesByGeomType(geom_type):
            if obj_type.name == name:
                return obj_type
        return None


def tr(source):
    return source


# def _():
#     tr("Point")
