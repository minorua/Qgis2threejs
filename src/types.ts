/*
These type definitions are incomplete and may contain inaccuracies

TODO:
 - Definition of coordinates for points, linestrings and polygons
*/
import type * as THREE from "three";

import type { LayerType, MaterialType } from "./core.js";
import type { Scene } from "./scene.js";
export type { LayerType, MaterialType };

//// Data structures loaded into the application
export interface Point2 {
    x: number;
    y: number;
}

export interface Point3 {
    x: number;
    y: number;
    z: number;
}

export type Vec3 = [number, number, number];

export interface BaseExtent {
    cx: number;
    cy: number;
    width: number;
    height: number;
    rotation: number;
}

/* Properties */
export interface SceneProperties {
	baseExtent: BaseExtent;	 // map base extent in map coordinates. center is (cx, cy).
	origin: Point3;		     // origin of 3D world in map coordinates
	zScale: number;			 // vertical scale factor
    light: string;
    fog?: {
        color: number;
        density: number;
    };
    proj?: string;           // used for lat/lon display
}

export interface LayerProperties {
    type: LayerType;
    name: string;
    clickable: boolean;
    visible: boolean;
}

export interface DEMLayerProperties extends LayerProperties {
    type: "dem";
    clipped: boolean;
    tiled: boolean;
    mtlNames: string[];
    mtlIdx: number;
    sides?: {
        mtl: MaterialData;
        bottom: number;
    };
    edges?: {
        mtl: MaterialData;
    };
    wireframe?: {
        mtl: MaterialData;
    };
}

export interface VectorLayerProperties extends LayerProperties {
    type: "point" | "line" | "polygon";
    objType: string;
    propertyNames?: string[];
    label?: {
        relative?: boolean;
        font?: string;
        size?: number;
        color?: string;
        olcolor?: string;
        bgcolor?: string;
        cncolor?: number;
        underline?: boolean;
    };
}

/* Data */
interface BaseData {
    type: string;
}

/* Scene */
export interface SceneData extends BaseData {
    type: "scene";
    properties: SceneProperties;
    layers?: LayerData[];   // export
    animation?: {           // export
        tracks: Track[];
        repeat: boolean;
    };
}

/* Material and Model */
export interface MaterialImageData {
    url?: string;
    base64?: string;
}

export interface MaterialData {
    type: MaterialType;
    mtlIndex: number;
    c?: number;         // color
    o?: number;         // opacity
    ds?: boolean | number;  // double-sided
    flat?: boolean | number;
    image?: MaterialImageData;
    t?: boolean | number;        // transparent
    s?: number;         // point size
    dashed?: boolean | number;
    thickness?: number;
    metalness?: number;
    roughness?: number;
}

export interface ModelData {
    url?: string;
    base64?: string;
    ext?: string;
    resourcePath?: string;
}

/* Layer and Block */
export interface LayerData extends BaseData {
    type: "layer";
    id: string | number;
    properties: LayerProperties;
}

export interface BlockData extends BaseData {
    type: "block";
    layer: number | string;     // TODO: numeric jsLayerId
    block: number;
    progress?: number;
}

/* DEM Layer and its Block */
export interface DEMLayerData extends LayerData {
    properties: DEMLayerProperties;
    body?: {
        blocks?: DEMBlockData[];
    }
}

export interface DEMGridBlockData extends BlockData {
    width: number;
    height: number;
    translate: Vec3;
    zScale: number;
    grid?: DEMGridData;
    geom?: TIN_Border;
}

export interface DEMTileGridBlockData extends BlockData {
    segments: number;
    tileSize: number;
    translate: Vec3;
    zScale: number;
    grid: DEMGridData;
}

export interface DEMMaterialBlockData extends BlockData {
    materials?: MaterialData[];
}

export type DEMBlockData = DEMGridBlockData | DEMTileGridBlockData | DEMMaterialBlockData;

export interface DEMGridData {
    width: number;      // columns
    height: number;     // rows
    nodata: number;
    base64?: string;
    url?: string;

    values?: number[];
}

export interface TIN {
    triangles: {
        v: number[];
        f: number[];
    };
    centroids?: number[];
}

export interface TIN_Border extends TIN {
    polygons: number[];
}

/* Vector Layer and its Block */
export interface VectorLayerData extends LayerData {
    properties: VectorLayerProperties;
    body: {
        materials?: MaterialData[];
        models?: ModelData[];
        blocks?: FeatureBlockData[] | FeatureBlockDataRef[];
    };
}

export interface FeatureBlockData extends BlockData {
    features: FeatureData[];
    featureCount: number;
    startIndex: number;
}

export interface FeatureBlockDataRef extends BlockData {
    url: string;
    featureCound: number;
}

export interface FeatureData {
    geom: GeomData;
    mtl?: number;
    model?: number;
    prop?: Record<string, string | number>;
    lbl?: string;
    lh?: number;
    anim?: {
        delay: number;
        duration: number;
    };
}

export interface GeomData {
    pts?: number[];     // TODO
    r?: number;
    w?: number;
    h?: number;
    d?: number;
    l?: number;
    dd?: number;
    url?: string;
}

/* Animation */
export interface AnimationData extends BaseData {
    type: "animation";
    tracks: Track[];
    repeat: boolean;
}

export interface Track {
    type: string;
    name: string;
    enabled: boolean;
    keyframes: Keyframe[]
}

export interface Keyframe {
    type: string;
    name: string;
    easing?: string;
    delay: number;
    duration: number;
    narration?: string;
    camera?: CameraState;
    opacity?: number;
    mtlId?: number;
    mtlIndex?: number;
    effect?: string;
    sequential?: boolean;
}

interface CameraStateA {
    pos: Point3;
    lookAt: Point3;
}

interface CameraStateF {
    x: number;
    y: number;
    z: number;
    fx: number;
    fy: number;
    fz: number;
}

export type CameraState = CameraStateA | CameraStateF;

export interface NarrationData extends BaseData {
    type: "narration";
    content: string;
}

/* Preview requests, commands and signals */
export interface CameraStateData extends BaseData {
    type: "cameraState";
    state: CameraState;
}

export interface LabelsData extends BaseData {
    type: "labels";
    Header: string;
    Footer: string;
}

export interface SignalData extends BaseData {
    type: "signal";
    name: string;
    success?: boolean;
    is_scene?: boolean;
}

export type AppData =
    SceneData
    | LayerData
    | BlockData;

export type PreviewData =
    AppData
    | AnimationData
    | NarrationData
    | CameraStateData
    | LabelsData
    | SignalData;


//// Interfaces for the app, gui, and modules objects
export interface App {
    /* core objects */
    loadingManager;
    camera;
    container;
    controls;
    renderer;
    scene: Scene;
    viewHelper;
    effect;

    camera2;
    container2;
    renderer2;
    scene2: Scene;

    /* state */
    width: number;
    height: number;
    sceneLoaded: boolean;
    labelVisible;
    _wireframeMode: boolean;
    selectedLayer;
    selectedObject;
    mouseDownPoint: THREE.Vector2;
    mouseUpPoint: THREE.Vector2;
    queryTargetPosition;

    /* sub-modules */
    animation;
    cameraAction;
    eventListener;
    measure;

    /* functions */
    dispatchEvent(event);
    addEventListener(type, listener, prepend?: boolean);
    removeEventListener(type, listener);

    init(container: HTMLElement);
    initLoadingManager();

    loadData(data: AppData);
    loadFile(url: string, type, callback?);
    loadJSONFile(url: string, callback?);
    loadSceneFile(url: string, sceneFileLoadedCallback?, sceneLoadedCallback?);
    loadTextureFile(url: string, callback?);
    loadModelFile(url: string, callback?);
    loadModelData(data, ext: string, resourcePath: string, callback?);

    buildCamera(is_ortho?: boolean);
    buildNorthArrow(container: HTMLElement, declination?);
    buildViewHelper(container: HTMLElement);

    adjustCameraNearFar();
    adjustCameraPosition(force?);

    animate();
    start();
    pause();
    resume();

    render(immediate?: boolean);
    setIntervalRender(delay, repeat);
    updateControlsAndRender();

    currentViewUrl();
    setCanvasSize(width, height);
    setLabelVisible(visible);
    setRotateAnimationMode(enabled);
    setWireframeMode(wireframe);

    cleanView();
    highlightFeature(object);
    saveCanvasImage(width, height, fill_backgroundtrue, saveImageFunc?);

    canvasClicked(e);
    intersectObjects(offsetX, offsetY);

    /* private */
    anim_timer;
    highlightObject;
    highlightMaterial;
    modelBuilders;
    urlParams;
    queryMarker: THREE.Mesh;
    _canvasImageUrl;
}

export interface Gui {
    modules;

    /* sub-modules */
    dat;
    popup;
    layerPanel;

    /* functions */
    init();
    clean();
    showInfo();
    showQueryResult(point, layer, obj, show_coords);
    showPrintDialog();
}

export interface Modules {
    THREE,
    ColladaLoader,
    GLTFLoader,
    OutlineEffect,
    ViewHelper
}


export type Q3DEventListener = (...args: any[]) => void;
