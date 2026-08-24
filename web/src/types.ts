/*
These type definitions are incomplete and may contain inaccuracies
*/
import type * as THREE from "three";
import type { Collada } from "three/addons/loaders/ColladaLoader.js";
import type { GLTF } from "three/addons/loaders/GLTFLoader.js";

import type { LayerType, MaterialType, TweenType } from "./core.js";
import type { Scene } from "./scene.js";
import type { MapLayer } from "./layer/layer.js";
import type { DEMLayer } from "./layer/demlayer.js";
import type { LineLayer } from "./layer/linelayer.js";
export type { LayerType, MaterialType, TweenType };

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

export type Vec2 = [number, number];
export type Vec3 = [number, number, number];

export interface MapExtent {
    cx: number;
    cy: number;
    width: number;
    height: number;
}

/* Properties */
export interface SceneProperties {
	baseExtent: MapExtent;	 // map base extent in map coordinates. center is (cx, cy).
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
    dataType: "grid" | "mesh";
    mtlNames: string[];
    mtlIdx: number;
    sides?: {
        mtl: MaterialData;
        bottom: number;
    };
}

export interface VectorLayerProperties extends LayerProperties {
    type: "point" | "line" | "polygon";
    objType: string;
    fieldNames?: string[];
    label?: LabelProperties;
}

interface LabelProperties {
    relative?: boolean;
    font?: string;
    size?: number;
    color?: string;
    olcolor?: string;
    bgcolor?: string;
    cncolor?: number;
    underline?: boolean;
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
    useNow?: boolean;
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

export type ModelObject = Collada | GLTF;

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

export interface DEMBlockDataBase extends BlockData {
    extent: MapExtent;
    translate: Vec3;
    zScale: number;
    segments: number;
}

/**
 * DEM block data based on regular grid.
 */
export interface DEMBlockGridData extends DEMBlockDataBase {
    grid: DEMGridData | DEMGridDataRef;
}

export interface DEMBlockMeshData extends DEMBlockDataBase {
    mesh: DEMMeshData | DEMMeshDataRef;
}

export interface DEMBlockMaterialData extends BlockData {
    materials: MaterialData[];
}

export type DEMBlockData = DEMBlockGridData | DEMBlockMeshData | DEMBlockMaterialData;

export interface DEMGridData {
    columns: number;
    rows: number;
    dem_values: Base64F32;
    nodata?: Base64F32;
}

export interface ParsedDEMGridData {
    columns: number;
    rows: number;
    dem_values: Float32Array;
    nodata?: Float32Array1;
}

export interface DEMGridDataRef {
    url: string;
}

export interface DEMMeshData {
    vertices: string;
    indices: string;
    uvs?: string;
}

export interface ParsedDEMMeshData {
    vertices: Float32Array;
    indices: Uint32Array;
    uvs?: Float32Array;
}

export interface DEMMeshDataRef {
    url: string;
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
    geom: GeomData | MeshData;
    mtl?: {
        idx: number;
        brdr?: number;
        edge?: number;
    };
    model?: number;
    prop?: Record<string, string | number>;
    lbl?: string;
    lh?: number;
    anim?: {
        delay: number;
        duration: number;
    };
}

export interface Feature extends FeatureData {
    objs?: RenderableObject[];
}

export type RenderableObject = THREE.Mesh<THREE.BufferGeometry, THREE.Material> | THREE.Line | THREE.Points | THREE.Sprite;

export interface GeomData {
    pts?: number[] | Vec3[];
    lines?: (number[] | Vec3[])[];
    polygons: Vec2[][][];
    centroids: Vec3[];
    r?: number;
    w?: number;
    h?: number;
    d?: number;
    l?: number;
    dd?: number;
    bh?: number;
    size?: number;
    scale?: number;
    rotateX?: number;
    rotateY?: number;
    rotateZ?: number;
    rotateO?: THREE.EulerOrder;
    url?: string;
}

export interface MeshData {
    vertices: number[];
    indices: number[];
    centroids: (Vec3 | 0)[];
}

/* Animation */
export interface AnimationData extends BaseData {
    type: "animation";
    tracks: Track[];
    repeat: boolean;
}

export interface TrackData {
    type: string;
    name: string;
    enabled: boolean;
    keyframes: Keyframe[]
}

export interface Track extends TrackData {
    prop_list?;
    currentIndex?: number;
    _keyframes?;
    onStart?: () => void;
    onUpdate?: (obj, elapsed?, isFirst?) => void;
}

export interface Keyframe {
    delay?: number;
    duration?: number;
    easing?: string;
    narration?: string;
    camera?: CameraStateFK;
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

interface CameraStateFK extends CameraStateF {
    phi?: number;
}

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


//// binary data
type BinaryDataType = "f32" | "I32";

interface Base64DataBase {
    __type__: BinaryDataType;
    compressed: boolean;
    data: string;
}

interface Base64F32 extends Base64DataBase {
    __type__: "f32";
}

interface Base64I32 extends Base64DataBase {
    __type__: "I32";
}

export type Base64Data = Base64F32 | Base64I32;

interface DataRefBase {
    __type__: BinaryDataType;
    compressed: boolean;
    offset: number;
    size: number;
}

interface DataRefF32 extends DataRefBase {
    __type__: "f32";
}

interface DataRefI32 extends DataRefBase {
    __type__: "I32";
}

type DataRef = DataRefF32 | DataRefI32;

/** Float32Array & { length: 1 } */
type Float32Array1 = Float32Array;


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
    animation: AnimationModule;
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
    loadJSONBinaryFile(url: string): Promise<any>;
    buildCamera(is_ortho?: boolean);
    buildNorthArrow(container: HTMLElement, declination?: number);
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

interface AnimationModule {
    isActive: boolean;
    start(): void;
    stop(): void;
    keyframes: {
        isActive: boolean;
        isPaused: boolean;
        curveFactor: number;
        easingFunction: (easing) => unknown;
        tracks: Track[];
        clear(): void;
        load(track: Track | Track[]): void;
        start(): void;
        stop(): void;
        pause(): void;
        resume(): void;
    };
    orbit: {
        isActive: boolean;
        start(): void;
        stop(): void;
    };
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
    THREE;
    BufferGeometryUtils;
    ColladaLoader;
    GLTFLoader;
    OutlineEffect;
    ViewHelper;
    meshline;
    dat;
}

export interface Tween {
    type: TweenType;
    curveFactor?: number;
    init(track: Track, layer?: MapLayer): void;
}

export interface TweenDEM extends Tween {
    init(track: Track, layer?: DEMLayer): void;
}

export interface TweenLine extends Tween {
    init(track: Track, layer?: LineLayer): void;
}

export type Tweens = Record<string, Tween>;

//// Interface for the pyObj
interface Signal<TArgs extends unknown[] = []> {
    connect(callback: (...args: TArgs) => void): void;
}

export interface PyObj {
    sendData: Signal<[data: PreviewData, viaQueue: boolean]>;

    emitInitialized(): void;
    emitDataLoaded(): void;
    emitDataLoadError(): void;
    emitSceneLoaded(): void;
    emitScriptReady(scriptFileId: number): void;
    emitTweenStarted(index: number): void;
    emitAnimationStopped(): void;

    showStatusMessage(message: string, timeout_ms?: number): void;
    saveBase64(b64str: string, filename: string, is_first: boolean, is_last: boolean): void;
    saveText(text: string, filename: string, is_first: boolean, is_last: boolean): void;
    saveImage(dataUrl: string): void;
    copyToClipboard(dataUrl: string): void;

    // dev
    emitRequestedRenderingFinished(): void;
    sendTestResult(testName: string, result: boolean, msg: string): void;
};

//// Event map
export interface ObjectEventMap extends THREE.Object3DEventMap {
	renderRequest: {};
}

export interface SceneEventMap extends ObjectEventMap {
	cameraUpdateRequest: {
		pos: THREE.Vector3;
		focal: THREE.Vector3;
		near: number;
		far: number;
	};
	lightChanged: {
		light: string;
	};
}

export interface ModelEventMap extends THREE.Object3DEventMap {
	modelLoaded: {
		model: ModelObject;
	};
}

export type Q3DEventListener = (...args: any[]) => void;
