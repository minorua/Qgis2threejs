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


class Script:

    # Script ID
    PROJ4 = 1
    GLTFLOADER = 2
    COLLADALOADER = 3
    GLTFEXPORTER = 4
    POTREE = 5
    PCLAYER = 6
    OUTLINE = 7
    VIEWHELPER = 8
    MESHLINE = 9
    FETCH = 101

    # Script path (relative from js directory)
    PATH = {
        PROJ4: "proj4js/proj4.js",
        GLTFLOADER: "threejs/loaders/GLTFLoader.js",
        COLLADALOADER: "threejs/loaders/ColladaLoader.js",
        GLTFEXPORTER: "threejs/exporters/GLTFExporter.js",
        POTREE: "potree-core/potree.min.js",
        PCLAYER: "pointcloudlayer.js",
        OUTLINE: "threejs/effects/OutlineEffect.js",
        VIEWHELPER: "threejs/editor/ViewHelper.js",
        MESHLINE: "meshline/THREE.MeshLine.js",
        FETCH: "unfetch/unfetch.js"
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
