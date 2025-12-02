# -*- coding: utf-8 -*-
# (C) 2014 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later
# begin: 2014-01-11

from ...const import LayerType, PropertyID as PID
from ....gui.propwidget import PropertyWidget, WVT


class ObjectTypeBase:
    """Base class for all 3D object types.

    This is the abstract base class for various types of 3D objects.
    Subclasses are expected to implement methods that provide material and geometry data for each feature.
    """

    experimental = False

    def __init__(self, settings, mtlManager=None):
        """
        Args:
            settings: ExportSettings object
            mtlManager: MaterialManager object (optional)
                Note: mtlManager needs to be set before calling .material()
        """
        self.settings = settings
        self.mtlManager = mtlManager

    def setupWidgets(self, ppage):
        """Setup UI widgets for object type properties.

        This method is called to configure the property widgets displayed in the UI
        for this object type. Subclasses should override this to define custom properties.

        Args:
            ppage: VectorPropertyPage widget to setup
        """
        pass

    def material(self, feat):
        """Get material properties for a feature.

        This method should return a dictionary containing material information for the given feature.
        The material manager is used to avoid generating duplicate materials.

        Args:
            feat: Feature object

        Returns:
            A dictionary with material properties (e.g., {"idx": material_index}), where idx is
            the unique material index obtained from MaterialManager
        """
        pass

    def geometry(self, feat, geom):
        """Get 3D geometry data for a feature.

        This method should return a dictionary containing geometry data for the given feature.

        Args:
            feat: Feature object
            geom: VectorGeometry subclass object

        Returns:
            A dictionary with geometry data (e.g., {"pts": [[0, 0, 0], [10, 10, 10]], "r": 5})
        """
        pass

    def defaultValue(self):
        """Get default size value.

        Calculates a reasonable default value for geometry properties like radius or width.

        Returns:
            Float value as default size
        """
        return float("{0:.3g}".format(self.settings.baseExtent().width() * 0.01))

    def defaultValueZ(self):
        """Get default height value

        Calculates a reasonable default value for height properties, taking into account
        the z-scale factor and map extent.

        Returns:
            Float value as default height
        """
        return float("{0:.3g}".format(self.settings.baseExtent().width() * self.settings.mapTo3d().zScale * 0.01))

    @classmethod
    def displayName(cls):
        """Get the display name of the object type."""
        return tr(cls.name)


class PointTypeBase(ObjectTypeBase):

    layerType = LayerType.POINT


class LineTypeBase(ObjectTypeBase):

    layerType = LayerType.LINESTRING


class PolygonTypeBase(ObjectTypeBase):

    layerType = LayerType.POLYGON


# Point
class PointBasicTypeBase(PointTypeBase):

    def material(self, feat):
        return {"idx": self.mtlManager.getMeshMaterialIndex(feat.prop(PID.C), feat.prop(PID.OP))}


class PointType(PointTypeBase):

    name = "Point"
    pids = [PID.C, PID.OP, PID.M0]

    def setupWidgets(self, ppage):
        ppage.setupWidgets(mtlItems=[{"name": "Size", "defVal": 1}])

    def material(self, feat):
        return {"idx": self.mtlManager.getPointMaterialIndex(feat.prop(PID.C), feat.prop(PID.OP), feat.prop(PID.M0))}

    def geometry(self, feat, geom):
        v = []
        for pt in geom.toList():
            v.extend(pt)
        return {"pts": v}


class SphereType(PointBasicTypeBase):

    name = "Sphere"
    pids = [PID.C, PID.OP, PID.G0]

    def setupWidgets(self, ppage):
        ppage.setupWidgets(geomItems=[{"name": "Radius", "defVal": self.defaultValue()}])

    def geometry(self, feat, geom):
        return {"pts": geom.toList(),
                "r": feat.prop(PID.G0)}


class CylinderType(PointBasicTypeBase):

    name = "Cylinder"
    pids = [PID.C, PID.OP, PID.G0, PID.G1]

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
    pids = [PID.C, PID.OP, PID.G0, PID.G1, PID.G2]

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
    pids = [PID.C, PID.OP, PID.G0, PID.G1, PID.G2]

    def setupWidgets(self, ppage):
        ppage.setupWidgets(geomItems=[{"name": "Radius", "defVal": self.defaultValue()},
                                      {"name": "Dip", "label": "Degrees", "valType": WVT.ANGLE, "defVal": 0, "label_field": None},
                                      {"name": "Dip direction", "label": "Degrees", "valType": WVT.ANGLE, "defVal": 0, "label_field": None}])

    def material(self, feat):
        return {"idx": self.mtlManager.getMeshMaterialIndex(feat.prop(PID.C), feat.prop(PID.OP), doubleSide=True)}

    def geometry(self, feat, geom):
        return {"pts": geom.toList(),
                "r": feat.prop(PID.G0),
                "d": feat.prop(PID.G1),
                "dd": feat.prop(PID.G2)}


class PlaneType(PointTypeBase):

    name = "Plane"
    pids = [PID.C, PID.OP, PID.G0, PID.G1, PID.G2, PID.G3]

    def setupWidgets(self, ppage):
        val = self.defaultValue()
        ppage.setupWidgets(geomItems=[{"name": "Width", "defVal": val},
                                      {"name": "Length", "defVal": val},
                                      {"name": "Dip", "label": "Degrees", "valType": WVT.ANGLE, "defVal": 0, "label_field": None},
                                      {"name": "Dip direction", "label": "Degrees", "valType": WVT.ANGLE, "defVal": 0, "label_field": None}])

    def material(self, feat):
        return {"idx": self.mtlManager.getMeshMaterialIndex(feat.prop(PID.C), feat.prop(PID.OP), doubleSide=True)}

    def geometry(self, feat, geom):
        return {"pts": geom.toList(),
                "w": feat.prop(PID.G0),
                "l": feat.prop(PID.G1),
                "d": feat.prop(PID.G2),
                "dd": feat.prop(PID.G3)}


# Line
class LineType(LineTypeBase):

    name = "Line"
    pids = [PID.C, PID.OP, PID.M0]

    def setupWidgets(self, ppage):
        ppage.setupWidgets(mtlItems=[{"name": "Dashed", "type": PropertyWidget.CHECKBOX}])

    def material(self, feat):
        return {"idx": self.mtlManager.getLineIndex(feat.prop(PID.C), feat.prop(PID.OP), feat.prop(PID.M0))}

    def geometry(self, feat, geom):
        return {"lines": geom.toList(flat=True)}


class ThickLineType(LineTypeBase):

    name = "Thick Line"
    pids = [PID.C, PID.OP, PID.M0, PID.M1]

    def setupWidgets(self, ppage):
        ppage.setupWidgets(mtlItems=[{"name": "Thickness", "defVal": 1},
                                     {"name": "Dashed", "type": PropertyWidget.CHECKBOX}])

    def material(self, feat):
        return {"idx": self.mtlManager.getMeshLineIndex(feat.prop(PID.C), feat.prop(PID.OP), feat.prop(PID.M0), feat.prop(PID.M1))}

    def geometry(self, feat, geom):
        return {"lines": geom.toList(flat=True)}


class PipeType(LineTypeBase):

    name = "Pipe"
    pids = [PID.C, PID.OP, PID.G0]

    def setupWidgets(self, ppage):
        ppage.setupWidgets(geomItems=[{"name": "Radius", "defVal": self.defaultValue()}])

    def material(self, feat):
        return {"idx": self.mtlManager.getMeshMaterialIndex(feat.prop(PID.C), feat.prop(PID.OP))}

    def geometry(self, feat, geom):
        r = feat.prop(PID.G0)
        return {"lines": geom.toList(),
                "r": r}


class ConeLineType(PipeType):

    name = "Cone"


class BoxLineType(LineTypeBase):

    name = "Box"
    pids = [PID.C, PID.OP, PID.G0, PID.G1]

    def setupWidgets(self, ppage):
        val = self.defaultValue()
        ppage.setupWidgets(geomItems=[{"name": "Width", "defVal": val},
                                      {"name": "Height", "defVal": val}])

    def material(self, feat):
        return {"idx": self.mtlManager.getMeshMaterialIndex(feat.prop(PID.C), feat.prop(PID.OP))}

    def geometry(self, feat, geom):
        return {"lines": geom.toList(),
                "w": feat.prop(PID.G0),
                "h": feat.prop(PID.G1)}


class WallType(LineTypeBase):

    name = "Wall"
    pids = [PID.C, PID.OP, PID.ALT2]

    def setupWidgets(self, ppage):
        ppage.setupWidgets(alt2=True)

    def material(self, feat):
        return {"idx": self.mtlManager.getMeshFlatMaterialIndex(feat.prop(PID.C), feat.prop(PID.OP), doubleSide=True)}

    def geometry(self, feat, geom):
        return {"lines": geom.toList(flat=True),
                "bh": feat.prop(PID.ALT2) * self.settings.mapTo3d().zScale}


# Polygon
class PolygonType(PolygonTypeBase):

    """3d polygon support: yes"""

    name = "Polygon"
    pids = [PID.C, PID.OP]

    def setupWidgets(self, ppage):
        ppage.setupWidgets()

    def material(self, feat):
        return {"idx": self.mtlManager.getMeshFlatMaterialIndex(feat.prop(PID.C), feat.prop(PID.OP), True)}

    def geometry(self, feat, geom):
        g = geom.toDict(flat=True)
        return g


class ExtrudedType(PolygonTypeBase):

    """3d polygon support: no"""

    name = "Extruded"
    pids = [PID.C, PID.C2, PID.OP, PID.G0]

    def setupWidgets(self, ppage):
        ppage.setupWidgets(geomItems=[{"name": "Height", "defVal": self.defaultValueZ()}],
                           color2={"name": "Edge color",
                                   "itemText": {None: "No edge"},
                                   "defVal": None})

    def material(self, feat):
        mtl = {"idx": self.mtlManager.getMeshMaterialIndex(feat.prop(PID.C), feat.prop(PID.OP))}

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
    pids = [PID.C, PID.C2, PID.OP]

    def setupWidgets(self, ppage):
        ppage.setupWidgets(color2={"name": "Border color",
                                   "itemText": {None: "No border"},
                                   "defVal": None})

    def material(self, feat):
        mtl = {"idx": self.mtlManager.getMeshMaterialIndex(feat.prop(PID.C), feat.prop(PID.OP), True)}

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


# BillboardType
class BillboardType(PointTypeBase):

    name = "Billboard"
    pids = [PID.PATH, PID.OP, PID.G0]

    def setupWidgets(self, ppage):
        filterString = "Images (*.png *.jpg *.gif *.bmp);;All files (*.*)"

        ppage.setupWidgets(filepath={"name": "Image file", "filterString": filterString, "allowURL": True},
                           geomItems=[{"name": "Size", "valType": WVT.OTHERS, "defVal": 1}],
                           color=False)

    def material(self, feat):
        if feat.prop(PID.PATH):
            return {"idx": self.mtlManager.getSpriteImageIndex(feat.prop(PID.PATH), feat.prop(PID.OP))}
        return None

    def geometry(self, feat, geom):
        return {"pts": geom.toList(),
                "size": feat.prop(PID.G0)}


# ModelFileType
class ModelFileType(PointTypeBase):

    name = "3D Model"
    pids = [PID.PATH, PID.G0, PID.G1, PID.G2, PID.G3, PID.G4]
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
        d = {"pts": geom.toList(),
             "rotateX": feat.prop(PID.G1),
             "rotateY": feat.prop(PID.G2),
             "rotateZ": feat.prop(PID.G3),
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
    Billboard = BillboardType
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
                                 PlaneType, PointType, BillboardType, ModelFileType],
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
