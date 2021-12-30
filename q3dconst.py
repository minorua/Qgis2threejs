class LayerType:
    DEM = 0
    POINT = 1
    LINESTRING = 2
    POLYGON = 3
    POINTCLOUD = 4


class DEMMtlType:
    LAYER = 0
    MAPCANVAS = 1
    FILE = 2
    COLOR = 3


# Script ID
SCRIPT_PROJ4 = 1
SCRIPT_GLTFLOADER = 2
SCRIPT_COLLADALOADER = 3
SCRIPT_GLTFEXPORTER = 4
SCRIPT_POTREE = 5
SCRIPT_PCLAYER = 6
SCRIPT_OUTLINE = 7
SCRIPT_VIEWHELPER = 8
SCRIPT_MESHLINE = 9
SCRIPT_FETCH = 101

# Script path (relative from js directory)
SCRIPT_PATH = {
    SCRIPT_PROJ4: "proj4js/proj4.js",
    SCRIPT_GLTFLOADER: "threejs/loaders/GLTFLoader.js",
    SCRIPT_COLLADALOADER: "threejs/loaders/ColladaLoader.js",
    SCRIPT_GLTFEXPORTER: "threejs/exporters/GLTFExporter.js",
    SCRIPT_POTREE: "potree-core/potree.min.js",
    SCRIPT_PCLAYER: "pointcloudlayer.js",
    SCRIPT_OUTLINE: "threejs/effects/OutlineEffect.js",
    SCRIPT_VIEWHELPER: "threejs/editor/ViewHelper.js",
    SCRIPT_MESHLINE: "meshline/THREE.MeshLine.js",
    SCRIPT_FETCH: "unfetch/unfetch.js"
}

# Layer properties
GEOM_WIDGET_MAX_COUNT = 4
MTL_WIDGET_MAX_COUNT = 2        # except for color, color2 and opacity


class PropertyID:

    ALT = 1
    ALT2 = 2

    PATH = 3

    G0 = 10
    G1 = 11
    G2 = 12
    G3 = 13

    C = 20
    C2 = 21
    OP = 22
    M0 = 23
    M1 = 24

    LBLH = 30

    PID_NAME_DICT = {
        ALT: "fieldExpressionWidget_altitude",
        ALT2: "comboEdit_altitude2",
        PATH: "comboEdit_FilePath",
        C: "comboEdit_Color",
        C2: "comboEdit_Color2",
        OP: "comboEdit_Opacity",
        LBLH: "labelHeightWidget"
    }

    @classmethod
    def init(cls):
        for i in range(GEOM_WIDGET_MAX_COUNT):
            cls.PID_NAME_DICT[cls.G0 + i] = "geomWidget" + str(i)

        for i in range(MTL_WIDGET_MAX_COUNT):
            cls.PID_NAME_DICT[cls.M0 + i] = "mtlWidget" + str(i)


PropertyID.init()
