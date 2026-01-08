// (C) 2017 Minoru Akagi
// SPDX-License-Identifier: MIT

//// configuration
Q3D.Config.potree.basePath = document.currentScript.src + "/../../js/potree-core";
Q3D.Config.potree.maxNodesLoading = 1;

var app = Q3D.application,
	gui = Q3D.gui;

var preview = {

	renderEnabled: true,

	timer: {
		tickCount: 0
	}
};

//// initialization
function init(off_screen, debug_mode, qgis_version, is_webengine) {

	Q3D.Config.debugMode = debug_mode;
	Q3D.Config.qgisVersion = qgis_version;
	Q3D.Config.isWebEngine = is_webengine;

	if (is_webengine) {
		// Web Channel
		new QWebChannel(qt.webChannelTransport, function(channel) {
			window.pyObj = channel.objects.bridge;
			pyObj.sendScriptData.connect(function (script, data) {
				var pyData = function () {
					return data;
				};

				eval(script);

				if (Q3D.Config.debugMode) {
					var dataType = (typeof data === "object") ? data.type : data;
					console.debug("↓", script, "# " + dataType + " data loaded", data);
				}
			});

			_init(off_screen);

		});
	}
	else {
		// WebKit Bridge
		window.pyData = function () {
			return pyObj.data();
		}

		_init(off_screen);

	}
}

function _init(off_screen) {

	var container = Q3D.E("view");
	app.init(container);

	if (off_screen) {
		Q3D.E("progress").style.display = "none";
		var renderOffscreen = app.render;
		app.render = function () {};		// not necessary to render scene before scene has been completely loaded
		app.addEventListener("sceneLoaded", function () {
			app.render = renderOffscreen;
			app.render(true); app.render(true); // render scene twice for output stability
		});
	}
	else {
		Q3D.E("closemsgbar").onclick = closeMessageBar;
	}

	app.addEventListener("sceneLoaded", function () {
		pyObj.emitSceneLoaded();
	});

	app.addEventListener("sceneLoadError", function () {
		pyObj.emitSceneLoadError();
	});

	app.addEventListener("tweenStarted", function (e) {
		pyObj.emitTweenStarted(e.index);
	});

	app.addEventListener("animationStopped", function () {
		pyObj.emitAnimationStopped();
	});

	if (Q3D.Config.debugMode) {
		displayFPS();
	}

	// check extension support of web view
	// see https://github.com/minorua/Qgis2threejs/issues/147
	var gl = app.renderer.getContext();		// WebGLRenderingContext
	if (gl.getExtension("WEBGL_depth_texture") === null) {

		var viewName = (Q3D.Config.isWebEngine) ? "WebEngine" : "WebKit";

		var msg = "The current web view (Qt " + viewName + ") cannot display 3D objects. ";

		if (!Q3D.Config.isWebEngine) {

			if (Q3D.Config.qgisVersion >= 33600) {

				msg += "Please use the Qt WebEngine view instead. You can find instructions on how to do this in the plugin ";
				msg += "<a href='https://github.com/minorua/Qgis2threejs/wiki/How-to-use-Qt-WebEngine-view-with-Qgis2threejs'>wiki</a>.";

			}
			else {

				msg += "Please consider using QGIS version 3.36 or a later version, which supports using Qt WebEngine view.";

			}
		}

		showMessageBar(msg, undefined, true);
	}

	pyObj.emitInitialized();
}

//// load functions
function loadData(data) {
	if (Q3D.Config.debugMode) {
		console.log("Loading " + (data.type || "unknown") + " data...");
	}

	var p = data.properties;

	if (data.type == "scene" && p !== undefined) {
		// update camera position - keep relative position to base extent
		var lastP = app.scene.userData,
			lastBE = lastP.baseExtent;

		if (lastBE !== undefined) {
			var be = p.baseExtent,
				v0 = new THREE.Vector3(lastBE.cx, lastBE.cy, 0).sub(lastP.origin),
				v1 = new THREE.Vector3(be.cx, be.cy, 0).sub(p.origin),
				s = be.width / lastBE.width;

			var pos = new THREE.Vector3().copy(app.camera.position).sub(v0).multiplyScalar(s).add(v1),
				focal = new THREE.Vector3().copy(app.controls.target).sub(v0).multiplyScalar(s).add(v1);

			var near, far;
			if (s != 1) {
				near = 0.001 * be.width;
				far = 100 * be.width;
			}
			app.scene.requestCameraUpdate(pos, focal, near, far);
		}
	}

	app.loadData(data);

	pyObj.emitDataLoaded();
}

function loadScriptFile(path, callback) {
	var url = new URL(path, document.baseURI);

	var elms = document.head.getElementsByTagName("script");
	for (var i = 0; i < elms.length; i++) {
		if (elms[i].src == url) {
			if (callback) callback();
			return false;
		}
	}

	var s = document.createElement("script");
	s.src = url;
	if (callback) s.onload = callback;
	document.head.appendChild(s);
	return true;
}

function loadModel(url) {

	var loadToScene = function (res) {
		var boxsize = new THREE.Box3().setFromObject(res.scene).getSize(),
				scale = 50 / Math.max(boxsize.x, boxsize.y, boxsize.z);

		var parent = new THREE.Group();
		parent.scale.set(scale, scale, scale);
		parent.rotation.x = Math.PI / 2;
		parent.add(res.scene);
		app.scene.add(parent);

		app.render();

		var sceneScale = app.scene.userData.scale,
			objScale = scale / sceneScale;

		console.log("Model " + url + " loaded.");
		console.log("scale: " + scale + " (obj: " + objScale + " x scene: " + sceneScale + ")");
		console.log("To clear the added object, use scene reload (F5).");

		showMessageBar('Model preview: Successfully loaded "' + url.split("/").pop() + '". See console for details.', 3000);
	};
	var onError = function (e) {
		console.warn(e.message);
		showMessageBar('Model preview: Failed to load "' + url.split("/").pop() + '". See console for details.', 5000, true);
	};

	var ext = url.split(".").pop();
	if (ext == "dae") {
		loadScriptFile("../js/lib/threejs/loaders/ColladaLoader.js", function () {
			var loader = new THREE.ColladaLoader(app.loadingManager);
			loader.load(url, loadToScene, undefined, onError);
		});
	}
	else if (ext == "gltf" || ext == "glb") {
		loadScriptFile("../js/lib/threejs/loaders/GLTFLoader.js", function () {
			var loader = new THREE.GLTFLoader(app.loadingManager);
			loader.load(url, loadToScene, undefined, onError);
		});
	}
}

function hideLayer(layerId, remove_obj) {
	var layer = app.scene.mapLayers[layerId];
	if (layer !== undefined) {
		layer.visible = false;
		if (remove_obj) layer.clearObjects();
	}
}

var progressFadeoutSet = false;
function updateProgressBar(loaded, total) {
	total = total || 1;
	Q3D.E("progressbar").style.width = (loaded / total * 100) + "%";
	if (progressFadeoutSet) {
		Q3D.E("progressbar").classList.remove("fadeout");
		progressFadeoutSet = false;
	}
}

function allDataSent() {
	// hide progress bar
	Q3D.E("progressbar").classList.add("fadeout");
	progressFadeoutSet = true;
}

function displayFPS() {
	preview.timer.last = Date.now();

	window.setInterval(function () {
		var now = Date.now(),
			elapsed = now - preview.timer.last,
			fps = preview.timer.tickCount / elapsed * 1000;

		Q3D.E("fps").innerHTML = "FPS: " + Math.round(fps);

		preview.timer.last = now;
		preview.timer.tickCount = 0;
	}, 1000);
}

function saveModelAsGLTF(filename) {
	console.log("Saving model to " + filename);

	var scene = new THREE.Scene(), layer, group;
	for (var k in app.scene.mapLayers) {
		layer = app.scene.mapLayers[k];
		group = layer.objectGroup;
		group.rotation.set(-Math.PI / 2, 0, 0);
		group.name = layer.properties.name;
		scene.add(group);
	}
	scene.updateMatrixWorld();

	var options = {
		binary: (filename.split(".").pop().toLowerCase() == "glb")
	};

	var gltfExporter = new THREE.GLTFExporter();
	gltfExporter.parse(scene, function(result) {

		if (result instanceof ArrayBuffer) {
			pyObj.saveBytes(new Uint8Array(result), filename);
		}
		else {
			pyObj.saveString(JSON.stringify(result, null, 2), filename);
		}
		showStatusMessage("Successfully saved the model.", 5000);

		// restore preview
		for (var k in app.scene.mapLayers) {
			layer = app.scene.mapLayers[k];
			group = layer.objectGroup;
			group.rotation.set(0, 0, 0);
			app.scene.add(group);
		}
		app.scene.updateMatrixWorld();
		app.render();
	}, options);
}

function requestRendering() {
	// wait for two frames to ensure rendering is done
	requestAnimationFrame(function () {
		requestAnimationFrame(function () {
			app.render(true);
			pyObj.emitRequestedRenderingFinished();
		});
	});
}

var barTimerId = null;
function showMessageBar(message, timeout_ms, warning) {
	if (barTimerId !== null) {
		clearTimeout(barTimerId);
		barTimerId = null;
	}
	if (timeout_ms) {
		barTimerId = setTimeout(closeMessageBar, timeout_ms);
	}

	Q3D.E("msgcontent").innerHTML = message;

	var e = Q3D.E("msgbar");
	e.style.display = "block";
	if (warning) {
		e.classList.add("warning");
	}
	else {
		e.classList.remove("warning");
	}
}

function closeMessageBar() {
	Q3D.E("msgbar").style.display = "none";
	barTimerId = null;
}

function showStatusMessage(message, timeout_ms) {
	pyObj.showStatusMessage(message, timeout_ms || 0);
	console.log(message);
}

function clearStatusMessage() {
	showStatusMessage("");
}

function setPreviewEnabled(enabled) {
	var e = Q3D.E("cover");

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
		if (THREE.OutlineEffect === undefined) {
			loadScriptFile("../js/lib/threejs/effects/OutlineEffect.js", function () {
				app.effect = new THREE.OutlineEffect(app.renderer);
			});
		}
		else if (app.effect !== undefined) {
			app.effect = new THREE.OutlineEffect(app.renderer);
		}
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
	var vec2 = new THREE.Vector2();
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
	var p = app.scene.userData;
	if (p.light) {
		app.scene.dispatchEvent({type: "lightChanged", light: p.light});
	}

	// rebuild view helper
	if (app.viewHelper !== undefined) {
		app.buildViewHelper(Q3D.E("navigation"));
	}

	app.updateControlsAndRender();
}

// current camera position and its target
function cameraState(flat) {
	var p = app.scene.toMapCoordinates(app.camera.position),
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
	if (Q3D.Config.autoAdjustCameraPos) {
		app.adjustCameraPosition();
	}
	app.render();
}

//// lights
function changeLight(type) {
	app.scene.lightGroup.clear();
	app.scene.buildLights(Q3D.Config.lights[type], app.scene.userData.baseExtent.rotation);
	app.scene.dispatchEvent({type: "lightChanged", light: type});
	app.render();
}

//// widgets
function setNavigationEnabled(enabled) {
	var elm = Q3D.E("navigation");
	elm.style.display = (enabled) ? "block" : "none";

	if (enabled) {
		if (app.viewHelper === undefined) {
			app.buildViewHelper(elm);
			app.viewHelper.render(app.renderer3);
		}
	}
	else {
		app.viewHelper = undefined;
	}
}

function setNorthArrowVisible(visible) {
	Q3D.E("northarrow").style.display = (visible) ? "block" : "none";
	if (visible && app.scene2 === undefined) {
		app.buildNorthArrow(Q3D.E("northarrow"), 0, app.scene.userData.baseExtent.rotation);
		app.render();
	}
}

function setNorthArrowColor(color) {
	if (app.scene2 === undefined) {
		Q3D.Config.northArrow.color = color;
	}
	else {
		app.scene2.children[app.scene2.children.length - 1].material.color = new THREE.Color(color);
		app.render();
	}
}

function setHFLabel(properties) {
	Q3D.E("header").innerHTML = properties.Header || "";
	Q3D.E("footer").innerHTML = properties.Footer || "";
}

//// animation
function loadKeyframeGroups(groups) {
	app.animation.keyframes.clear();
	app.animation.keyframes.load(groups);
}

function startAnimation(groups, repeat) {
	if (groups) loadKeyframeGroups(groups);
	Q3D.Config.animation.repeat = Boolean(repeat);

	loadScriptFile("../js/lib/tweenjs/tween.js", function () {
		app.animation.keyframes.start();
	});
}

function stopAnimation() {
	app.animation.keyframes.stop();
	closeNarrativeBox();
}

function showNarrativeBox(content) {
	Q3D.E("narbody").innerHTML = content;
	Q3D.E("narrativebox").classList.add("visible");
	var e = Q3D.E("nextbtn");
	e.className = "";
	e.innerHTML = "Close";
}

function closeNarrativeBox() {
	Q3D.E("narrativebox").classList.remove("visible");
}

function setLayerOpacity(layerId, opacity) {
	app.scene.mapLayers[layerId].opacity = opacity;
}

function saveCanvasImage(width, height) {
	app._saveCanvasImage(width, height, true, function (canvas) {
		pyObj.saveImage(canvas.toDataURL("image/png"));
	});
}

function copyCanvasToClipboard(width, height) {
	app._saveCanvasImage(width, height, true, function (canvas) {
		pyObj.copyToClipboard(canvas.toDataURL("image/png"));
	});
}

//// overrides
app._render = app.render;
app._saveCanvasImage = app.saveCanvasImage;

(function () {
	var renderImmediately = function () {
		if (!preview.renderEnabled) return;

		app._render(true);
		preview.timer.tickCount++;
	};

	app.render = function (immediate) {
		if (immediate) {
			renderImmediately();
		}
		else {
			requestAnimationFrame(renderImmediately);
		}
	};
})();

app.saveCanvasImage = function (width, height, fill_background) {
	var saveCanvasImage = function (canvas) {
		pyObj.saveImage(canvas.toDataURL("image/png"));
		gui.popup.hide();
	};
	app._saveCanvasImage(width, height, fill_background, saveCanvasImage);
};

//// polyfills
// for binary glTF export
// https://developer.mozilla.org/ja/docs/Web/API/HTMLCanvasElement/toBlob
if (!HTMLCanvasElement.prototype.toBlob) {
	Object.defineProperty(HTMLCanvasElement.prototype, 'toBlob', {
		value: function (callback, type, quality) {
			var binStr = atob(this.toDataURL(type, quality).split(',')[1]),
				len = binStr.length,
				arr = new Uint8Array(len);

			for (var i = 0; i < len; i++) {
				arr[i] = binStr.charCodeAt(i);
			}

			callback(new Blob([arr], {type: type || 'image/png'}));
		}
 	});
}
