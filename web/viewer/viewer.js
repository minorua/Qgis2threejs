// (C) 2017 Minoru Akagi
// SPDX-License-Identifier: MIT

const { app, gui, modules, conf, E } = window.Q3D;

conf.preview = {

	// showTriangleCount: debug_mode,

	showFPS: false

};

const preview = {

	renderEnabled: true,

	noRenderDuringLoad: true,	// whether to suppress rendering while data is loading

	isDataLoading: false,		// indicates whether scene/layer/block data sent from Python (such as scene/layer properties,
								// DEM grids, feature geometries, and images) is being loaded; if block data includes image data,
								// it remains true until the images have been loaded as textures.

	timer: {
		tickCount: 0
	}
};

//// initialization
function init(off_screen, debug_mode, qgis_version) {

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
		app.render = () => {};		// No need to render the scene before it has fully loaded.
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
const appLoadDataTypes = ["scene", "layer", "block"];

function loadData(data, viaQueue) {
	let result = true;

	if (conf.debugMode) {
		console.debug("Loading " + (data.type || "unknown") + " data...");
	}

	if (viaQueue) {
		preview.isDataLoading = true;
		app.loadingManager.itemStart("data");
	}

	if (appLoadDataTypes.includes(data.type)) {
		if (data.type == "scene" && data.properties !== undefined) {
			_requestCameraUpdate(data.properties);
		}
		result = app.loadData(data);

		if (data.progress !== undefined) {
			console.debug("Progress: " + data.progress);
			updateProgressBar(data.progress);
		}
	}
	else if (data.type == "signal") {
		if (data.name = "queueCompleted") {
			tasksAndLoadingFinalized(data.success, data.is_scene);
			setTimeout(() => app.render(), 300);	// Temporary workaround: schedule a delayed redraw to ensure changes
													// to the scene are rendered even on low-performance systems.
		}
	}
	else if (data.type == "labels") {
		E("header").innerHTML = data.Header || "";
		E("footer").innerHTML = data.Footer || "";
	}
	else if (data.type == "cameraState") {
		setCameraState(data.state);
	}
	else if (data.type == "animation") {
		startAnimation(data.tracks, data.repeat);
	}
	else if (data.type == "narration") {
		showNarrativeBox(data.content);
	}

	if (viaQueue) {
		app.loadingManager.itemEnd("data");
	}

	return result;
}

function _requestCameraUpdate(sp) {
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

function loadScriptFile(path, callback, isModule=false, isNamespace=false) {
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

	const url = new URL(path, document.baseURI);
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

function loadModel(url) {

	const loadToScene = (res) => {
		const boxsize = new THREE.Box3().setFromObject(res.scene).getSize();
		const scale = 50 / Math.max(boxsize.x, boxsize.y, boxsize.z);

		const parent = new THREE.Group();
		parent.scale.set(scale, scale, scale);
		parent.rotation.x = Math.PI / 2;
		parent.add(res.scene);
		app.scene.add(parent);

		app.render();

		const sceneScale = app.scene.userData.scale;
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
		import("three/loaders/ColladaLoader.js").then(({ ColladaLoader }) => {
			const loader = new ColladaLoader(app.loadingManager);
			loader.load(url, loadToScene, undefined, onError);
		});
	}
	else if (ext == "gltf" || ext == "glb") {
		import("three/loaders/GLTFLoader.js").then(({ GLTFLoader }) => {
			const loader = new GLTFLoader(app.loadingManager);
			loader.load(url, loadToScene, undefined, onError);
		});
	}
}

function hideLayer(layerId, remove_obj) {
	const layer = app.scene.mapLayers[layerId];
	if (layer === undefined) return;

	layer.visible = false;
	if (remove_obj) layer.clearObjects();
}

let progressFadeoutSet = false;
function tasksAndLoadingFinalized(success, is_scene) {
	// hide progress bar
	E("progressbar").classList.add("fadeout");
	progressFadeoutSet = true;

	if (success && is_scene) {
		setTimeout(function () {
			app.dispatchEvent({type: "sceneLoaded"});
		}, 0);
	}
	else {
		app.adjustCameraNearFar();
	}
}

function updateProgressBar(loaded, total) {
	total = total || 100;
	E("progressbar").style.width = (loaded / total * 100) + "%";
	if (progressFadeoutSet) {
		E("progressbar").classList.remove("fadeout");
		progressFadeoutSet = false;
	}
}

function showTriangleCount() {
	window.setInterval(function () {
		const triangles = app.renderer.info.render.triangles;
		if (triangles != preview.lastTriangleCount) {
			E("triangles").innerHTML = "Triangles: " + app.renderer.info.render.triangles.toLocaleString();
			preview.lastTriangleCount = triangles;
		}
	}, 1000);
}

function showFPS() {
	preview.timer.last = Date.now();

	window.setInterval(function () {
		const now = Date.now();
		const elapsed = now - preview.timer.last;
		const fps = Math.round(preview.timer.tickCount / elapsed * 1000);

		if (fps != preview.lastFPS) {
			E("fps").innerHTML = "FPS: " + fps;
			preview.lastFPS = fps;
		}

		preview.timer.last = now;
		preview.timer.tickCount = 0;
	}, 1000);
}

function saveModelAsGLTF(filename) {
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

	import("three/exporters/GLTFExporter.js").then(({ GLTFExporter }) => {
		const gltfExporter = new GLTFExporter();
		gltfExporter.parse(scene, (result) => {
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
				layer = app.scene.mapLayers[id];
				group = layer.objectGroup;
				group.rotation.set(0, 0, 0);
				app.scene.add(group);
			}
			app.scene.updateMatrixWorld();
			app.render();
		}, options);
	});
}

function uint8ToBase64(u8) {
    let binary = "";
    for (let i = 0; i < u8.length; i++) {
        binary += String.fromCharCode(u8[i]);
    }
    return btoa(binary);
}

function sendData(data, is_base64, filename, callback) {
    const CHUNK_SIZE = 100000;
    let offset = 0;

	function sendNext() {
        if (offset >= data.length) {
			if (callback) callback();
            return;
        }

        const chunk = data.slice(offset, offset + CHUNK_SIZE);
        const isFirst = (offset === 0);
        const isLast = (offset + CHUNK_SIZE >= data.length);

		if (is_base64) {
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

function requestRendering() {
	requestAnimationFrame(function () {
		app.render(true);
		pyObj.emitRequestedRenderingFinished();
	});
}

let barTimerId = null;
function showMessageBar(message, timeout_ms, warning) {
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

function showStatusMessage(message, timeout_ms) {
	pyObj.showStatusMessage(message, timeout_ms || 0);
	console.info(message);
}

function clearStatusMessage() {
	showStatusMessage("");
}

function setPreviewEnabled(enabled) {
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

function setOutlineEffectEnabled(enabled) {
	if (enabled) {
		loadScriptFile("../js/lib/threejs/effects/OutlineEffect.js", () => {
			app.effect = new modules.OutlineEffect(app.renderer);
		}, true);
	}
	else {
		app.effect = undefined;
	}
}

function setBackgroundColor(color, alpha) {
	app.renderer.setClearColor(color, alpha);
	app.render();
}

function verifySize(width, height) {
	const vec2 = new THREE.Vector2();
	app.renderer.getSize(vec2);
	return (vec2.x == width && vec2.y == height);
}

//// camera
function switchCamera(is_ortho) {
	app.buildCamera(is_ortho);
	app.controls.object = app.camera;
	app.controls.reset();

	console.log("Camera switched to " + ((is_ortho) ? "orthographic" : "perspective") + " camera.");

	// change parent of light
	const p = app.scene.userData;
	if (p.light) {
		app.scene.dispatchEvent({type: "lightChanged", light: p.light});
	}

	// rebuild view helper
	if (app.viewHelper) {
		app.viewHelper.dispose();
		app.buildViewHelper(app.container);
	}

	app.updateControlsAndRender();
}

// current camera position and its target
function cameraState(flat) {
	const p = app.scene.toMapCoordinates(app.camera.position),
		  t = app.scene.toMapCoordinates(app.controls.target);
	if (flat) {
		return {
			x: p.x, y: p.y, z: p.z, fx: t.x, fy: t.y, fz: t.z
		};
	}

	return {
		pos: {x: p.x, y: p.y, z: p.z},
		lookAt: {x: t.x, y: t.y, z: t.z}
	};
}

function setCameraState(s) {
	if (s.pos !== undefined) {
		app.camera.position.copy(app.scene.toWorldCoordinates(s.pos));
		app.controls.target.copy(app.scene.toWorldCoordinates(s.lookAt));
	}
	else {
		app.camera.position.copy(app.scene.toWorldCoordinates(s));
		app.controls.target.copy(app.scene.toWorldCoordinates({x: s.fx, y: s.fy, z: s.fz}));
	}
	app.camera.lookAt(app.controls.target);
	app.render();
}

function adjustCameraPos() {
	if (conf.autoAdjustCameraPos) {
		app.adjustCameraPosition();
	}
	app.render();
}

//// lights
function changeLight(type) {
	app.scene.lightGroup.clear();
	app.scene.buildLights(conf.lights[type], app.scene.userData.baseExtent.rotation);
	app.scene.dispatchEvent({type: "lightChanged", light: type});
	app.render();
}

//// widgets
function setNavigationEnabled(enabled) {
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

function setNorthArrowVisible(visible) {
	E("northarrow").style.display = (visible) ? "block" : "none";
	if (visible && app.scene2 === undefined) {
		app.buildNorthArrow(E("northarrow"), 0, app.scene.userData.baseExtent.rotation);
		app.render();
	}
}

function setNorthArrowColor(color) {
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
	conf.animation.repeat = Boolean(repeat);

	loadScriptFile("../js/lib/tweenjs/tween.js", () => {
		app.animation.keyframes.start();
	});
}

function stopAnimation() {
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

function setLayerOpacity(layerId, opacity) {
	app.scene.mapLayers[layerId].opacity = opacity;
}

function saveCanvasImage(width, height) {
	app._saveCanvasImage(width, height, true, (canvas) => {
		pyObj.saveImage(canvas.toDataURL("image/png"));
	});
}

function copyCanvasToClipboard(width, height) {
	app._saveCanvasImage(width, height, true, (canvas) => {
		pyObj.copyToClipboard(canvas.toDataURL("image/png"));
	});
}


//// overrides
app._initLoadingManager = app.initLoadingManager;
app._render = app.render;
app._saveCanvasImage = app.saveCanvasImage;

app.initLoadingManager = () => {
	app._initLoadingManager();

	app.loadingManager.onLoad = () => {
		app.loadingManager.isLoading = false;
		app.dispatchEvent({type: "loadComplete"});	// dispath loadComplete instead of sceneLoaded
	};

	app.loadingManager.onProgress = undefined;
};

app.render = (immediate) => {
	if (!preview.renderEnabled) return;
	if (preview.noRenderDuringLoad && preview.isDataLoading) return;

	app._render(immediate);

	if (immediate) preview.timer.tickCount++;
};

app.saveCanvasImage = (width, height, fill_background) => {
	const saveCanvasImage = (canvas) => {
		pyObj.saveImage(canvas.toDataURL("image/png"));
		gui.popup.hide();
	};
	app._saveCanvasImage(width, height, fill_background, saveCanvasImage);
};
