// (C) 2017 Minoru Akagi
// SPDX-License-Identifier: MIT

import { app, conf, gui, modules, E } from "./Qgis2threejs.js";
const THREE = modules.THREE;
export { app, conf, gui, THREE }

import { ViewHelper } from "three/addons/helpers/ViewHelper.js";
modules.ViewHelper = ViewHelper;

import type { CameraState, PreviewData, SceneProperties } from "./types.js";

conf.preview = {

	showFPS: false

};

/* Used for FPS display */
let tickCount = 0;
let lastFPS = 0;
let lastFPSTime = 0;


export const preview = {

	renderEnabled: true,

	/**
	 * Whether to suppress rendering while data is loading.
	 */
	noRenderDuringLoad: true,

	/**
	 * Indicates whether scene/layer/block data sent from Python (such as scene/layer properties,
	 * DEM grids, feature geometries, and images) is being loaded; if block data includes image data,
	 * it remains true until the images have been loaded as textures.
	 */
	isDataLoading: false
};

/**
 * Initialize the viewer
 */
export function init(off_screen: boolean, debug_mode: number, qgis_version: number) {

	conf.debugMode = debug_mode;
	conf.qgisVersion = qgis_version;

	new QWebChannel(qt.webChannelTransport, (channel) => {
		window.pyObj = channel.objects.bridge;
		pyObj.sendData.connect((data, viaQueue) => {
			const result = loadData(data, viaQueue);

			if (conf.debugMode) {
				const dataType = data.type || "unknown";
				console.debug("↓" + dataType + " data " + (result ? "loaded" : "loading error"), data);
			}
		});

		_init(off_screen);

	});
}

function _init(off_screen) {

	const container = E("view");
	app.init(container);

	if (off_screen) {
		E("progress").style.display = "none";
		const renderOffscreen = app.render;
		app.render = () => { };		// No need to render the scene before it has fully loaded.
		app.addEventListener("sceneLoaded", () => {
			app.adjustCameraNearFar();

			app.render = renderOffscreen;
			app.render(true);
		});
	}
	else {
		E("closemsgbar").onclick = closeMessageBar;
	}

	app.addEventListener("loadComplete", () => {
		preview.isDataLoading = false;
		pyObj.emitDataLoaded();

		app.render();
	});

	app.addEventListener("loadError", () => {
		pyObj.emitDataLoadError();
	});

	app.addEventListener("sceneLoaded", () => {
		pyObj.emitSceneLoaded();
	});

	app.addEventListener("tweenStarted", (e) => {
		pyObj.emitTweenStarted(e.index);
	});

	app.addEventListener("animationStopped", () => {
		pyObj.emitAnimationStopped();
	});

	if (conf.debugMode) {
		showTriangleCount();
	}

	if (conf.preview.showFPS) {
		showFPS();
	}

	pyObj.emitInitialized();
}

//// load functions
/**
 * Loads JSON-compatible data or handles signals, commands and requests
 * @returns true if no error occurs.
 */
function loadData(data: PreviewData, viaQueue: boolean): boolean {
	let result = true;

	if (conf.debugMode) {
		console.debug("Loading " + (data.type || "unknown") + " data...");
	}

	if (viaQueue) {
		preview.isDataLoading = true;
		app.loadingManager.itemStart("data");
	}

	switch (data.type) {
		case "scene":
			if (data.properties !== undefined) {
				_requestCameraUpdate(data.properties);
			}
		// fall through
		case "layer":
		case "block":
			result = app.loadData(data);

			if ("progress" in data) {
				console.debug("Progress: " + data.progress);
				updateProgressBar(data.progress);
			}
			break;

		case "signal":
			if (data.name === "queueCompleted") {
				tasksAndLoadingFinalized(data.success, data.is_scene);

				// Temporary workaround: schedule a delayed redraw to ensure changes
				// to the scene are rendered even on low-performance systems.
				setTimeout(() => app.render(), 300);
			}
			break;

		case "labels":
			E("header").innerHTML = data.Header || "";
			E("footer").innerHTML = data.Footer || "";
			break;

		case "cameraState":
			setCameraState(data.state);
			break;

		case "animation":
			startAnimation(data.tracks, data.repeat);
			break;

		case "narration":
			showNarrativeBox(data.content);
			break;
	}

	if (viaQueue) {
		app.loadingManager.itemEnd("data");
	}

	return result;
}

function _requestCameraUpdate(sp: SceneProperties) {
	// update camera position - keep relative position to base extent
	const lastP = app.scene.userData;
	const lastBE = lastP.baseExtent;
	if (lastBE === undefined) return;

	const be = sp.baseExtent;
	const v0 = new THREE.Vector3(lastBE.cx, lastBE.cy, 0).sub(lastP.origin);
	const v1 = new THREE.Vector3(be.cx, be.cy, 0).sub(sp.origin);
	const s = be.width / lastBE.width;

	const pos = new THREE.Vector3().copy(app.camera.position).sub(v0).multiplyScalar(s).add(v1);
	const focal = new THREE.Vector3().copy(app.controls.target).sub(v0).multiplyScalar(s).add(v1);

	let near, far;
	if (s != 1) {
		near = 0.001 * be.width;
		far = 100 * be.width;
	}
	app.scene.requestCameraUpdate(pos, focal, near, far);
}

export function loadScriptFile(path: string, callback?: () => void, isModule = false, isNamespace = false) {
	if (isModule) {
		const mod = path.split("/").pop().split(".")[0];
		import(path).then(module => {
			if (isNamespace) {
				modules[mod] = module;
			} else {
				modules[mod] = module[mod];
			}
			if (callback) callback();
		});
		return;
	}

	const url = new URL(path, document.baseURI).toString();
	for (const elm of document.head.getElementsByTagName("script")) {
		if (elm.src == url) {
			if (callback) callback();
			return false;
		}
	}

	const s = document.createElement("script");
	s.src = url;
	if (callback) s.onload = callback;
	document.head.appendChild(s);
	return true;
}

export function loadModel(url: string) {

	const loadToScene = (res) => {
		const boxsize = new THREE.Box3().setFromObject(res.scene).getSize();
		const scale = 50 / Math.max(boxsize.x, boxsize.y, boxsize.z);

		const parent = new THREE.Group();
		parent.scale.set(scale, scale, scale);
		parent.rotation.x = Math.PI / 2;
		parent.add(res.scene);
		app.scene.add(parent);

		app.render();

		const sceneScale = app.scene.userData.scale;		// TODO: FIXME
		const objScale = scale / sceneScale;

		console.log("Model " + url + " loaded.");
		console.log("scale: " + scale + " (obj: " + objScale + " x scene: " + sceneScale + ")");
		console.log("To clear the added object, use scene reload (F5).");

		showMessageBar('Model preview: Successfully loaded "' + url.split("/").pop() + '". See console for details.', 3000);
	};
	const onError = (e) => {
		console.warn(e.message);
		showMessageBar('Model preview: Failed to load "' + url.split("/").pop() + '". See console for details.', 5000, true);
	};

	const ext = url.split(".").pop();
	if (ext == "dae") {
		import("three/addons/loaders/ColladaLoader.js").then(({ ColladaLoader }) => {
			const loader = new ColladaLoader(app.loadingManager);
			loader.load(url, loadToScene, undefined, onError);
		});
	}
	else if (ext == "gltf" || ext == "glb") {
		import("three/addons/loaders/GLTFLoader.js").then(({ GLTFLoader }) => {
			const loader = new GLTFLoader(app.loadingManager);
			loader.load(url, loadToScene, undefined, onError);
		});
	}
}

export function hideLayer(layerId: number, remove_obj: boolean = false) {
	const layer = app.scene.mapLayers[layerId];
	if (layer === undefined) return;

	layer.visible = false;
	if (remove_obj) layer.clearObjects();
}

let progressFadeoutSet = false;
function tasksAndLoadingFinalized(success: boolean, is_scene: boolean) {
	// hide progress bar
	E("progressbar").classList.add("fadeout");
	progressFadeoutSet = true;

	if (success && is_scene) {
		setTimeout(function () {
			app.dispatchEvent({ type: "sceneLoaded" });
		}, 0);
	}
	else {
		app.adjustCameraNearFar();
	}
}

function updateProgressBar(loaded: number, total: number = 100) {
	E("progressbar").style.width = (loaded / total * 100) + "%";
	if (progressFadeoutSet) {
		E("progressbar").classList.remove("fadeout");
		progressFadeoutSet = false;
	}
}

let lastTriangleCount = -1;

function showTriangleCount() {
	window.setInterval(function () {
		const triangles = app.renderer.info.render.triangles;
		if (triangles != lastTriangleCount) {
			E("triangles").innerHTML = "Triangles: " + app.renderer.info.render.triangles.toLocaleString();
			lastTriangleCount = triangles;
		}
	}, 1000);
}

function showFPS() {
	lastFPSTime = Date.now();

	window.setInterval(function () {
		const now = Date.now();
		const elapsed = now - lastFPSTime;
		const fps = Math.round(tickCount / elapsed * 1000);

		if (fps != lastFPS) {
			E("fps").innerHTML = "FPS: " + fps;
			lastFPS = fps;
		}

		lastFPSTime = now;
		tickCount = 0;
	}, 1000);
}

export function saveAsGLTF(filename: string) {
	showStatusMessage('Saving the model to "' + filename + '"...');

	const scene = new THREE.Scene();
	for (const id in app.scene.mapLayers) {
		const layer = app.scene.mapLayers[id];
		const group = layer.objectGroup;
		group.rotation.set(-Math.PI / 2, 0, 0);
		group.name = layer.properties.name;
		scene.add(group);
	}
	scene.updateMatrixWorld();

	const options = {
		binary: (filename.split(".").pop().toLowerCase() == "glb")
	};

	import("three/addons/exporters/GLTFExporter.js").then(({ GLTFExporter }) => {
		const gltfExporter = new GLTFExporter();
		gltfExporter.parseAsync(scene, options).then((result) => {
			const showStatus = () => {
				showStatusMessage("Successfully saved the model.", 5000);
			}

			if (result instanceof ArrayBuffer) {
				sendData(new Uint8Array(result), true, filename, showStatus);
			}
			else {
				sendData(JSON.stringify(result, null, 2), false, filename, showStatus);
			}

			// restore preview
			for (const id in app.scene.mapLayers) {
				const layer = app.scene.mapLayers[id];
				const group = layer.objectGroup;
				group.rotation.set(0, 0, 0);
				app.scene.add(group);
			}
			app.scene.updateMatrixWorld();
			app.render();
		});
	});
}

export function saveAsJSON(filename: string) {
	const obj = app.scene.toJSON();
	const json = JSON.stringify(obj, null, 2).replace(/\[\s*([\d\s,.-]+)\s*\]/g, (match, inner) => {
		return '[' + inner.replace(/\s+/g, ' ').trim() + ']';
	});
	sendData(json, false, filename);
}

function sendData(data: Uint8Array | string, is_base64: boolean, filename: string, callback?: () => void) {
	const CHUNK_SIZE = 100000;
	let offset = 0;

	function sendNext() {
		if (offset >= data.length) {
			if (callback) callback();
			return;
		}

		const chunk: Uint8Array | string = data.slice(offset, offset + CHUNK_SIZE);
		const isFirst = (offset === 0);
		const isLast = (offset + CHUNK_SIZE >= data.length);

		if (chunk instanceof Uint8Array) {
			pyObj.saveBase64(uint8ToBase64(chunk), filename, isFirst, isLast);
		}
		else {
			pyObj.saveText(chunk, filename, isFirst, isLast);
		}

		offset += CHUNK_SIZE;

		setTimeout(sendNext, 0);
	}
	sendNext();
}

function uint8ToBase64(u8: Uint8Array) {
	if (typeof u8.toBase64 === "function") {
		return u8.toBase64();
	}

	let binary = "";
	for (let i = 0; i < u8.length; i++) {
		binary += String.fromCharCode(u8[i]);
	}
	return btoa(binary);
}

export function requestRendering() {
	requestAnimationFrame(function () {
		app.render(true);
		pyObj.emitRequestedRenderingFinished();
	});
}

let barTimerId: number | null = null;
export function showMessageBar(message: string, timeout_ms: number = 0, warning = false) {
	if (barTimerId !== null) {
		clearTimeout(barTimerId);
		barTimerId = null;
	}
	if (timeout_ms) {
		barTimerId = setTimeout(closeMessageBar, timeout_ms);
	}

	E("msgcontent").innerHTML = message;

	const e = E("msgbar");
	e.style.display = "block";
	if (warning) {
		e.classList.add("warning");
	}
	else {
		e.classList.remove("warning");
	}
}

function closeMessageBar() {
	E("msgbar").style.display = "none";
	barTimerId = null;
}

function showStatusMessage(message: string, timeout_ms: number = 0) {
	pyObj.showStatusMessage(message, timeout_ms);
	console.info(message);
}

function clearStatusMessage() {
	showStatusMessage("");
}

export function setPreviewEnabled(enabled: boolean) {
	const e = E("cover");

	if (enabled) {
		app.resume();
	}
	else {
		app.pause();
		e.innerHTML = '<img src="../../Qgis2threejs.png">';
	}
	e.style.display = (enabled) ? "none" : "block";
}

export function setOutlineEffectEnabled(enabled: boolean) {
	if (enabled) {
		import("three/addons/effects/OutlineEffect.js").then(({ OutlineEffect }) => {
			app.effect = new OutlineEffect(app.renderer);
		});
	}
	else {
		app.effect = undefined;
	}
}

export function setBackgroundColor(color: number, alpha: number) {
	app.renderer.setClearColor(color, alpha);
	app.render();
}

//// camera
export function switchCamera(is_ortho: boolean) {
	app.buildCamera(is_ortho);
	app.controls.object = app.camera;
	app.controls.reset();

	console.log("Camera switched to " + ((is_ortho) ? "orthographic" : "perspective") + " camera.");

	// change parent of light
	const p = app.scene.userData;
	if (p.light) {
		app.scene.dispatchEvent({ type: "lightChanged", light: p.light });
	}

	// rebuild view helper
	if (app.viewHelper) {
		app.viewHelper.dispose();
		app.buildViewHelper(app.container);
	}

	app.updateControlsAndRender();
}

/**
 * Get current camera position and its target.
 */
export function cameraState(flat: boolean | number) {
	const p = app.scene.toMapCoordinates(app.camera.position),
		t = app.scene.toMapCoordinates(app.controls.target);
	if (flat) {
		return {
			x: p.x, y: p.y, z: p.z, fx: t.x, fy: t.y, fz: t.z
		};
	}

	return {
		pos: { x: p.x, y: p.y, z: p.z },
		lookAt: { x: t.x, y: t.y, z: t.z }
	};
}

function setCameraState(s: CameraState) {
	if ("pos" in s) {
		app.camera.position.copy(app.scene.toWorldCoordinates(s.pos));
		app.controls.target.copy(app.scene.toWorldCoordinates(s.lookAt));
	}
	else {
		app.camera.position.copy(app.scene.toWorldCoordinates(s));
		app.controls.target.copy(app.scene.toWorldCoordinates({ x: s.fx, y: s.fy, z: s.fz }));
	}
	app.camera.lookAt(app.controls.target);
	app.render();
}

export function adjustCameraPos() {
	if (conf.autoAdjustCameraPos) {
		app.adjustCameraPosition();
	}
	app.render();
}

//// lights
export function changeLight(type) {
	app.scene.lightGroup.clear();
	app.scene.buildLights(conf.lights[type], app.scene.userData.baseExtent.rotation);
	app.scene.dispatchEvent({ type: "lightChanged", light: type });
	app.render();
}

//// widgets
export function setNavigationEnabled(enabled) {
	if (enabled) {
		if (app.viewHelper === undefined) {
			app.buildViewHelper(app.container);
			app.viewHelper.render(app.renderer);
		}
	}
	else {
		if (app.viewHelper) {
			app.viewHelper.dispose();
			app.viewHelper = undefined;
		}
	}
	app.render();
}

export function setNorthArrowVisible(visible) {
	E("northarrow").style.display = (visible) ? "block" : "none";
	if (visible && app.scene2 === undefined) {
		app.buildNorthArrow(E("northarrow"), 0, app.scene.userData.baseExtent.rotation);		// TODO: FIXME
		app.render();
	}
}

export function setNorthArrowColor(color: number) {
	if (app.scene2 === undefined) {
		conf.northArrow.color = color;
	}
	else {
		app.scene2.children[app.scene2.children.length - 1].material.color = new THREE.Color(color);
		app.render();
	}
}

//// animation
function loadKeyframeGroups(groups) {
	app.animation.keyframes.clear();
	app.animation.keyframes.load(groups);
}

function startAnimation(groups, repeat) {
	if (groups) loadKeyframeGroups(groups);
	conf.animation.repeat = repeat;

	loadScriptFile("../js/lib/tweenjs/tween.js", () => {
		app.animation.keyframes.start();
	});
}

export function stopAnimation() {
	app.animation.keyframes.stop();
	closeNarrativeBox();
}

function showNarrativeBox(content) {
	E("narbody").innerHTML = content;
	E("narrativebox").classList.add("visible");
	const e = E("nextbtn");
	e.className = "";
	e.innerHTML = "Close";
}

function closeNarrativeBox() {
	E("narrativebox").classList.remove("visible");
}

export function setLayerOpacity(layerId, opacity) {
	app.scene.mapLayers[layerId].opacity = opacity;
}

export function saveCanvasImage(width, height) {
	_saveCanvasImage(width, height, true, (canvas) => {
		pyObj.saveImage(canvas.toDataURL("image/png"));
	});
}

export function copyCanvasToClipboard(width, height) {
	_saveCanvasImage(width, height, true, (canvas) => {
		pyObj.copyToClipboard(canvas.toDataURL("image/png"));
	});
}


//// wraps
const _initLoadingManager = app.initLoadingManager.bind(app);
const _render = app.render.bind(app);
const _saveCanvasImage = app.saveCanvasImage.bind(app);

app.initLoadingManager = () => {
	_initLoadingManager();

	app.loadingManager.onLoad = () => {
		app.loadingManager.isLoading = false;
		app.dispatchEvent({ type: "loadComplete" });	// dispath loadComplete instead of sceneLoaded
	};

	app.loadingManager.onProgress = undefined;
};

app.render = (immediate) => {
	if (!preview.renderEnabled) return;
	if (preview.noRenderDuringLoad && preview.isDataLoading) return;

	_render(immediate);

	if (immediate) tickCount++;
};

app.saveCanvasImage = (width, height, fill_background) => {
	const saveCanvasImage = (canvas) => {
		pyObj.saveImage(canvas.toDataURL("image/png"));
		gui.popup.hide();
	};
	_saveCanvasImage(width, height, fill_background, saveCanvasImage);
};
