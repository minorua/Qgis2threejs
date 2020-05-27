# Layer geometry type
TYPE_DEM = 0
TYPE_POINT = 1
TYPE_LINESTRING = 2
TYPE_POLYGON = 3
TYPE_POINTCLOUD = 4

# Script ID
SCRIPT_PROJ4 = 1
SCRIPT_GLTFLOADER = 2
SCRIPT_COLLADALOADER = 3
SCRIPT_GLTFEXPORTER = 4
SCRIPT_POTREE = 5
SCRIPT_PCLAYER = 6

# Script path (relative from js directory)
SCRIPT_PATH = {
    SCRIPT_PROJ4: "proj4js/proj4.js",
    SCRIPT_GLTFLOADER: "threejs/loaders/GLTFLoader.js",
    SCRIPT_COLLADALOADER: "threejs/loaders/ColladaLoader.js",
    SCRIPT_GLTFEXPORTER: "threejs/exporters/GLTFExporter.js",
    SCRIPT_POTREE: "potree-core/potree.min.js",
    SCRIPT_PCLAYER: "pointcloudlayer.js"

}
