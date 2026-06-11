# -*- coding: utf-8 -*-
# (C) 2018 Minoru Akagi
# SPDX-License-Identifier: GPL-2.0-or-later

from PyQt6.QtCore import Qt


class LayerType:
    """Enum for layer type in this plugin"""
    DEM = 0
    POINT = 1
    LINESTRING = 2
    POLYGON = 3
    POINTCLOUD = 4


class DEMMtlType:
    """Enum for DEM material"""
    MAPCANVAS = 0
    LAYER = 1
    FILE = 2
    COLOR = 3

    # paths to icon files
    ICON_PATHS = {
        MAPCANVAS: "mLayoutItemMap.svg",
        LAYER: "algorithms/mAlgorithmMergeLayers.svg",
        FILE: "mLayoutItemPicture.svg"
    }


class ScriptFile:
    """Enum for JavaScript files"""
    GLTFLOADER = 1
    COLLADALOADER = 2
    OUTLINE = 4
    VIEWHELPER = 5
    BUFGEOMUTILS = 6
    PROJ4 = 10
    POTREE = 11
    MESHLINE = 12
    PCLAYER = 101
    TEST = 102

    # type
    TYPE_NON_MODULE = 0
    TYPE_CLASS = 1
    TYPE_UTILS = 2

    # relative paths to script files from js directory
    THREE_DIR = "lib/threejs"
    FILES = {
        GLTFLOADER: (THREE_DIR + "/loaders/GLTFLoader.js", TYPE_CLASS),
        COLLADALOADER: (THREE_DIR + "/loaders/ColladaLoader.js", TYPE_CLASS),
        OUTLINE: (THREE_DIR + "/effects/OutlineEffect.js", TYPE_CLASS),
        VIEWHELPER: (THREE_DIR + "/helpers/ViewHelper.js", TYPE_CLASS),
        BUFGEOMUTILS: (THREE_DIR + "/utils/BufferGeometryUtils.js", TYPE_UTILS),
        PROJ4: ("lib/proj4js/proj4.js", TYPE_NON_MODULE),
        POTREE: ("lib/potree-core/potree.min.js", TYPE_NON_MODULE),
        MESHLINE: ("lib/meshline/THREE.MeshLine.js", TYPE_NON_MODULE),
        PCLAYER: ("pointcloudlayer.js", TYPE_NON_MODULE),
        TEST: ("../../tests/gui/test.js", TYPE_NON_MODULE)
    }


# Layer properties
GEOM_WIDGET_MAX_COUNT = 5
MTL_WIDGET_MAX_COUNT = 2        # excluding color, color2 and opacity


class PropertyID:
    """Enum for property widgets"""
    ALT = 1
    ALT2 = 2

    PATH = 3

    G0 = 10
    G1 = 11
    G2 = 12
    G3 = 13
    G4 = 14

    C = 20
    C2 = 21
    OP = 22

    M0 = 23
    M1 = 24

    LBLH = 30
    LBLTXT = 31

    # widget name
    PID_NAME_DICT = {
        ALT: "fieldExpressionWidget_altitude",
        ALT2: "comboEdit_altitude2",
        PATH: "comboEdit_FilePath",
        C: "comboEdit_Color",
        C2: "comboEdit_Color2",
        OP: "comboEdit_Opacity",
        LBLH: "labelHeightWidget",
        LBLTXT: "expression_Label"
    }

    # enum for animation
    DLY = 80
    DUR = 81

    @classmethod
    def init(cls):
        for i in range(GEOM_WIDGET_MAX_COUNT):
            cls.PID_NAME_DICT[cls.G0 + i] = "geomWidget" + str(i)

        for i in range(MTL_WIDGET_MAX_COUNT):
            cls.PID_NAME_DICT[cls.M0 + i] = "mtlWidget" + str(i)


PropertyID.init()


class ATConst:
    """Enum for animation tree widget"""
    # ITEM TYPES

    # TOP LEVEL
    ITEM_TOPLEVEL = 32
    ITEM_TL_CAMERA = 32
    ITEM_TL_LAYER = 33

    # TRACK
    ITEM_TRK = 64

    ITEM_TRK_CAMERA = 64
    ITEM_TRK_OPACITY = 65
    ITEM_TRK_TEXTURE = 66
    ITEM_TRK_GROWING_LINE = 67

    # ITEM TYPE (MEMBER OF TRACK. KEYFRAME OR EFFECT)
    ITEM_MBR = 128

    ITEM_CAMERA = 128
    ITEM_OPACITY = 129
    ITEM_TEXTURE = 130
    ITEM_GROWING_LINE = 131         # EFFECT

    # ITEM_TL_LAYER
    DATA_LAYER_ID = Qt.ItemDataRole.UserRole

    # TRACK
    DATA_NEXT_INDEX = Qt.ItemDataRole.UserRole

    # COMMON FOR KEYFRAME
    DATA_EASING = Qt.ItemDataRole.UserRole + 1
    DATA_DURATION = Qt.ItemDataRole.UserRole + 2
    DATA_DELAY = Qt.ItemDataRole.UserRole + 3
    DATA_NARRATION = Qt.ItemDataRole.UserRole + 4

    # CAMERA KEYFRAME
    DATA_CAMERA = Qt.ItemDataRole.UserRole

    # OPACITY KEYFRAME
    DATA_OPACITY = Qt.ItemDataRole.UserRole

    # TEXTURE KEYFRAME
    DATA_MTL_ID = Qt.ItemDataRole.UserRole
    DATA_EFFECT = Qt.ItemDataRole.UserRole + 5

    # LINE GROWING EFFECT
    DATA_SEQ = Qt.ItemDataRole.UserRole

    # EASING
    EASING_NONE = 0
    EASING_LINEAR = 1
    EASING_EASE_INOUT = 2
    EASING_EASE_IN = 3
    EASING_EASE_OUT = 4

    @classmethod
    def defaultName(cls, typ):
        name = ["Camera", "Opacity", "Texture", "Growing line"]
        if typ & cls.ITEM_TRK:
            return "Track" if typ == cls.ITEM_TRK_CAMERA else "{} track".format(name[typ - cls.ITEM_TRK])

        if typ & cls.ITEM_MBR:
            return "{} keyframe".format(name[typ - cls.ITEM_MBR])

        return "UNDEF"
