// (C) 2014 Minoru Akagi
// SPDX-License-Identifier: MIT
// https://github.com/minorua/Qgis2threejs

import * as THREE from "three";
import { OrbitControls } from "three/controls/OrbitControls.js";

const THREE_EX = {

	OrbitControls: OrbitControls

};

export const Q3D = {

	VERSION: "3.1",

	application: {},

	gui: {
		modules: [],
		dat: null
	},

	Config: {
		// renderer
		renderer: {
			hiDpi: true       // HD-DPI support
		},

		texture: {
			anisotropy: -4    // zero means max available value. negative value means max / -v.
		},

		// scene
		autoAdjustCameraPos: true,  // automatic camera height adjustment
		bgColor: null,              // null is sky

		// camera
		orthoCamera: false,
		viewpoint: {      // z-up
			default: {      // assumed that origin is (0, 0, 0) and base extent width in 3D world coordinates is 1
				pos: new THREE.Vector3(0, -1, 1),
				lookAt: new THREE.Vector3()
			}
		},

		// light
		lights: {
			directional: [
				{
					type: "ambient",
					color: 0x999999,
					intensity: 2.513
				},
				{
					type: "directional",
					color: 0xffffff,
					intensity: 2.513,
					azimuth: 220,   // azimuth of light, in degrees. default light azimuth of gdaldem hillshade is 315.
					altitude: 45    // altitude angle in degrees.
				}
			],
			point: [
				{
					type: "ambient",
					color: 0x999999,
					intensity: 2.827
				},
				{
					type: "point",
					color: 0xffffff,
					intensity: 3,
					decay: 0.01,
					height: 10
				}
			]
		},

		// layer
		allVisible: false,   // set every layer visible property to true on load if set to true

		line: {
			dash: {
				dashSize: 1,
				gapSize: 0.5
			}
		},

		label: {
			visible: true,
			canvasHeight: 64,
			clickable: true
		},

		// widgets
		navigation: {
			enabled: true,
			top: null,
			bottom: 0
		},

		northArrow: {
			color: 0x8b4513,
			cameraDistance: 30,
			enabled: false
		},

		// animation
		animation: {
			enabled: false,
			startOnLoad: false,
			easingCurve: "Cubic",
			repeat: false
		},

		// others
		qmarker: {
			radius: 0.004,
			color: 0xffff00,
			opacity: 0.8,
			k: 0.2    // size factor for ortho camera
		},

		measure: {
			marker: {
				radius: 0.004,
				color: 0xffff00,
				opacity: 0.5
				/* k: 0.2 */
			},
			line: {
				color: 0xffff00
			}
		},

		coord: {
			visible: true,
			latlon: false
		},

		gui: {
			customPlane: false		// dat-gui
		},

		debugMode: false,

		preview: null
	}
};

window["THREE"] = THREE;
window["THREE_EX"] = THREE_EX;
window["Q3D"] = Q3D;

// consts
Q3D.LayerType = {

	DEM: "dem",
	Point: "point",
	Line: "line",
	Polygon: "polygon",
	PointCloud: "pc"

};

Q3D.MaterialType = {

	MeshLambert: 0,
	MeshPhong: 1,
	MeshToon: 2,
	Line: 3,
	MeshLine: 4,
	Sprite: 5,
	Point: 6,
	MeshStandard: 7,
	Unknown: -1

};

Q3D.KeyframeType = {

	CameraMotion: 64,
	Opacity: 65,
	Texture: 66,
	GrowingLine: 67

};

Q3D.uv = {

	i: new THREE.Vector3(1, 0, 0),
	j: new THREE.Vector3(0, 1, 0),
	k: new THREE.Vector3(0, 0, 1)

};

Q3D.deg2rad = Math.PI / 180;

Q3D.ua = window.navigator.userAgent.toLowerCase();
Q3D.isTouchDevice = ("ontouchstart" in window);

Q3D.E = (id) => document.getElementById(id);

const app = Q3D.application;
const gui = Q3D.gui;
const conf = Q3D.Config;
const E = Q3D.E;

(function () {
	const vec3 = new THREE.Vector3();

	/*
	Q3D.application
	*/
	const listeners = {};
	app.dispatchEvent = (event) => {
		for (const listener of listeners[event.type] || []) {
			listener(event);
		}
	};

	app.addEventListener = (type, listener, prepend) => {
		listeners[type] = listeners[type] || [];
		if (prepend) {
			listeners[type].unshift(listener);
		}
		else {
			listeners[type].push(listener);
		}
	};

	app.removeEventListener = (type, listener) => {
		const array = listeners[type];
		if (!array) return;

		const idx = array.indexOf(listener);
		if (idx !== -1) array.splice(idx, 1);
	};

	app.init = (container) => {

		app.container = container;
		app.sceneLoaded = false;

		app.selectedObject = null;
		app.highlightObject = null;

		app.modelBuilders = [];
		app._wireframeMode = false;

		// URL parameters
		const params = app.parseUrlParameters();
		app.urlParams = params;

		if ("popup" in params) {
			// open popup window
			const c = window.location.href.split("?");
			window.open(c[0] + "?" + c[1].replace(/&?popup/, ""), "popup", "width=" + params.width + ",height=" + params.height);
			gui.popup.show("Another window has been opened.");
			return;
		}

		if (params.hiDpi == "no") conf.renderer.hiDpi = false;
		if (params.anisotropy) conf.texture.anisotropy = parseFloat(params.anisotropy);

		if (params.cx !== undefined) conf.viewpoint.pos = new THREE.Vector3(parseFloat(params.cx), parseFloat(params.cy), parseFloat(params.cz));
		if (params.tx !== undefined) conf.viewpoint.lookAt  = new THREE.Vector3(parseFloat(params.tx), parseFloat(params.ty), parseFloat(params.tz));

		if (params.width && params.height) {
			container.style.width = params.width + "px";
			container.style.height = params.height + "px";
		}

		app.width = container.clientWidth;
		app.height = container.clientHeight;

		const bgcolor = conf.bgColor;
		if (bgcolor === null) container.classList.add("sky");

		// WebGLRenderer
		app.renderer = new THREE.WebGLRenderer({alpha: true, antialias: true});
		app.renderer.autoClear = false;

		if (conf.renderer.hiDpi) {
			app.renderer.setPixelRatio(window.devicePixelRatio);
		}

		app.renderer.setSize(app.width, app.height);
		app.renderer.setClearColor(bgcolor || 0, (bgcolor === null) ? 0 : 1);
		app.container.appendChild(app.renderer.domElement);

		if (conf.texture.anisotropy <= 0) {
			const maxAnis = app.renderer.capabilities.getMaxAnisotropy() || 1;

			if (conf.texture.anisotropy == 0) {
				conf.texture.anisotropy = maxAnis;
			}
			else {
				conf.texture.anisotropy = (maxAnis > -conf.texture.anisotropy) ? -maxAnis / conf.texture.anisotropy : 1;
			}
		}

		// outline effect
		if (THREE_EX.OutlineEffect) app.effect = new THREE_EX.OutlineEffect(app.renderer);

		// scene
		app.scene = new Q3DScene();

		app.scene.addEventListener("renderRequest", (event) => {
			app.render();
		});

		app.scene.addEventListener("cameraUpdateRequest", (event) => {
			app.camera.position.copy(event.pos);
			app.camera.lookAt(event.focal);
			if (app.controls.target !== undefined) app.controls.target.copy(event.focal);
			if (app.controls.saveState !== undefined) app.controls.saveState();

			if (Number.isNaN(event.near) || Number.isNaN(event.far)) return;

			app.camera.near = (app.camera.isOrthographicCamera) ? 0 : event.near;
			app.camera.far = event.far;
			app.camera.updateProjectionMatrix();
		});

		app.scene.addEventListener("lightChanged", (event) => {
			if (event.light == "point") {
				app.scene.add(app.camera);
				app.camera.add(app.scene.lightGroup);
			}
			else {    // directional
				app.scene.remove(app.camera);
				app.scene.add(app.scene.lightGroup);
			}
		});

		app.scene.addEventListener("mapRotationChanged", (event) => {
			if (app.scene2) {
				app.scene2.lightGroup.clear();
				app.scene2.buildLights(Q3D.Config.lights.directional, event.rotation);
			}
		});

		// camera
		app.buildCamera(conf.orthoCamera);

		// controls
		app.controls = new THREE_EX.OrbitControls(app.camera, app.renderer.domElement);
		app.controls.listenToKeyEvents(window);
		app.controls.addEventListener("change", (event) => {
			app.render();
		});
		app.controls.update();

		// navigation
		if (conf.navigation.enabled) {
			app.buildViewHelper(app.container);
		}

		// north arrow
		if (conf.northArrow.enabled) {
			app.buildNorthArrow(E("northarrow"));
		}

		// labels
		app.labelVisible = conf.label.visible;

		// create a marker for queried point
		var opt = conf.qmarker;
		app.queryMarker = new THREE.Mesh(new THREE.SphereGeometry(opt.radius, 32, 32),
										 new THREE.MeshLambertMaterial({color: opt.color, opacity: opt.opacity, transparent: (opt.opacity < 1)}));
		app.queryMarker.name = "marker";

		app.queryMarker.onBeforeRender = function (renderer, scene, camera, geometry, material, group) {
			this.scale.setScalar(this.position.distanceTo(camera.position) * ((camera.isPerspectiveCamera) ? 1 : conf.qmarker.k));
			this.updateMatrixWorld();
		};

		app.highlightMaterial = new THREE.MeshLambertMaterial({emissive: 0x999900, transparent: true, opacity: 0.5, side: THREE.DoubleSide});

		// loading manager
		app.initLoadingManager();

		// event listeners
		app.addEventListener("sceneLoaded", () => {
			E("progressbar").classList.add("fadeout");

			app.adjustCameraNearFar();

			if (conf.viewpoint.pos === undefined && conf.autoAdjustCameraPos) {
				app.adjustCameraPosition();
			}
			app.render();

			if (conf.animation.enabled) {
				const btn = E("animbtn");
				if (btn) {
					btn.className = "playbtn";
				}

				if (conf.animation.startOnLoad) {
					app.animation.keyframes.start();
				}
			}
		}, true);

		window.addEventListener("keydown", app.eventListener.keydown);
		window.addEventListener("resize", app.eventListener.resize);

		app.renderer.domElement.addEventListener("mousedown", app.eventListener.mousedown);
		app.renderer.domElement.addEventListener("mouseup", app.eventListener.mouseup);

		gui.init();
	};

	app.parseUrlParameters = () => {
		const vars = {};
		for (const param of window.location.search.substring(1).split('&').concat(window.location.hash.substring(1).split('&'))) {
			const p = param.split('=');
			vars[p[0]] = p[1];
		}
		return vars;
	};

	app.initLoadingManager = () => {
		app.loadingManager = new THREE.LoadingManager(
		() => {   // onLoad
			app.loadingManager.isLoading = false;
			app.sceneLoaded = true;
			app.dispatchEvent({type: "sceneLoaded"});
		},
		(url, loaded, total) => {   // onProgress
			E("progressbar").style.width = (loaded / total * 100) + "%";
		},
		() => {   // onError
			app.loadingManager.isLoading = false;
			app.dispatchEvent({type: "loadError"});
		});

		app.loadingManager.isLoading = false;

		app.loadingManager.onStart = () => {
			app.loadingManager.isLoading = true;
		};
	};

	app.loadFile = (url, type, callback) => {

		const loader = new THREE.FileLoader(app.loadingManager);
		loader.setResponseType(type);

		const onError = (e) => {
			if (location.protocol == "file:") {
				gui.popup.show("This browser doesn't allow loading local files via Ajax. See <a href='https://github.com/minorua/Qgis2threejs/wiki/Browser-Support'>plugin wiki page</a> for details.", "Error", true);
			}
		};

		try {
			loader.load(url, callback, undefined, onError);
		}
		catch (e) {      // for IE
			onError(e);
		}
	};

	app.loadData = (data) => {
		try {
			app.scene.loadData(data);
			if (data.animation !== undefined) app.animation.keyframes.load(data.animation.tracks);
			return true;
		}
		catch (e) {
			console.error(e);
			return false;
		}
	};

	app.loadJSONFile = (url, callback) => {
		app.loadFile(url, "json", (data) => {
			app.loadData(data);
			if (callback) callback(data);
		});
	};

	app.loadSceneFile = (url, sceneFileLoadedCallback, sceneLoadedCallback) => {

		const onload = () => {
			if (sceneFileLoadedCallback) sceneFileLoadedCallback(app.scene);

			app.loadingManager.itemEnd("scenefile");
		};

		if (sceneLoadedCallback) {
			app.addEventListener("sceneLoaded", () => {
				sceneLoadedCallback(app.scene);
			});
		}

		app.loadingManager.itemStart("scenefile");

		const ext = url.split(".").pop();
		if (ext == "json") {
			app.loadJSONFile(url, onload);
		}
		else if (ext == "js") {
			const e = document.createElement("script");
			e.src = url;
			e.onload = onload;
			document.body.appendChild(e);
		}
	};

	app.loadTextureFile = (url, callback) => {
		return new THREE.TextureLoader(app.loadingManager).load(url, callback);
	};

	app.loadModelFile = (url, callback) => {
		const ext = url.split(".").pop();

		let loader;
		if (ext == "dae") {
			loader = new THREE_EX.ColladaLoader(app.loadingManager);
		}
		else if (ext == "gltf" || ext == "glb") {
			loader = new THREE_EX.GLTFLoader(app.loadingManager);
		}
		else {
			console.warn("Model file type not supported: " + url);
			return;
		}

		app.loadingManager.itemStart("M" + url);

		loader.load(url, (model) => {
			if (callback) callback(model);
			app.loadingManager.itemEnd("M" + url);
		},
		undefined, (e) => {
			console.warn("Failed to load model: " + url);
			app.loadingManager.itemError("M" + url);
		});
	};

	app.loadModelData = (data, ext, resourcePath, callback) => {

		if (ext == "dae") {
			const model = new THREE_EX.ColladaLoader(app.loadingManager).parse(data, resourcePath);
			if (callback) callback(model);
		}
		else if (ext == "gltf" || ext == "glb") {
			new THREE_EX.GLTFLoader(app.loadingManager).parse(data, resourcePath, (model) => {
				if (callback) callback(model);
			}, (e) => {
				console.warn("Failed to load a glTF model: " + e);
			});
		}
		else {
			console.warn("Model file type not supported: " + ext);
			return;
		}
	};

	app.mouseDownPoint = new THREE.Vector2();
	app.mouseUpPoint = new THREE.Vector2();

	app.eventListener = {

		keydown: function (e) {
			if (e.ctrlKey) return;

			if (e.shiftKey) {
				switch (e.keyCode) {
					case 82:  // Shift + R
						app.controls.reset();
						return;
					case 83:  // Shift + S
						gui.showPrintDialog();
						return;
				}
				return;
			}

			switch (e.keyCode) {
				case 8:   // BackSpace
					if (app.measure.isActive) app.measure.removeLastPoint();
					return;
				case 13:  // Enter
					app.animation.keyframes.resume();
					return;
				case 27:  // ESC
					if (gui.popup.isVisible()) {
						app.cleanView();
					}
					else if (app.controls.autoRotate) {
						app.setRotateAnimationMode(false);
					}
					return;
				case 73:  // I
					gui.showInfo();
					return;
				case 76:  // L
					app.setLabelVisible(!app.labelVisible);
					return;
				case 82:  // R
					app.setRotateAnimationMode(!app.controls.autoRotate);
					return;
				case 87:  // W
					app.setWireframeMode(!app._wireframeMode);
					return;
			}
		},

		mousedown: function (e) {
			app.mouseDownPoint.set(e.clientX, e.clientY);
		},

		mouseup: function (e) {
			app.mouseUpPoint.set(e.clientX, e.clientY);
			if (app.mouseDownPoint.equals(app.mouseUpPoint)) app.canvasClicked(e);
		},

		resize: function () {
			app.setCanvasSize(app.container.clientWidth, app.container.clientHeight);
			app.render();
		}

	};

	app.setCanvasSize = (width, height) => {
		const changed = (app.width != width || app.height != height);

		app.width = width;
		app.height = height;
		app.camera.aspect = width / height;
		app.camera.updateProjectionMatrix();
		app.renderer.setSize(width, height);

		if (changed) app.dispatchEvent({type: "canvasSizeChanged"});
	};

	app.buildCamera = (is_ortho) => {
		if (is_ortho) {
			app.camera = new THREE.OrthographicCamera(-app.width / 10, app.width / 10, app.height / 10, -app.height / 10);
		}
		else {
			app.camera = new THREE.PerspectiveCamera(45, app.width / app.height);
		}

		// magic to change y-up world to z-up
		app.camera.up.set(0, 0, 1);

		// temporary near and far values from base extent
		const be = app.scene.userData.baseExtent;
		if (be) {
			app.camera.near = (is_ortho) ? 0 : 0.001 * be.width;
			app.camera.far = 100 * be.width;
			app.camera.updateProjectionMatrix();
		}
	};

	// adjusts camera's near and far based on the scene's bounding box
	app.adjustCameraNearFar = () => {
		const bbox = app.scene.boundingBox();
		if (!bbox.isEmpty()) {
			const sphere = bbox.getBoundingSphere(new THREE.Sphere());

			app.camera.near = (app.camera.isOrthographicCamera) ? 0 : 0.001 * sphere.radius;
			app.camera.far = 50 * sphere.radius;
			app.camera.updateProjectionMatrix();

			console.debug("[camera] near: " + app.camera.near + ", far: " + app.camera.far);
		}
	};

	// moves camera target to center of scene
	app.adjustCameraPosition = (force) => {
		if (!force) {
			app.render(true);

			// stay at current position if rendered objects exist
			const r = app.renderer.info.render;
			if (r.triangles + r.points + r.lines) return;
		}
		const bbox = app.scene.boundingBox(true);
		if (bbox.isEmpty()) return;

		bbox.getCenter(vec3);
		app.cameraAction.zoom(vec3.x, vec3.y, (bbox.max.z + vec3.z) / 2, app.scene.userData.baseExtent.width);
	};

	// declination: clockwise from +y, in degrees
	app.buildNorthArrow = (container, declination) => {
		container.style.display = "block";

		app.renderer2 = new THREE.WebGLRenderer({alpha: true, antialias: true});
		app.renderer2.setClearColor(0, 0);
		app.renderer2.setSize(container.clientWidth, container.clientHeight);

		app.container2 = container;
		app.container2.appendChild(app.renderer2.domElement);

		app.camera2 = new THREE.PerspectiveCamera(45, container.clientWidth / container.clientHeight, 1, 1000);
		app.camera2.position.set(0, 0, conf.northArrow.cameraDistance);
		app.camera2.up = app.camera.up;

		app.scene2 = new Q3DScene();
		app.scene2.buildLights(conf.lights.directional, 0);

		// an arrow object
		const vertices = [
			-5, -10, 0,
			 0,  10, 0,
			 0,  -7, 3,
			 5, -10, 0
		];

		const index = [
			0, 1, 2,
			2, 1, 3
		];

		const geometry = new THREE.BufferGeometry();
		geometry.setAttribute("position", new THREE.BufferAttribute(new Float32Array(vertices), 3));
		geometry.setIndex(index);

		const material = new THREE.MeshLambertMaterial({
			color: conf.northArrow.color,
			flatShading: true,
			side: THREE.DoubleSide
		});

		const mesh = new THREE.Mesh(geometry, material);
		if (declination) mesh.rotation.z = -declination * Q3D.deg2rad;

		app.scene2.add(mesh);
	};

	const anim_timer = new THREE.Timer();
	let _pupListenerAdded = false;
	app.buildViewHelper = (container) => {
		app.viewHelper = new THREE_EX.ViewHelper(app.camera, container);
		app.viewHelper.center = app.controls.target;
		app.viewHelper.setLabels("X", "Y", "Z");
		app.viewHelper.location.top = Q3D.Config.navigation.top;
		app.viewHelper.location.bottom = Q3D.Config.navigation.bottom;

		if (_pupListenerAdded) return;

		container.addEventListener("pointerup", (event) => {
			if (app.viewHelper && app.viewHelper.handleClick(event)) {
				anim_timer.update();
				requestAnimationFrame(app.animate);
			}
		});
		_pupListenerAdded = true;
	};

	app.currentViewUrl = () => {
		const c = app.scene.toMapCoordinates(app.camera.position);
		const t = app.scene.toMapCoordinates(app.controls.target);

		let hash = `#cx=${c.x.toFixed(3)}&cy=${c.y.toFixed(3)}&cz=${c.z.toFixed(3)}`;

		if (t.x || t.y || t.z) {
			hash += `&tx=${t.x.toFixed(3)}&ty=${t.y.toFixed(3)}&tz=${t.z.toFixed(3)}`;
		}
		return window.location.href.split("#")[0] + hash;
	};

	// enable the controls
	app.start = () => {
		if (app.controls) app.controls.enabled = true;
	};

	app.pause = () => {
		app.animation.isActive = false;
		if (app.controls) app.controls.enabled = false;
	};

	app.resume = () => {
		if (app.controls) app.controls.enabled = true;
	};

	// animation loop
	app.animate = () => {

		if (app.animation.isActive) {
			requestAnimationFrame(app.animate);

			if (app.animation.keyframes.isActive) TWEEN.update();
			else if (app.controls.enabled) app.controls.update();
		}
		else if (app.viewHelper && app.viewHelper.animating) {
			requestAnimationFrame(app.animate);

			anim_timer.update();
			app.viewHelper.update(anim_timer.getDelta());
		}

		app.render(true);
	};

	app.animation = {

		isActive: false,

		start: function () {
			this.isActive = true;
			app.animate();
		},

		stop: function () {
			this.isActive = false;
		},

		keyframes: {    // keyframe animation

			isActive: false,

			isPaused: false,

			curveFactor: 0,

			easingFunction: function (easing) {
				if (easing == 1) return TWEEN.Easing.Linear.None;
				if (easing > 1) {
					const f = TWEEN.Easing[Q3D.Config.animation.easingCurve];
					if (easing == 2) return f["InOut"];
					else if (easing == 3) return f["In"];
					else return f["Out"];   // easing == 4
				}
			},

			tracks: [],

			clear: function () {
				this.tracks = [];
			},

			load: function (track) {
				if (!Array.isArray(track)) track = [track];

				this.tracks = this.tracks.concat(track);
			},

			start: function () {

				const narBox = E("narrativebox");
				const btn = E("nextbtn");
				let currentNarElem;

				this.tracks.forEach((track) => {

					let tween;
					for (const p in Q3D.Tweens) {
						if (Q3D.Tweens[p].type == track.type) {
							tween = Q3D.Tweens[p];
							break;
						}
					}
					if (tween === undefined) {
						console.warn("unknown animation type: " + track.type);
						return;
					}

					const layer = (track.layerId !== undefined) ? app.scene.mapLayers[track.layerId] : undefined;

					track.completed = false;
					track.currentIndex = 0;
					track.prop_list = [];

					tween.init(track, layer);

					const keyframes = track.keyframes;

					const showNBox = (idx) => {
						// narrative box
						const n = keyframes[idx].narration;
						if (n && narBox) {
							if (currentNarElem) {
								currentNarElem.classList.remove("visible");
							}

							currentNarElem = E(n.id);
							if (currentNarElem) {
								currentNarElem.classList.add("visible");
							}
							else {    // preview
								E("narbody").innerHTML = n.text;
							}

							if (btn) {
								if (idx < keyframes.length - 1) {
									btn.className = "nextbtn";
									btn.innerHTML =  "";
								}
								else {
									btn.className = "";
									btn.innerHTML = "Close";
								}
							}

							setTimeout(() => {
								this.pause();
								narBox.classList.add("visible");
							}, 0);
						}
					};

					const onStart = () => {
						if (track.onStart) track.onStart();

						app.dispatchEvent({type: "tweenStarted", index: track.currentIndex});

						// pause if narrative box is shown
						if (narBox && narBox.classList.contains("visible")) {
							narBox.classList.remove("visible");
						}
					};

					const onComplete = (obj) => {
						if (!keyframes[track.currentIndex].easing) {
							track.onUpdate(obj, 1);
						}

						if (track.onComplete) track.onComplete(obj);

						const index = ++track.currentIndex;
						if (index == keyframes.length - 1) {
							track.completed = true;

							let completed = true;
							for (const t of this.tracks) {
								if (!t.completed) completed = false;
							}

							if (completed) {
								if (currentNarElem) {
									currentNarElem.classList.remove("visible");
								}

								if (conf.animation.repeat) {
									setTimeout(() => {
										this.start();
									}, 0);
								}
								else {
									this.stop();
								}
							}
						}

						// show narrative box if the current keyframe has a narrative content
						showNBox(index);
					};

					let t0, t1, t2;
					for (let i = 0; i < keyframes.length - 1; i++) {

						t2 = new TWEEN.Tween(track.prop_list[i]).delay(keyframes[i].delay).onStart(onStart)
										 .to(track.prop_list[i + 1], keyframes[i].duration).onComplete(onComplete);

						if (keyframes[i].easing) {
							t2.easing(this.easingFunction(keyframes[i].easing)).onUpdate(track.onUpdate);
						}

						if (i == 0) {
							t0 = t2;
						}
						else {
							t1.chain(t2);
						}
						t1 = t2;
					}

					showNBox(0);

					t0.start();
				});

				app.animation.isActive = this.isActive = true;
				app.dispatchEvent({type: "animationStarted"});
				app.animate();
			},

			stop: function () {

				TWEEN.removeAll();

				app.animation.isActive = this.isActive = this.isPaused = false;
				this._pausedTweens = null;

				app.dispatchEvent({type: "animationStopped"});
			},

			pause: function () {

				if (this.isPaused) return;

				this._pausedTweens = TWEEN.getAll();

				if (this._pausedTweens.length) {
					for (const pt of this._pausedTweens) {
						pt.pause();
					}
					this.isPaused = true;
				}
				app.animation.isActive = this.isActive = false;
			},

			resume: function () {

				const box = E("narrativebox");
				if (box && box.classList.contains("visible")) {
					box.classList.remove("visible");
				}

				if (!this.isPaused) return;

				for (const pt of this._pausedTweens) {
					pt.resume();
				}
				this._pausedTweens = null;

				app.animation.isActive = this.isActive = true;
				this.isPaused = false;

				app.animate();
			}
		},

		orbit: {      // orbit animation

			isActive: false,

			start: function () {

				app.controls.autoRotate = true;
				app.animation.isActive = this.isActive = true;

				app.animate();
			},

			stop: function () {

				app.controls.autoRotate = false;
				app.animation.isActive = this.isActive = false;
			}
		}
	};

	app.updateControlsAndRender = () => {
		app.controls.update();
		app.render();
	};

	let rafId = null;

	const renderImmediately = () => {
		app.render(true);
		rafId = null;
	};

	app.render = (immediate) => {
		if (!immediate) {
			if (rafId === null) {
				rafId = requestAnimationFrame(renderImmediately);
			}
			return;
		}

		if (app.camera.parent) {
			app.camera.updateMatrixWorld();
		}

		// rendering
		app.renderer.clear()
		if (app.effect) {
			app.effect.render(app.scene, app.camera);
		}
		else {
			app.renderer.render(app.scene, app.camera);
		}

		// North arrow
		if (app.renderer2) {
			app.scene2.quaternion.copy(app.camera.quaternion).invert();
			app.scene2.updateMatrixWorld();

			app.renderer2.render(app.scene2, app.camera2);
		}

		// navigation widget
		if (app.viewHelper) {
			app.viewHelper.render(app.renderer);
		}
	};

	(function () {
		let dly, rpt, times, id = null;
		const func = () => {
			app.render();
			if (rpt <= ++times) {
				clearInterval(id);
				id = null;
			}
		};
		app.setIntervalRender = (delay, repeat) => {
			if (id === null || delay != dly) {
				if (id !== null) {
					clearInterval(id);
				}
				id = setInterval(func, delay);
				dly = delay;
			}
			rpt = repeat;
			times = 0;
		};
	})();

	app.setLabelVisible = (visible) => {
		app.labelVisible = visible;
		app.scene.labelGroup.visible = visible;
		app.scene.labelConnectorGroup.visible = visible;
		app.render();
	};

	app.setRotateAnimationMode = (enabled) => {
		if (enabled) {
			app.animation.orbit.start();
		}
		else {
			app.animation.orbit.stop();
		}
	};

	app.setWireframeMode = (wireframe) => {
		if (wireframe == app._wireframeMode) return;

		for (const id in app.scene.mapLayers) {
			app.scene.mapLayers[id].setWireframeMode(wireframe);
		}

		app._wireframeMode = wireframe;
		app.render();
	};

	app.intersectObjects = (offsetX, offsetY) => {
		const vec2 = new THREE.Vector2((offsetX / app.width) * 2 - 1,
									  -(offsetY / app.height) * 2 + 1);
		const ray = new THREE.Raycaster();
		ray.params.Line.threshold = 0.5;
		ray.params.Points.threshold = 0.5;
		ray.setFromCamera(vec2, app.camera);
		return ray.intersectObjects(app.scene.visibleObjects(app.labelVisible));
	};

	app._offset = (elm) => {
		let top = 0, left = 0;
		do {
			top += elm.offsetTop || 0; left += elm.offsetLeft || 0; elm = elm.offsetParent;
		} while (elm);
		return {top: top, left: left};
	};

	app.queryTargetPosition = new THREE.Vector3();

	app.cameraAction = {

		move: function (x, y, z) {
			if (x === undefined) app.camera.position.copy(app.queryTargetPosition);
			else app.camera.position.set(x, y, z);

			app.updateControlsAndRender();
			app.cleanView();
		},

		vecZoom: new THREE.Vector3(0, -1, 1).normalize(),

		zoom: function (x, y, z, dist) {
			if (x === undefined) vec3.copy(app.queryTargetPosition);
			else vec3.set(x, y, z);

			if (dist === undefined) dist = app.scene.userData.baseExtent.width * 0.1;

			app.camera.position.copy(app.cameraAction.vecZoom).multiplyScalar(dist).add(vec3);
			app.camera.lookAt(vec3);
			if (app.controls.target !== undefined) app.controls.target.copy(vec3);
			app.updateControlsAndRender();
			app.cleanView();
		},

		zoomToLayer: function (layer) {
			if (!layer) return;

			const bbox = layer.boundingBox();
			bbox.getSize(vec3);
			const dist = Math.max(vec3.x, vec3.y * 3 / 4) * 1.2;

			bbox.getCenter(vec3);
			app.cameraAction.zoom(vec3.x, vec3.y, vec3.z, dist);
		},

		orbit: function (x, y, z) {
			if (app.controls.target === undefined) return;

			if (x === undefined) app.controls.target.copy(app.queryTargetPosition);
			else app.controls.target.set(x, y, z);

			app.setRotateAnimationMode(true);
			app.cleanView();
		}

	};

	app.cleanView = () => {
		gui.clean();

		app.scene.remove(app.queryMarker);
		app.highlightFeature(null);
		app.measure.clear();
		app.render();

		app.selectedLayer = null;

		if (app._canvasImageUrl) {
			URL.revokeObjectURL(app._canvasImageUrl);
			app._canvasImageUrl = null;
		}
	};

	app.highlightFeature = (object) => {
		if (app.highlightObject) {
			// remove highlight object from the scene
			app.scene.remove(app.highlightObject);
			app.selectedObject = null;
			app.highlightObject = null;
		}

		if (object === null) return;

		const layer = app.scene.mapLayers[object.userData.layerId];
		if (!layer || layer.type == Q3D.LayerType.DEM || layer.type == Q3D.LayerType.PointCloud) return;
		if (layer.properties.objType == "Billboard") return;

		// create a highlight object (if layer type is Point, slightly bigger than the object)
		const s = (layer.type == Q3D.LayerType.Point) ? 1.01 : 1;

		const clone = object.clone();
		clone.traverse((obj) => {
			obj.material = app.highlightMaterial;
		});
		if (s != 1) clone.scale.multiplyScalar(s);

		// add the highlight object to the scene
		app.scene.add(clone);

		app.selectedObject = object;
		app.highlightObject = clone;
	};

	app.canvasClicked = (e) => {

		// button 2: right click
		if (e.button == 2 && app.measure.isActive) {
			app.measure.removeLastPoint();
			return;
		}

		const canvasOffset = app._offset(app.renderer.domElement);
		for (const obj of app.intersectObjects(e.clientX - canvasOffset.left, e.clientY - canvasOffset.top)) {

			if (app.measure.isActive) {
				app.measure.addPoint(obj.point);
				return;
			}

			// get layerId of clicked object
			let o = obj.object;
			let layerId;
			while (o) {
				layerId = o.userData.layerId;
				if (layerId !== undefined) break;
				o = o.parent;
			}

			if (layerId === undefined) break;

			const layer = app.scene.mapLayers[layerId];
			if (!layer.clickable) break;

			app.selectedLayer = layer;
			app.queryTargetPosition.copy(obj.point);

			// query marker
			app.queryMarker.position.copy(obj.point);
			app.scene.add(app.queryMarker);

			if (o.userData.isLabel) {
				o = o.userData.objs[o.userData.partIdx];    // label -> object
			}

			app.highlightFeature(o);
			app.render();
			gui.showQueryResult(obj.point, layer, o, conf.coord.visible);

			return;
		}
		if (app.measure.isActive) return;

		app.cleanView();

		if (app.controls.autoRotate) {
			app.setRotateAnimationMode(false);
		}
	};

	app.saveCanvasImage = (width, height, fill_background, saveImageFunc) => {
		if (fill_background === undefined) fill_background = true;

		let old_size;
		if (width && height) {
			old_size = [app.width, app.height];
			app.setCanvasSize(width, height);
		}

		const saveBlob = (blob) => {
			const filename = "image.png";

			if (app._canvasImageUrl) URL.revokeObjectURL(app._canvasImageUrl);
			app._canvasImageUrl = URL.createObjectURL(blob);

			// display a link to save the image
			const e = document.createElement("a");
			e.className = "download-link";
			e.href = app._canvasImageUrl;
			e.download = filename;
			e.innerHTML = "Save";
			gui.popup.show("Click to save the image to a file." + e.outerHTML, "Image is ready");
		};

		const saveCanvasImage = saveImageFunc || ((canvas) => canvas.toBlob(saveBlob));

		const restoreCanvasSize = () => {
			if (old_size) app.setCanvasSize(old_size[0], old_size[1]);
			app.render();
		};

		// background option
		if (!fill_background) app.renderer.setClearColor(0, 0);

		// rendering
		app.renderer.clear()
		app.renderer.preserveDrawingBuffer = true;

		if (app.effect) {
			app.effect.render(app.scene, app.camera);
		}
		else {
			app.renderer.render(app.scene, app.camera);
		}

		// restore clear color
		const bgcolor = conf.bgColor;
		app.renderer.setClearColor(bgcolor || 0, (bgcolor === null) ? 0 : 1);

		if (fill_background && bgcolor === null) {
			const canvas = document.createElement("canvas");
			canvas.width = width;
			canvas.height = height;

			const ctx = canvas.getContext("2d");
			if (fill_background && bgcolor === null) {
				// render "sky-like" background
				const grad = ctx.createLinearGradient(0, 0, 0, height);
				grad.addColorStop(0, "#98c8f6");
				grad.addColorStop(0.4, "#cbebff");
				grad.addColorStop(1, "#f0f9ff");
				ctx.fillStyle = grad;
				ctx.fillRect(0, 0, width, height);
			}

			const image = new Image();
			image.onload = () => {
				ctx.drawImage(image, 0, 0, width, height);

				saveCanvasImage(canvas);
				restoreCanvasSize();
			};
			image.src = app.renderer.domElement.toDataURL("image/png");
		}
		else {
			saveCanvasImage(app.renderer.domElement);
			restoreCanvasSize();
		}
	};

	(function () {

		let path = [];

		app.measure = {

			isActive: false,

			precision: 3,

			start: function () {
				app.scene.remove(app.queryMarker);

				if (!this.geom) {
					var opt = conf.measure.marker;
					this.geom = new THREE.SphereGeometry(opt.radius, 32, 32);
					this.mtl = new THREE.MeshLambertMaterial({color: opt.color, opacity: opt.opacity, transparent: (opt.opacity < 1)});

					opt = conf.measure.line;
					this.lineMtl = new THREE.LineBasicMaterial({color: opt.color});
					this.markerGroup = new Q3DGroup();
					this.markerGroup.name = "measure marker";
					this.lineGroup = new Q3DGroup();
					this.lineGroup.name = "measure line";
				}

				this.isActive = true;

				app.scene.add(this.markerGroup);
				app.scene.add(this.lineGroup);

				this.addPoint(app.queryTargetPosition);
			},

			addPoint: function (pt) {
				// add a marker
				const marker = new THREE.Mesh(this.geom, this.mtl);
				marker.position.copy(pt);
				marker.onBeforeRender = app.queryMarker.onBeforeRender;

				this.markerGroup.updateMatrixWorld();
				this.markerGroup.add(marker);

				path.push(marker.position);

				if (path.length > 1) {
					// add a line
					const v = path[path.length - 2].toArray().concat(path[path.length - 1].toArray());
					const geom = new THREE.BufferGeometry().setAttribute("position", new THREE.Float32BufferAttribute(v, 3));
					const line = new THREE.Line(geom, this.lineMtl);
					this.lineGroup.add(line);
				}

				app.render();
				this.showResult();
			},

			removeLastPoint: function () {
				path.pop();
				this.markerGroup.children.pop();
				this.lineGroup.children.pop();

				app.render();

				if (path.length) this.showResult();
				else app.cleanView();
			},

			clear: function () {
				if (!this.isActive) return;

				this.markerGroup.clear();
				this.lineGroup.clear();

				app.scene.remove(this.markerGroup);
				app.scene.remove(this.lineGroup);

				path = [];
				this.isActive = false;
			},

			formatLength: function (length) {
				return (length) ? length.toFixed(this.precision) : 0;
			},

			showResult: function () {
				const vec2 = new THREE.Vector2();
				const zScale = app.scene.userData.zScale;
				let total = 0, totalxy = 0, dz = 0;
				if (path.length > 1) {
					let dxy;
					for (let i = path.length - 1; i > 0; i--) {
						dxy = vec2.copy(path[i]).distanceTo(path[i - 1]);
						dz = (path[i].z - path[i - 1].z) / zScale;

						total += Math.sqrt(dxy * dxy + dz * dz);
						totalxy += dxy;
					}
					dz = (path[path.length - 1].z - path[0].z) / zScale;
				}

				let html = '<table class="measure">';
				html += "<tr><td>Total distance:</td><td>" + this.formatLength(total) + " m</td><td></td></tr>";
				html += "<tr><td>Horizontal distance:</td><td>" + this.formatLength(totalxy) + " m</td><td></td></tr>";
				html += "<tr><td>Vertical difference:</td><td>" + this.formatLength(dz) + ' m</td><td><span class="tooltip tooltip-btn" data-tooltip="elevation difference between start point and end point">?</span></td></tr>';
				html += "</table>";

				gui.popup.show(html, "Measure distance");
			}
		};
	})();


	/*
	Q3D.gui
	*/
	const VIS = "visible";

	function CE(tagName, parent, innerHTML) {
		const elem = document.createElement(tagName);
		if (parent) parent.appendChild(elem);
		if (innerHTML) elem.innerHTML = innerHTML;
		return elem;
	}

	function ON_CLICK(id, listener) {
		const e = document.getElementById(id);
		if (e) e.addEventListener("click", listener);
	}

	gui.init = () => {
		// tool buttons
		ON_CLICK("layerbtn", () => {
			if (!gui.layerPanel.initialized) gui.layerPanel.init();

			if (gui.layerPanel.isVisible()) {
				gui.layerPanel.hide();
			}
			else {
				if (gui.popup.isVisible()) {
					gui.popup.hide();
				}
				gui.layerPanel.show();
			}
		});

		ON_CLICK("infobtn", () => {
			gui.layerPanel.hide();

			if (gui.popup.isVisible() && gui.popup.content == "pageinfo") gui.popup.hide();
			else gui.showInfo();
		});

		const btn = E("animbtn");
		if (conf.animation.enabled && btn) {
			const anim = app.animation.keyframes;

			const playButton = () => {
				btn.className = "playbtn";
			};

			const pauseButton = () => {
				btn.className = "pausebtn";
			};

			btn.onclick = () => {
				if (anim.isActive) {
					anim.pause();
					playButton();
				}
				else if (anim.isPaused) {
					anim.resume();
					pauseButton();
				}
				else anim.start();
			};

			app.addEventListener('animationStarted', pauseButton);
			app.addEventListener('animationStopped', playButton);
		}

		// popup
		ON_CLICK("closebtn", app.cleanView);
		ON_CLICK("zoomtolayer", () => app.cameraAction.zoomToLayer(app.selectedLayer));
		ON_CLICK("zoomtopoint", () => app.cameraAction.zoom());
		ON_CLICK("orbitbtn", () => app.cameraAction.orbit());
		ON_CLICK("measurebtn", () => app.measure.start());

		// narrative box
		ON_CLICK("nextbtn", () => app.animation.keyframes.resume());

		// attribution
		if (typeof proj4 === "undefined") {
			const e = E("lib_proj4js");
			if (e) e.classList.add("hidden");
		}

		// initialize modules
		for (const mod of gui.modules) {
			mod.init();
		}
	};

	gui.clean = () => {
		gui.popup.hide();
		if (gui.layerPanel.initialized) gui.layerPanel.hide();
	};

	gui.popup = {

		modal: false,

		content: null,

		timerId: null,

		isVisible: function () {
			return E("popup").classList.contains(VIS);
		},

		// show box
		// obj: html, element or content id ("queryresult" or "pageinfo")
		// modal: boolean
		// duration: int [milliseconds]
		show: function (obj, title, modal, duration) {

			if (modal) app.pause();
			else if (this.modal) app.resume();

			this.content = obj;
			this.modal = Boolean(modal);

			const e = E("layerpanel");
			if (e) e.classList.remove(VIS);

			const content = E("popupcontent");
			[content, E("queryresult"), E("pageinfo")].forEach((e) => {
				if (e) e.classList.remove(VIS);
			});

			if (obj == "queryresult" || obj == "pageinfo") {
				E(obj).classList.add(VIS);
			}
			else {
				if (obj instanceof HTMLElement) {
					content.innerHTML = "";
					content.appendChild(obj);
				}
				else {
					content.innerHTML = obj;
				}
				content.classList.add(VIS);
			}
			E("popupbar").innerHTML = title || "";
			E("popup").classList.add(VIS);

			if (this.timerId !== null) {
				clearTimeout(this.timerId);
				this.timerId = null;
			}

			if (duration) {
				this.timerId = setTimeout(() => gui.popup.hide(), duration);
			}
		},

		hide: function () {
			E("popup").classList.remove(VIS);
			if (this.timerId !== null) clearTimeout(this.timerId);
			this.timerId = null;
			this.content = null;
			if (this.modal) app.resume();
		}

	};

	gui.showInfo = () => {
		const e = E("urlbox");
		if (e) e.value = app.currentViewUrl();
		gui.popup.show("pageinfo");
	};

	gui.showQueryResult = (point, layer, obj, show_coords) => {
		let e;
		// layer name
		e = E("qr_layername");
		if (layer && e) e.innerHTML = layer.properties.name;

		// clicked coordinates
		e = E("qr_coords_table");
		if (e) {
			if (show_coords) {
				e.classList.remove("hidden");

				const pt = app.scene.toMapCoordinates(point);

				e = E("qr_coords");

				if (conf.coord.latlon) {
					const lonLat = proj4(app.scene.userData.proj).inverse([pt.x, pt.y]);
					e.innerHTML = Q3D.Utils.convertToDMS(lonLat[1], lonLat[0]) + ", Elev. " + pt.z.toFixed(2);
				}
				else {
					e.innerHTML = [pt.x.toFixed(2), pt.y.toFixed(2), pt.z.toFixed(2)].join(", ");
				}
			}
			else {
				e.classList.add("hidden");
			}
		}

		e = E("qr_attrs_table");
		if (e) {
			for (let i = e.children.length - 1; i >= 0; i--) {
				if (e.children[i].tagName.toUpperCase() == "TR") e.removeChild(e.children[i]);
			}

			if (layer && layer.properties.propertyNames !== undefined) {
				for (let i = 0, l = layer.properties.propertyNames.length; i < l; i++) {
					const row = document.createElement("tr");
					row.innerHTML = "<td>" + layer.properties.propertyNames[i] + "</td>" +
									"<td>" + obj.userData.properties[i] + "</td>";
					e.appendChild(row);
				}
				e.classList.remove("hidden");
			}
			else {
				e.classList.add("hidden");
			}
		}
		gui.popup.show("queryresult");
	};

	gui.showPrintDialog = () => {

		var f = CE("form");
		f.className = "print";

		var d1 = CE("div", f, "Image Size");
		d1.style.textDecoration = "underline";

		var d2 = CE("div", f),
			l1 = CE("label", d2, "Width:"),
			width = CE("input", d2);
		d2.style.cssFloat = "left";
		l1.htmlFor = width.id = width.name = "printwidth";
		width.type = "text";
		width.value = app.width;
		CE("span", d2, "px,");

		var d3 = CE("div", f),
			l2 = CE("label", d3, "Height:"),
			height = CE("input", d3);
		l2.htmlFor = height.id = height.name = "printheight";
		height.type = "text";
		height.value = app.height;
		CE("span", d3, "px");

		var d4 = CE("div", f),
			ka = CE("input", d4);
		ka.type = "checkbox";
		ka.checked = true;
		CE("span", d4, "Keep Aspect Ratio");

		var d5 = CE("div", f, "Option");
		d5.style.textDecoration = "underline";

		var d6 = CE("div", f),
			bg = CE("input", d6);
		bg.type = "checkbox";
		bg.checked = true;
		CE("span", d6, "Fill Background");

		var d7 = CE("div", f),
			ok = CE("span", d7, "OK"),
			cancel = CE("span", d7, "Cancel");
		d7.className = "buttonbox";

		CE("input", f).type = "submit";

		// event handlers
		// width and height boxes
		var aspect = app.width / app.height;

		width.oninput = () => {
			if (ka.checked) height.value = Math.round(width.value / aspect);
		};

		height.oninput = () => {
			if (ka.checked) width.value = Math.round(height.value * aspect);
		};

		ok.onclick = () => {
			gui.popup.show("Rendering...");
			window.setTimeout(() => app.saveCanvasImage(width.value, height.value, bg.checked), 10);
		};

		cancel.onclick = app.cleanView;

		// enter key pressed
		f.onsubmit = () => {
			ok.onclick();
			return false;
		};

		gui.popup.show(f, "Save Image", true);   // modal
	};

	gui.layerPanel = {

		init: function () {
			const panel = E("layerpanel");
			app.scene.forEachLayer((layer, layerId) => {
				const p = layer.properties;
				const item = CE("div", panel);
				item.className = "layer";

				// visible
				let e = CE("div", item, "<input type='checkbox'" +  ((p.visible) ? " checked" : "") + ">" + p.name);
				e.querySelector("input[type=checkbox]").addEventListener("change", function () {
					layer.visible = this.checked;
				});

				// material dropdown
				let select;
				if (p.mtlNames && p.mtlNames.length > 1) {
					select = CE("select", CE("div", item, "Material: "));
					for (var i = 0; i < p.mtlNames.length; i++) {
						CE("option", select, p.mtlNames[i]).setAttribute("value", i);
					}
					select.value = p.mtlIdx;
				}

				// opacity slider
				e = CE("div", item, "Opacity: <input type='range'><output></output>");
				const slider = e.querySelector("input[type=range]");
				const label = e.querySelector("output");
				const setLabel = (opacity) => {
					label.innerHTML = opacity + " %";
				};

				const o = Math.round(layer.opacity * 100);
				slider.value = o;
				setLabel(o);

				slider.addEventListener("input", function () {
					setLabel(this.value);
				});
				slider.addEventListener("change", function () {
					setLabel(this.value);
					layer.opacity = this.value / 100;
				});

				if (select) {
					select.addEventListener("change", function () {
						layer.currentMtlIndex = this.value;
						const o = Math.round(layer.opacity * 100);
						slider.value = o;
						setLabel(o);
					});
				}
			});
			gui.layerPanel.initialized = true;
		},

		isVisible: function () {
			return E("layerpanel").classList.contains(VIS);
		},

		show: function () {
			E("layerpanel").classList.add(VIS);
		},

		hide: function () {
			E("layerpanel").classList.remove(VIS);
		}

	};

})();


// Q3D classes

class Q3DGroup extends THREE.Group {

	add(object) {
		super.add(object);
		object.updateMatrixWorld();
		return this;
	}

	clear() {
		for (let i = this.children.length - 1; i >= 0; i--) {
			this.remove(this.children[i]);
		}
		return this;
	}

}


/*
Q3DScene
.userData
	- baseExtent(cx, cy, width, height, rotation): map base extent in map coordinates. center is (cx, cy).
	- origin: origin of 3D world in map coordinates
	- zScale: vertical scale factor
	- proj: (optional) proj string. used to display clicked position in long/lat.
*/
class Q3DScene extends THREE.Scene {

	constructor() {
		super();

		this.autoUpdate = false;

		this.mapLayers = {};    // map layers. key is layerId.

		this.lightGroup = new Q3DGroup();
		this.lightGroup.name = "light";
		this.add(this.lightGroup);

		this.labelGroup = new Q3DGroup();
		this.labelGroup.name = "label";
		this.add(this.labelGroup);

		this.labelConnectorGroup = new Q3DGroup();
		this.labelConnectorGroup.name = "label connector";
		this.add(this.labelConnectorGroup);
	}

	add(object) {
		super.add(object);
		object.updateMatrixWorld();
		return this;
	}

	forEachLayer(callback) {
		for (const layerId in this.mapLayers) {
			callback(this.mapLayers[layerId], layerId);
		}
	}

	loadData(data) {
		if (data.type == "scene") {
			const p = data.properties;
			if (p !== undefined) {
				// fog
				if (p.fog) {
					this.fog = new THREE.FogExp2(p.fog.color, p.fog.density);
				}

				// light
				const rotation0 = (this.userData.baseExtent) ? this.userData.baseExtent.rotation : 0;
				if (p.light != this.userData.light || p.baseExtent.rotation != rotation0) {
					this.lightGroup.clear();
					this.buildLights(Q3D.Config.lights[p.light] || Q3D.Config.lights.directional, p.baseExtent.rotation);
					this.dispatchEvent({type: "lightChanged", light: p.light});
				}

				const be = p.baseExtent;
				p.pivot = new THREE.Vector3(be.cx, be.cy, p.origin.z).sub(p.origin);   // 2D center of extent in 3D world coordinates

				// set initial camera position and parameters
				if (this.userData.origin === undefined) {

					const s = be.width;
					let v = Q3D.Config.viewpoint;
					let pos, focal;

					if (v.pos === undefined) {
						v = v.default;
						if (be.rotation) {
							v = {
								pos: v.pos.clone().applyAxisAngle(Q3D.uv.k, be.rotation * Q3D.deg2rad),
								lookAt: v.lookAt.clone().applyAxisAngle(Q3D.uv.k, be.rotation * Q3D.deg2rad)
							};
						}
						pos = v.pos.clone().multiplyScalar(s).add(p.pivot);
						focal = v.lookAt.clone().multiplyScalar(s).add(p.pivot);
					}
					else {
						pos = new THREE.Vector3().copy(v.pos).sub(p.origin);
						focal = new THREE.Vector3().copy(v.lookAt).sub(p.origin);
					}

					pos.z *= p.zScale;
					focal.z *= p.zScale;

					const near = 0.001 * s,
						  far = 100 * s;

					this.requestCameraUpdate(pos, focal, near, far);
				}

				if (p.baseExtent.rotation != rotation0) {
					this.dispatchEvent({type: "mapRotationChanged", rotation: p.baseExtent.rotation});
				}

				this.userData = p;
			}

			// load layers
			if (data.layers !== undefined) {
				data.layers.forEach((layer) => this.loadData(layer));
			}
		}
		else if (data.type == "layer") {
			let layer = this.mapLayers[data.id];
			if (layer === undefined) {
				// create a layer
				const type = data.properties.type;
				if (type == "dem") layer = new Q3DDEMLayer();
				else if (type == "point") layer = new Q3DPointLayer();
				else if (type == "line") layer = new Q3DLineLayer();
				else if (type == "polygon") layer = new Q3DPolygonLayer();
				else {
					console.error("unknown layer type:" + type);
					return;
				}
				layer.id = data.id;
				layer.objectGroup.userData.layerId = data.id;
				layer.addEventListener("renderRequest", this.requestRender.bind(this));

				this.mapLayers[data.id] = layer;
				this.add(layer.objectGroup);
			}

			layer.loadData(data, this);

			this.requestRender();
		}
		else if (data.type == "block") {
			const layer = this.mapLayers[data.layer];
			if (layer === undefined) return;

			layer.loadData(data, this);

			this.requestRender();
		}
	}

	buildLights(lights, rotation) {
		let light;
		for (const p of lights) {
			if (p.type == "ambient") {
				light = new THREE.AmbientLight(p.color, p.intensity);
			}
			else if (p.type == "directional") {
				light = new THREE.DirectionalLight(p.color, p.intensity);
				light.position.copy(Q3D.uv.j)
							  .applyAxisAngle(Q3D.uv.i, p.altitude * Q3D.deg2rad)
							  .applyAxisAngle(Q3D.uv.k, (rotation - p.azimuth) * Q3D.deg2rad);
			}
			else if (p.type == "point") {
				light = new THREE.PointLight(p.color, p.intensity, 0, p.decay);
				light.position.set(0, 0, p.height);
			}
			else {
				continue;
			}
			this.lightGroup.add(light);
		}
	}

	requestRender() {
		this.dispatchEvent({type: "renderRequest"});
	}

	requestCameraUpdate(pos, focal, near, far) {
		this.dispatchEvent({type: "cameraUpdateRequest", pos: pos, focal: focal, near: near, far: far});
	}

	visibleObjects(labelVisible) {
		let objs = [];

		for (const id in this.mapLayers) {
			const layer = this.mapLayers[id];
			if (!layer.visible) continue;

			objs = objs.concat(layer.visibleObjects());

			if (labelVisible && layer.labels) {
				objs = objs.concat(layer.labels);
			}
		}

		return objs;
	}

	// 3D world coordinates to map coordinates
	toMapCoordinates(pt) {
		const p = this.userData;
		return {
			x: p.origin.x + pt.x,
			y: p.origin.y + pt.y,
			z: p.origin.z + pt.z / p.zScale
		};
	}

	// map coordinates to 3D world coordinates
	toWorldCoordinates(pt, isLonLat) {
		const p = this.userData;
		if (isLonLat && typeof proj4 !== "undefined") {
			// WGS84 long,lat to map coordinates
			var t = proj4(p.proj).forward([pt.x, pt.y]);
			pt = {x: t[0], y: t[1], z: pt.z};
		}

		return {
			x: pt.x - p.origin.x,
			y: pt.y - p.origin.y,
			z: (pt.z - p.origin.z) * p.zScale
		};
	}

	// return bounding box in 3d world coordinates
	boundingBox(only_visible) {
		const box = new THREE.Box3();
		for (const id in this.mapLayers) {
			if (only_visible && !this.mapLayers[id].visible) continue;

			const b = this.mapLayers[id].boundingBox();
			if (b) box.union(b);
		}
		return box;
	}

}


class Q3DMaterial {

	constructor() {
		this.loaded = false;
	}

	// material: a THREE.Material-based object
	set(material) {
		this.mtl = material;
		this.origProp = {};
		return this;
	}

	// callback is called when material has been completely loaded
	loadData(data, callback) {
		this.origProp = data;
		this.groupId = data.mtlIndex;

		const m = data;
		const opt = {};
		let defer = false;

		if (m.ds) opt.side = THREE.DoubleSide;

		if (m.flat) opt.flatShading = true;

		// texture
		if (m.image !== undefined) {
			if (m.image.url !== undefined) {
				opt.map = Q3D.application.loadTextureFile(m.image.url, () => {
					this._loadCompleted(callback);
				});
				defer = true;
			}
			else {    // base64
				opt.map = new THREE.TextureLoader(Q3D.application.loadingManager).load(m.image.base64);
				defer = true;
				delete m.image.base64;
			}
			opt.map.anisotropy = Q3D.Config.texture.anisotropy;
			opt.map.colorSpace = THREE.SRGBColorSpace;
		}

		if (m.c !== undefined) opt.color = m.c;

		if (m.o !== undefined && m.o < 1) {
			opt.opacity = m.o;
			opt.transparent = true;
		}

		if (m.t) opt.transparent = true;

		if (m.w) opt.wireframe = true;

		if (m.bm) {
			this.mtl = new THREE.MeshBasicMaterial(opt);
		}
		else if (m.type == Q3D.MaterialType.MeshLambert) {
			this.mtl = new THREE.MeshLambertMaterial(opt);
		}
		else if (m.type == Q3D.MaterialType.MeshPhong) {
			this.mtl = new THREE.MeshPhongMaterial(opt);
		}
		else if (m.type == Q3D.MaterialType.MeshToon) {
			this.mtl = new THREE.MeshToonMaterial(opt);
		}
		else if (m.type == Q3D.MaterialType.Point) {
			opt.size = m.s;
			this.mtl = new THREE.PointsMaterial(opt);
		}
		else if (m.type == Q3D.MaterialType.Line) {

			if (m.dashed) {
				opt.dashSize = Q3D.Config.line.dash.dashSize;
				opt.gapSize = Q3D.Config.line.dash.gapSize;
				this.mtl = new THREE.LineDashedMaterial(opt);
			}
			else {
				this.mtl = new THREE.LineBasicMaterial(opt);
			}
		}
		else if (m.type == Q3D.MaterialType.MeshLine) {

			opt.lineWidth = m.thickness;
			if (m.dashed) {
				opt.dashArray = 0.03;
				opt.dashRatio = 0.45;
				opt.dashOffset = 0.015;
				opt.transparent = true;
			}
			// opt.sizeAttenuation = 1;

			this.mtl = new THREE_EX.meshline.MeshLineMaterial(opt);
			this._updateAspect = () => {
				this.mtl.resolution.set(Q3D.application.width, Q3D.application.height);
			};

			this._updateAspect();
			Q3D.application.addEventListener("canvasSizeChanged", this._updateAspect);
		}
		else if (m.type == Q3D.MaterialType.Sprite) {
			opt.color = 0xffffff;
			this.mtl = new THREE.SpriteMaterial(opt);
		}
		else {
			if (m.roughness !== undefined) opt.roughness = m.roughness;
			if (m.metalness !== undefined) opt.metalness = m.metalness;

			this.mtl = new THREE.MeshStandardMaterial(opt);
		}

		if (!defer) this._loadCompleted(callback);
	}

	_loadCompleted(anotherCallback) {
		this.loaded = true;

		if (this._callbacks !== undefined) {
			for (const callback of this._callbacks) {
				callback();
			}
			this._callbacks = [];
		}

		if (anotherCallback) anotherCallback();
	}

	callbackOnLoad(callback) {
		if (this.loaded) return callback();

		if (this._callbacks === undefined) this._callbacks = [];
		this._callbacks.push(callback);
	}

	dispose() {
		if (!this.mtl) return;

		if (this.mtl.map) this.mtl.map.dispose();   // dispose of texture
		this.mtl.dispose();
		this.mtl = null;

		if (this._updateAspect) {
			Q3D.application.removeEventListener("canvasSizeChanged", this._updateAspect);
			this._updateAspect = undefined;
		}
	}
}


class Q3DMaterials extends THREE.EventDispatcher {

	constructor() {
		super();
		this.array = [];
	}

	// material: instance of Q3DMaterial object or THREE.Material-based object
	add(material) {
		if (material instanceof Q3DMaterial) {
			this.array.push(material);
		}
		else {
			this.array.push(new Q3DMaterial().set(material));
		}
	}

	get(index) {
		return this.array[index];
	}

	mtl(index) {
		return this.array[index].mtl;
	}

	loadData(data) {
		let iterated = false;

		const callback = () => {
			if (iterated) this.dispatchEvent({type: "renderRequest"});
		};

		for (const m of data) {
			const mtl = new Q3DMaterial();
			mtl.loadData(m, callback);
			this.add(mtl);
		}
		iterated = true;
	}

	dispose() {
		for (const m of this.array) {
			m.dispose();
		}
		this.array = [];
	}

	addFromObject3D(object) {
		const materials = new Set();

		object.traverse((obj) => {
			if (obj.material === undefined) return;

			for (const material of (Array.isArray(obj.material) ? obj.material : [obj.material])) {
				materials.add(material);
			}
		});

		for (const material of materials) {
			this.array.push(new Q3DMaterial().set(material));
		}
	}

	// opacity
	opacity() {
		if (this.array.length == 0) return 1;

		let sum = 0;
		for (const m of this.array) {
			sum += m.mtl.opacity;
		}
		return sum / this.array.length;
	}

	setOpacity(opacity) {
		for (const m of this.array) {
			m.mtl.opacity = opacity;

			const t = Boolean(m.origProp.t) || (opacity < 1);
			if (m.mtl.transparent !== t) {
				m.mtl.transparent = t;
				m.mtl.needsUpdate = true;
			}
		}
	}

	// wireframe: boolean
	setWireframeMode(wireframe) {
		for (const m of this.array) {
			if (m.origProp.w || m.mtl instanceof THREE.LineBasicMaterial) continue;
			m.mtl.wireframe = wireframe;
		}
	}

	removeItem(material, dispose) {
		for (let i = this.array.length - 1; i >= 0; i--) {
			if (this.array[i].mtl === material) {
				this.array.splice(i, 1);
				break;
			}
		}
		if (dispose) material.dispose();
	}

	removeItemsByGroupId(groupId) {
		for (let i = this.array.length - 1; i >= 0; i--) {
			if (this.array[i].groupId === groupId) {
				this.array.splice(i, 1);
			}
		}
	}

}


/*
 The GridGeometry class is almost the same as PlaneGeometry, but it does not
 generate triangles that include vertices with no-data values.

 It supports tile mode. When the grid has margin areas (right/bottom)
 with no actual data, pass `segments` explicitly so that UV coordinates
 are calculated based on the full tile extent rather than only the
 data-containing region.
*/
class GridGeometry extends THREE.BufferGeometry {

	constructor() {
		super();
		this.type = 'GridGeometry';
	}

	/**
	 * @param {object} grid
	 * @param {number} width      - Plane width (or tile size).
	 * @param {number} height     - Plane height (ignored when `segments` is given).
	 * @param {number} [segments] - When supplied, the grid is treated as a square tile.
	 */
	loadData(grid, width, height, segments) {
		const grid_values = grid.values;
		const columns = grid.width;		// number of columns of actual grid data
		const rows = grid.height;		// number of rows of actual grid data
		const nodata = (grid.nodata === undefined) ? undefined : new Float32Array(Q3D.Utils.base64ToUint8Array(grid.nodata).buffer)[0];

		const isTileMode = (segments !== undefined);
		const segmentsX = (isTileMode) ? segments : columns - 1;
		const segmentsY = (isTileMode) ? segments : rows - 1;
		const segment_width = width / segmentsX;
		const segment_height = ((isTileMode) ? width : height) / segmentsY;
		const half_w = width / 2;
		const half_h = ((isTileMode) ? width : height) / 2;

		const indices = [];
		const vertices = [];
		const uvs = [];

		for (let iy = 0; iy < rows; iy++) {

			const y = iy * segment_height - half_h;
			const v = 1 - (iy / segmentsY);

			for (let ix = 0; ix < columns; ix++) {

				const x = ix * segment_width - half_w;
				const i = ix + iy * columns;
				const z = grid_values[i];

				vertices.push(x, -y, (z === nodata) ? 0 : z);
				uvs.push(ix / segmentsX, v);

				if (ix === 0 || iy === 0) continue;

				const a = i - columns - 1;
				const b = i - 1;
				const c = i;
				const d = i - columns;

				if (grid_values[b] === nodata || grid_values[d] === nodata) continue;
				if (grid_values[a] !== nodata) indices.push(a, b, d);
				if (z !== nodata) indices.push(b, c, d);
			}
		}

		this.setIndex(indices);
		this.setAttribute('position', new THREE.Float32BufferAttribute(vertices, 3));
		this.setAttribute('uv', new THREE.Float32BufferAttribute(uvs, 2));
		this.computeBoundingSphere();
		this.computeBoundingBox();
		this.computeVertexNormals();
	}
}


class Q3DDEMBlockBase {

	constructor() {
		this.obj = null;
		this.materials = [];
		this.currentMtlIndex = 0;
	}

	loadData(data, layer, callback) {
		this.data = data;

		// load material
		for (const m of data.materials || []) {
			const mtl = new Q3DMaterial();
			mtl.loadData(m, () => layer.requestRender());
			this.materials[m.mtlIndex] = mtl;

			if (m.useNow) {
				this.currentMtlIndex = m.mtlIndex;
				if (this.obj) {
					layer.materials.removeItem(this.obj.material, true);

					this.obj.material = mtl.mtl;
					layer.requestRender();
				}
				layer.materials.add(mtl);
			}
		}
	}

	/**
	 * @returns {{x0: number, y0: number, x1: number, y1: number, xres: number, yres: number}}
	 */
	_auxArgs() {
		return {x0: 0, y0: 0, x1: 0, y1: 0, xres: 0, yres: 0};
	}

	buildSides(layer, parent, material, z0) {
		const {values: gridValues, width: w, height: h} = this.data.grid;
		const {x0, y0, x1, y1} = this._auxArgs();

		const planeWidth = x1 - x0;
		const planeHeight = y0 - y1;
		const cx = (x0 + x1) / 2;
		const cy = (y0 + y1) / 2;

		const k = w * (h - 1);
		const bandWidth = -2 * z0;

		// front and back
		const geomFr = new THREE.PlaneGeometry(planeWidth, bandWidth, w - 1, 1);
		const geomBa = geomFr.clone();

		const verticesFr = geomFr.attributes.position.array;
		const verticesBa = geomBa.attributes.position.array;

		for (let i = 0; i < w; i++) {
			verticesFr[i * 3 + 1] = gridValues[k + i];
			verticesBa[i * 3 + 1] = gridValues[w - 1 - i];
		}

		const meshFr = new THREE.Mesh(geomFr, material);
		meshFr.rotation.x = Math.PI / 2;
		meshFr.position.x = cx;
		meshFr.position.y = y1;
		meshFr.name = "side";
		parent.add(meshFr);

		const meshBa = new THREE.Mesh(geomBa, material);
		meshBa.rotation.x = Math.PI / 2;
		meshBa.rotation.y = Math.PI;
		meshBa.position.x = cx;
		meshBa.position.y = y0;
		meshBa.name = "side";
		parent.add(meshBa);

		// left and right
		const geomLe = new THREE.PlaneGeometry(bandWidth, planeHeight, 1, h - 1);
		const geomRi = geomLe.clone();

		const verticesLe = geomLe.attributes.position.array;
		const verticesRi = geomRi.attributes.position.array;

		for (let i = 0; i < h; i++) {
			verticesLe[(i * 2 + 1) * 3] = gridValues[w * i];
			verticesRi[i * 2 * 3] = -gridValues[w * (i + 1) - 1];
		}

		const meshLe = new THREE.Mesh(geomLe, material);
		meshLe.rotation.y = -Math.PI / 2;
		meshLe.position.x = x0;
		meshLe.position.y = cy;
		meshLe.name = "side";
		parent.add(meshLe);

		const meshRi = new THREE.Mesh(geomRi, material);
		meshRi.rotation.y = Math.PI / 2;
		meshRi.position.x = x1;
		meshRi.position.y = cy;
		meshRi.name = "side";
		parent.add(meshRi);

		// bottom
		const geom = new THREE.PlaneGeometry(planeWidth, planeHeight);
		const mesh = new THREE.Mesh(geom, material);
		mesh.rotation.x = Math.PI;
		mesh.position.set(cx, cy, z0);
		mesh.name = "bottom";
		parent.add(mesh);

		parent.updateMatrixWorld();
	}

	addEdges(layer, parent, material, z0) {
		const {values: gridValues, width: w, height: h} = this.data.grid;
		const {x0, y0, x1, y1, xres, yres} = this._auxArgs();

		const k = w * (h - 1);

		// terrain edges
		const vlFr = [];
		const vlBk = [];
		const vlLe = [];
		const vlRi = [];

		for (let i = 0; i < w; i++) {
			const x = x0 + xres * i;
			vlFr.push(x, y1, gridValues[k + i]);
			vlBk.push(x, y0, gridValues[i]);
		}

		for (let i = 0; i < h; i++) {
			const y = y0 - yres * i;
			vlLe.push(x0, y, gridValues[w * i]);
			vlRi.push(x1, y, gridValues[w * (i + 1) - 1]);
		}

		const verticesList = [vlFr, vlBk, vlLe, vlRi];

		if (z0 !== undefined) {
			// horizontal rectangle at bottom
			verticesList.push([
				x0, y0, z0,
				x1, y0, z0,
				x1, y1, z0,
				x0, y1, z0,
				x0, y0, z0
			]);

			// vertical lines at corners
			[
				[x0, y1, gridValues.at(-w)],
				[x1, y1, gridValues.at(-1)],
				[x1, y0, gridValues[w - 1]],
				[x0, y0, gridValues[0]]
			].forEach(([x, y, z]) => {
				verticesList.push([x, y, z, x, y, z0]);
			});
		}

		for (const vertices of verticesList) {
			const geom = new THREE.BufferGeometry().setAttribute("position", new THREE.Float32BufferAttribute(vertices, 3));

			const line = new THREE.Line(geom, material);
			line.name = "frame";
			parent.add(line);
		}

		parent.updateMatrixWorld();
	}

	// add quad wireframe
	addWireframe(layer, parent, material) {
		const {values: gridValues, width: w, height: h} = this.data.grid;
		const {x0, y0, xres, yres} = this._auxArgs();

		const group = new THREE.Group();

		for (let x = w - 1; x >= 0; x--) {
			const vertices = [];
			const vx = x0 + xres * x;

			for (let y = h - 1; y >= 0; y--) {
				vertices.push(vx, y0 - yres * y, gridValues[x + w * y]);
			}

			const geom = new THREE.BufferGeometry().setAttribute("position", new THREE.Float32BufferAttribute(vertices, 3));

			group.add(new THREE.Line(geom, material));
		}

		for (let y = h - 1; y >= 0; y--) {
			const vertices = [];
			const vy = y0 - yres * y;

			for (let x = w - 1; x >= 0; x--) {
				vertices.push(x0 + xres * x, vy, gridValues[x + w * y]);
			}

			const geom = new THREE.BufferGeometry().setAttribute("position", new THREE.Float32BufferAttribute(vertices, 3));

			group.add(new THREE.Line(geom, material));
		}

		parent.add(group);
		parent.updateMatrixWorld();
	}
}


class Q3DDEMBlock extends Q3DDEMBlockBase {

	loadData(data, layer, callback) {
		super.loadData(data, layer, callback);

		if (data.grid === undefined) return;

		const geom = new GridGeometry();
		const mesh = new THREE.Mesh(geom, (this.materials[this.currentMtlIndex] || {}).mtl);
		mesh.position.fromArray(data.translate);
		mesh.scale.z = data.zScale;
		layer.addObject(mesh);

		const buildGeometry = (grid) => {
			geom.loadData(grid, data.width, data.height);
			if (callback) callback(mesh);
		};

		const grid = data.grid;
		if (grid.url !== undefined) {
			Q3D.application.loadFile(grid.url, "arraybuffer", (buf) => {
				grid.values = new Float32Array(buf);
				buildGeometry(grid);
			});
		}
		else {
			if (grid.base64 !== undefined) {
				const bytes = Q3D.Utils.base64ToUint8Array(grid.base64);
				grid.values = new Float32Array(bytes.buffer);
				delete grid.base64;
			}
			buildGeometry(grid);
		}

		this.obj = mesh;
		return mesh;
	}

	_auxArgs() {
		const pw = this.data.width,
			  ph = this.data.height;
		return {
			x0: -pw / 2,
			y0: ph / 2,
			x1: pw / 2,
			y1: -ph / 2,
			xres: pw / (this.data.grid.width - 1),
			yres: ph / (this.data.grid.height - 1)
		}
	}
}


class Q3DDEMTileBlock extends Q3DDEMBlockBase {

	loadData(data, layer, callback) {
		const grid = data.grid;

		super.loadData(data, layer, callback);

		if (grid === undefined) return;

		const geom = new GridGeometry();
		const mesh = new THREE.Mesh(geom, (this.materials[this.currentMtlIndex] || {}).mtl);
		mesh.position.fromArray(data.translate);
		mesh.scale.z = data.zScale;
		layer.addObject(mesh);

		const buildGeometry = (grid) => {
			geom.loadData(grid, data.tileSize, data.tileSize, data.segments);
			if (callback) callback(mesh);
		};

		if (grid.url !== undefined) {
			Q3D.application.loadFile(grid.url, "arraybuffer", (buf) => {
				grid.values = new Float32Array(buf);
				buildGeometry(grid);
			});
		}
		else {
			if (grid.base64 !== undefined) {
				const bytes = Q3D.Utils.base64ToUint8Array(grid.base64);
				grid.values = new Float32Array(bytes.buffer);
				delete grid.base64;
			}
			buildGeometry(grid);
		}

		this.obj = mesh;
		return mesh;
	}

	_auxArgs() {
		const res = this.data.tileSize / this.data.segments;
		const pw = (this.data.grid.width - 1) * res;
		const ph = (this.data.grid.height - 1) * res;
		return {
			x0: -this.data.tileSize / 2,
		    y0: this.data.tileSize / 2,
			x1: pw - this.data.tileSize / 2,
			y1: this.data.tileSize / 2 - ph,
			xres: res,
			yres: res
		};
	}
}


class Q3DClippedDEMBlock extends Q3DDEMBlockBase {

	loadData(data, layer, callback) {
		super.loadData(data, layer, callback);

		if (data.geom === undefined) return;

		const geom = new THREE.BufferGeometry();
		const mesh = new THREE.Mesh(geom, (this.materials[this.currentMtlIndex] || {}).mtl);
		mesh.position.fromArray(data.translate);
		mesh.scale.z = data.zScale;
		layer.addObject(mesh);

		const buildGeometry = (obj) => {

			const v = obj.triangles.v;
			const normals = [];
			const uvs = [];

			let origin = layer.sceneData.origin,
				be = layer.sceneData.baseExtent,
				base_width = be.width,
				base_height = be.height,
				x0 = be.cx - origin.x - base_width * 0.5,
				y0 = be.cy - origin.y - base_height * 0.5;

			for (let i = 0, l = v.length; i < l; i += 3) {
				normals.push(0, 0, 1);
				uvs.push((v[i] - x0) / base_width, (v[i + 1] - y0) / base_height);
			}

			geom.setIndex(obj.triangles.f);
			geom.setAttribute("position", new THREE.Float32BufferAttribute(v, 3));
			geom.setAttribute("normal", new THREE.Float32BufferAttribute(normals, 3));
			geom.setAttribute("uv", new THREE.Float32BufferAttribute(uvs, 2));
			geom.computeVertexNormals();

			geom.attributes.position.needsUpdate = true;
			geom.attributes.normal.needsUpdate = true;
			geom.attributes.uv.needsUpdate = true;

			this.data.polygons = obj.polygons;
			if (callback) callback(mesh);
		};

		if (data.geom.url !== undefined) {
			Q3D.application.loadFile(data.geom.url, "json", obj => buildGeometry(obj));
		}
		else {    // preview
			buildGeometry(data.geom);
		}

		this.obj = mesh;
		return mesh;
	}

	buildSides(layer, parent, material, z0) {
		const bzFunc = (_x, _y) => z0;

		// make back-side material for bottom
		const mat_back = material.clone();
		mat_back.side = THREE.BackSide;
		layer.materials.add(mat_back);

		let geom, mesh, shape;
		for (const bnds of this.data.polygons) {
			// sides
			for (const bnd of bnds) {
				geom = Q3D.Utils.createWallGeometry(bnd, bzFunc);
				mesh = new THREE.Mesh(geom, material);
				mesh.name = "side";
				parent.add(mesh);
			}
			// bottom
			shape = new THREE.Shape(Q3D.Utils.flatArrayToVec2Array(bnds[0], 3));
			for (let j = 1, m = bnds.length; j < m; j++) {
				shape.holes.push(new THREE.Path(Q3D.Utils.flatArrayToVec2Array(bnds[j], 3)));
			}
			geom = new THREE.ShapeGeometry(shape);
			mesh = new THREE.Mesh(geom, mat_back);
			mesh.position.z = z0;
			mesh.name = "bottom";
			parent.add(mesh);
		}
		parent.updateMatrixWorld();
	}

	addEdges() {}
	addWireframe() {}
}


class Q3DMapLayer extends THREE.EventDispatcher {

	constructor() {
		super();

		this.id = null;
		this.properties = {};

		this.materials = new Q3DMaterials();
		this.materials.addEventListener("renderRequest", this.requestRender.bind(this));

		this.objectGroup = new Q3DGroup();
		this.objectGroup.name = "layer";
		this.objects = [];
	}

	addObject(object) {
		object.userData.layerId = this.id;
		this.objectGroup.add(object);

		const o = this.objects;
		object.traverse(obj => o.push(obj));

		return this.objectGroup.children.length - 1;
	}

	addObjects(objects) {
		for (const obj of objects) {
			this.addObject(obj);
		}
	}

	clearObjects() {
		// dispose of geometries
		this.objectGroup.traverse((obj) => {
			if (obj.geometry) obj.geometry.dispose();
		});

		// dispose of materials
		this.materials.dispose();

		// remove all child objects from object group
		for (var i = this.objectGroup.children.length - 1; i >= 0; i--) {
			this.objectGroup.remove(this.objectGroup.children[i]);
		}
		this.objects = [];
	}

	visibleObjects() {
		return (this.visible) ? this.objects : [];
	}

	loadData(data, scene) {
		if (data.type == "layer") {
			// properties
			if (data.properties !== undefined) {
				this.properties = data.properties;
				this.objectGroup.visible = (data.properties.visible || Q3D.Config.allVisible) ? true : false;
			}

			this.sceneData = scene.userData;
		}
	}

	get clickable() {
		return this.properties.clickable;
	}

	get opacity() {
		return this.materials.opacity();
	}

	set opacity(value) {
		this.materials.setOpacity(value);
		this.requestRender();
	}

	get visible() {
		return this.objectGroup.visible;
	}

	set visible(value) {
		this.objectGroup.visible = value;
		this.requestRender();
	}

	boundingBox() {
		return new THREE.Box3().setFromObject(this.objectGroup);
	}

	setWireframeMode(wireframe) {
		this.materials.setWireframeMode(wireframe);
	}

	requestRender() {
		this.dispatchEvent({type: "renderRequest"});
	}

}


class Q3DDEMLayer extends Q3DMapLayer {

	constructor() {
		super();
		this.type = Q3D.LayerType.DEM;
		this.blocks = [];
		this.auxiliaryMtl = {};
	}

	loadData(data, scene) {
		if (data.type == "layer") {
			this.clearObjects();
			super.loadData(data, scene);

			this.blocks = [];

			var p = scene.userData,
				rotation = p.baseExtent.rotation;

			if (data.properties.clipped) {
				this.objectGroup.position.set(0, 0, 0);
				this.objectGroup.rotation.z = 0;

				if (rotation) {
					// rotate around center of base extent
					this.objectGroup.position.copy(p.pivot).negate();
					this.objectGroup.position.applyAxisAngle(Q3D.uv.k, rotation * Q3D.deg2rad);
					this.objectGroup.position.add(p.pivot);
					this.objectGroup.rotateOnAxis(Q3D.uv.k, rotation * Q3D.deg2rad);
				}
			}
			else {
				this.objectGroup.position.copy(p.pivot);
				this.objectGroup.position.z *= p.zScale;
				this.objectGroup.rotation.z = rotation * Q3D.deg2rad;
			}
			this.objectGroup.updateMatrixWorld();

			this._loadAuxiliaryMaterials(data.properties);

			if (data.body !== undefined && data.body.blocks !== undefined) {
				data.body.blocks.forEach((block) => {
					this.buildBlock(block, scene, this);
				});
			}
		}
		else if (data.type == "block") {
			this.buildBlock(data, scene, this);
		}
	}

	_loadAuxiliaryMaterials(p) {
		["sides", "edges", "wireframe"].forEach((a) => {
			if (!p[a]) return;

			const m = new Q3DMaterial();
			m.loadData(p[a].mtl);
			this.materials.add(m);
			this.auxiliaryMtl[a] = m;
		});
	}

	buildBlock(data, scene, layer) {

		let block = this.blocks[data.block];
		if (block === undefined) {
			if (layer.properties.tiled) {
				block = new Q3DDEMTileBlock();
			}
			else if (layer.properties.clipped) {
				block = new Q3DClippedDEMBlock();
			}
			else {
				block = new Q3DDEMBlock();
			}
			this.blocks[data.block] = block;
		}

		block.loadData(data, this, (mesh) => {
			// add auxiliary objects
			if (layer.properties.sides) {	// sides and bottom
				block.buildSides(this, mesh, layer.auxiliaryMtl.sides.mtl, layer.properties.sides.bottom);
				this.sideVisible = true;
			}

			if (layer.properties.edges) {
				block.addEdges(this, mesh, layer.auxiliaryMtl.edges.mtl, (layer.properties.sides) ? layer.properties.sides.bottom : undefined);
			}

			if (layer.properties.wireframe) {
				block.addWireframe(this, mesh, layer.auxiliaryMtl.wireframe.mtl);

				mesh.material.polygonOffset = true;
				mesh.material.polygonOffsetFactor = 1;
				mesh.material.polygonOffsetUnits = 1;
			}

			delete data.grid;	// no longer needed

			this.requestRender();
		});
	}

	get opacity() {
		const b = this.blocks[0];
		if (b && b.materials[this.currentMtlIndex]) {
			const m = b.materials[this.currentMtlIndex];
			return (m.mtl) ? m.mtl.opacity : 1;
		}
		return this.materials.opacity();
	}

	set opacity(value) {
		for (const b of this.blocks) {
			const m = b.materials[this.currentMtlIndex];
			if (m && m.mtl) {
				m.mtl.opacity = value;
				m.mtl.transparent = (value < 1);
			}
		}
		this.requestRender();
	}

	get currentMtlIndex() {
		const b = this.blocks[0];
		return (b) ? b.currentMtlIndex : undefined;
	}

	set currentMtlIndex(mtlIndex) {
		this.materials.removeItemsByGroupId(this.currentMtlIndex);

		for (const b of this.blocks) {
			const m = b.materials[mtlIndex];
			if (m) {
				b.currentMtlIndex = mtlIndex;
				b.obj.material = m.mtl;
				this.materials.add(m);
			}
		}
		this.requestRender();
	}

	setSideVisible(visible) {
		this.sideVisible = visible;
		this.objectGroup.traverse((obj) => {
			if (obj.name == "side" || obj.name == "bottom") obj.visible = visible;
		});
	}

	// texture animation
	prepareTexAnimation(from, to) {
		this.anim = [];
		for (const block of this.blocks) {
			const imgFrom = block.materials[from].mtl.map.image;
			const imgTo = block.materials[to].mtl.map.image;

			const canvas = document.createElement("canvas");
			canvas.width = (imgFrom.width > imgTo.width) ? imgFrom.width : imgTo.width;
			canvas.height = (imgFrom.width > imgTo.width) ? imgFrom.height : imgTo.height;

			const ctx = canvas.getContext("2d");

			const tex = new THREE.CanvasTexture(canvas);
			tex.anisotropy = Q3D.Config.texture.anisotropy;
			tex.colorSpace = THREE.SRGBColorSpace;

			const opt = {
				map: tex,
				side: THREE.DoubleSide,
				transparent: true
			};

			let mtl;
			const m = block.obj.material;
			if (m) {
				if (m.isMeshToonMaterial) {
					mtl = new THREE.MeshToonMaterial(opt);
				}
				else if (m.isMeshPhongMaterial) {
					mtl = new THREE.MeshPhongMaterial(opt);
				}
			}
			if (mtl === undefined) {
				mtl = new THREE.MeshLambertMaterial(opt);
			}

			block.obj.material = mtl;
			this.materials.add(mtl);

			this.anim.push({
				img_from: imgFrom,
				img_to: imgTo,
				ctx: ctx,
				tex: mtl.map
			});
		}
	}

	setTextureAt(progress, effect) {

		if (this.anim === undefined) return;

		var w, h, w0, h0, w1, h1, ew, ew1;
		for (const a of this.anim) {
			w = a.ctx.canvas.width;
			h = a.ctx.canvas.height;
			w0 = a.img_from.width;
			h0 = a.img_from.height;
			w1 = a.img_to.width;
			h1 = a.img_to.height;

			if (effect == 0) {  // fade in
				a.ctx.globalAlpha = 1;
				a.ctx.drawImage(a.img_from, 0, 0, w0, h0,
											0, 0, w, h);
				a.ctx.globalAlpha = progress;
				a.ctx.drawImage(a.img_to, 0, 0, w1, h1,
										  0, 0, w, h);
			}
			else if (effect == 2) {  // slide to left (not used)
				if (progress === null) {
					a.ctx.drawImage(a.img_from, 0, 0, w0, h0,
												0, 0, w, h);
				}
				else {
					ew1 = w1 * progress;
					ew = w * progress;
					a.ctx.drawImage(a.img_to, w1 - ew1, 0, ew1, h1,
											  w - ew, 0, ew, h);
				}
			}
			a.tex.needsUpdate = true;
		}
	}
}


class Q3DVectorLayer extends Q3DMapLayer {

	constructor() {
		super();
		this.features = [];
		this.labels = [];
	}

	build(features, startIndex) {}

	addFeature(featureIdx, f, objs) {
		super.addObjects(objs);

		for (const obj of objs) {
			obj.userData.featureIdx = featureIdx;
		}
		f.objs = objs;

		this.features[featureIdx] = f;
		return f;
	}

	clearLabels() {
		this.labels = [];
		if (this.labelGroup) this.labelGroup.clear();
		if (this.labelConnectorGroup) this.labelConnectorGroup.clear();
	}

	buildLabels(features, getPointsFunc) {
		if (this.properties.label === undefined || getPointsFunc === undefined) return;

		const label = this.properties.label;
		const bs = this.sceneData.baseExtent.width * 0.016;
		const sc = bs * Math.pow(1.2, label.size);

		const hasOtl = (label.olcolor !== undefined);
		const hasConn = (label.cncolor !== undefined);

		let line_mtl;
		if (hasConn) {
			line_mtl = new THREE.LineBasicMaterial({
				color: label.cncolor
			});
		}

		const hasUnderline = Boolean(hasConn && label.underline);
		let ul_geom, onBeforeRender;
		if (hasUnderline) {
			ul_geom = new THREE.BufferGeometry();
			ul_geom.setAttribute("position", new THREE.Float32BufferAttribute([0, 0, 0, 1, 0, 0], 3));

			onBeforeRender = function (renderer, scene, camera, geometry, material, group) {
				this.quaternion.copy(camera.quaternion);
				this.updateMatrixWorld();
			};
		}

		const canvas = document.createElement("canvas");
		const ctx = canvas.getContext("2d");

		const th = Q3D.Config.label.canvasHeight;
		const ch = th;
		const font = th + "px " + (label.font || "sans-serif");

		canvas.height = ch;

		for (let i = 0, l = features.length; i < l; i++) {
			const f = features[i];
			const text = f.lbl;
			if (!text) continue;

			let partIdx = 0;
			getPointsFunc(f).forEach((pt) => {

				// label position
				const vec = new THREE.Vector3(pt[0], pt[1], (label.relative) ? pt[2] + f.lh : f.lh);

				// render label text
				ctx.font = font;
				const tw = ctx.measureText(text).width + 2;
				const cw = THREE.MathUtils.ceilPowerOfTwo(tw);

				canvas.width = cw;
				ctx.clearRect(0, 0, cw, ch);

				if (label.bgcolor !== undefined) {
					ctx.fillStyle = label.bgcolor;
					ctx.beginPath();
					ctx.roundRect((cw - tw) / 2, (ch - th) / 2, tw, th, 4);
					ctx.fill();
				}
				ctx.font = font;
				ctx.textAlign = "center";
				ctx.textBaseline = "middle";

				const x = cw / 2;
				const y = ch / 2;

				if (hasOtl) {
					// outline effect
					ctx.fillStyle = label.olcolor;
					for (let j = 0; j < 9; j++) {
						if (j != 4) ctx.fillText(text, x + Math.floor(j / 3) - 1, y + j % 3 - 1);
					}
				}

				ctx.fillStyle = label.color;
				ctx.fillText(text, x, y);

				const tex = new THREE.TextureLoader(Q3D.application.loadingManager).load(canvas.toDataURL(), () => this.requestRender());
				tex.colorSpace = THREE.SRGBColorSpace;

				const mtl = new THREE.SpriteMaterial({
					map: tex,
					transparent: true
				});

				const sprite = new THREE.Sprite(mtl);
				if (hasUnderline) {
					sprite.center.set((1 - tw / cw) * 0.5, 0);
				}
				else {
					sprite.center.set(0.5, 0);
				}
				sprite.position.copy(vec);
				sprite.scale.set(sc * cw / ch, sc, 1);

				sprite.userData.layerId = this.id;
				sprite.userData.properties = f.prop;
				sprite.userData.objs = f.objs;
				sprite.userData.partIdx = partIdx;
				sprite.userData.isLabel = true;

				this.labelGroup.add(sprite);

				if (Q3D.Config.label.clickable) this.labels.push(sprite);

				if (hasConn) {
					// a connector
					const geom = new THREE.BufferGeometry();
					geom.setAttribute("position", new THREE.Float32BufferAttribute(vec.toArray().concat(pt), 3));

					const conn = new THREE.Line(geom, line_mtl);
					conn.userData = sprite.userData;

					this.labelConnectorGroup.add(conn);

					if (hasUnderline) {
						const underline = new THREE.Line(ul_geom, line_mtl);
						underline.position.copy(vec);
						underline.scale.x = sc * tw / th;
						underline.updateMatrixWorld();
						underline.onBeforeRender = onBeforeRender;
						conn.add(underline);
					}
				}
				partIdx++;
			});
		}
	}

	loadData(data, scene) {
		if (data.type == "layer") {
			this.clearObjects();
			this.clearLabels();
			super.loadData(data, scene);

			this.features = [];

			if (this.properties.label !== undefined) {
				if (this.labelGroup === undefined) {
					this.labelGroup = new Q3DGroup();
					this.labelGroup.userData.layerId = this.id;
					this.labelGroup.visible = this.visible;
					scene.labelGroup.add(this.labelGroup);
				}

				if (this.labelConnectorGroup === undefined) {
					this.labelConnectorGroup = new Q3DGroup();
					this.labelConnectorGroup.userData.layerId = this.id;
					this.labelConnectorGroup.visible = this.visible;
					scene.labelConnectorGroup.add(this.labelConnectorGroup);
				}
			}

			if (data.body === undefined) return;

			if (data.body.materials !== undefined) {
				this.materials.loadData(data.body.materials);
			}

			(data.body.blocks || []).forEach((block) => {
				if (block.url !== undefined) Q3D.application.loadJSONFile(block.url);
				else {
					this.build(block.features, block.startIndex);
					if (this.properties.label !== undefined) this.buildLabels(block.features);
				}
			});
		}
		else if (data.type == "block") {
			this.build(data.features, data.startIndex);
			if (this.properties.label !== undefined) this.buildLabels(data.features);
		}
	}

	get visible() {
		return this.objectGroup.visible;
	}

	set visible(value) {
		if (this.labelGroup) this.labelGroup.visible = value;
		if (this.labelConnectorGroup) this.labelConnectorGroup.visible = value;

		this.objectGroup.visible = value;
		this.requestRender();
	}

}


class Q3DPointLayer extends Q3DVectorLayer {

	constructor() {
		super();
		this.type = Q3D.LayerType.Point;
	}

	loadData(data, scene) {
		if (data.type == "layer" && data.properties.objType == "3D Model" && data.body !== undefined) {
			if (this.models === undefined) {
				this.models = new Q3DModels();
				this.models.addEventListener("modelLoaded", (event) => {
					this.materials.addFromObject3D(event.model.scene);
					this.requestRender();
				});
			}
			else {
				this.models.clear();
			}
			this.models.loadData(data.body.models);
		}
		super.loadData(data, scene);
	}

	build(features, startIndex) {
		const { objType } = this.properties;
		if (objType == "Point") {
			return this.buildPoints(features, startIndex);
		}
		else if (objType == "Billboard") {
			return this.buildBillboards(features, startIndex);
		}
		else if (objType == "3D Model") {
			return this.buildModels(features, startIndex);
		}

		let unitGeom, transform;
		if (this.cachedGeometryType === objType) {
			unitGeom = this.geometryCache;
			transform = this.transformCache;
		}
		else {
			[unitGeom, transform] = this.geomAndTransformFunc(objType);
		}

		for (let fidx = 0; fidx < features.length; fidx++) {
			const f = features[fidx];
			const { pts } = f.geom;
			const material = this.materials.mtl(f.mtl.idx);

			const meshes = [];

			for (const pt of pts) {
				const mesh = new THREE.Mesh(unitGeom, material);

				transform(mesh, f.geom, pt);
				mesh.userData.properties = f.prop;

				meshes.push(mesh);
			}

			this.addFeature(fidx + startIndex, f, meshes);
		}

		this.cachedGeometryType = objType;
		this.geometryCache = unitGeom;
		this.transformCache = transform;
	}

	geomAndTransformFunc(objType) {

		const deg2rad = Q3D.deg2rad;
		const rx = 90 * deg2rad;

		if (objType == "Sphere") {
			return [
				new THREE.SphereGeometry(1, 32, 32),
				(mesh, geom, pt) => {
					mesh.scale.setScalar(geom.r);
					mesh.position.fromArray(pt);
				}
			];
		}
		else if (objType == "Box") {
			return [
				new THREE.BoxGeometry(1, 1, 1),
				(mesh, geom, pt) => {
					mesh.scale.set(geom.w, geom.h, geom.d);
					mesh.rotation.x = rx;
					mesh.position.set(pt[0], pt[1], pt[2] + geom.h / 2);
				}
			];
		}
		else if (objType == "Disk") {
			const sz = this.sceneData.zScale;
			return [
				new THREE.CircleGeometry(1, 32),
				(mesh, geom, pt) => {
					mesh.scale.set(geom.r, geom.r * sz, 1);
					mesh.rotateOnWorldAxis(Q3D.uv.i, -geom.d * deg2rad);
					mesh.rotateOnWorldAxis(Q3D.uv.k, -geom.dd * deg2rad);
					mesh.position.fromArray(pt);
				}
			];
		}
		else if (objType == "Plane") {
			const sz = this.sceneData.zScale;
			return [
				new THREE.PlaneGeometry(1, 1, 1, 1),
				(mesh, geom, pt) => {
					mesh.scale.set(geom.w, geom.l * sz, 1);
					mesh.rotateOnWorldAxis(Q3D.uv.i, -geom.d * deg2rad);
					mesh.rotateOnWorldAxis(Q3D.uv.k, -geom.dd * deg2rad);
					mesh.position.fromArray(pt);
				}
			];
		}

		// Cylinder or Cone
		const radiusTop = (objType == "Cylinder") ? 1 : 0;
		return [
			new THREE.CylinderGeometry(radiusTop, 1, 1, 32),
			(mesh, geom, pt) => {
				mesh.scale.set(geom.r, geom.h, geom.r);
				mesh.rotation.x = rx;
				mesh.position.set(pt[0], pt[1], pt[2] + geom.h / 2);
			}
		];
	}

	buildPoints(features, startIndex) {
		for (let fidx = 0; fidx < features.length; fidx++) {
			const f = features[fidx];

			const obj = new THREE.Points(
				new THREE.BufferGeometry().setAttribute("position", new THREE.Float32BufferAttribute(f.geom.pts, 3)),
				this.materials.mtl(f.mtl.idx)
			);
			obj.userData.properties = f.prop;

			this.addFeature(fidx + startIndex, f, [obj]);
		}
	}

	buildBillboards(features, startIndex) {

		const errMtl = {
			mtl: new THREE.SpriteMaterial({color: 0xffffff}),
			callbackOnLoad: () => {}
		};

		features.forEach((f, fidx) => {

			const material = (f.mtl) ? this.materials.get(f.mtl.idx) : errMtl;

			if (!f.mtl) {
				console.warn("[" + this.properties.name + "] Billboard: There is a missing material.");
			}

			const sprites = [];
			for (const pt of f.geom.pts) {
				const sprite = new THREE.Sprite(material.mtl);

				sprite.position.fromArray(pt);
				sprite.scale.set(f.geom.size, f.geom.size, 1);
				sprite.userData.properties = f.prop;

				sprites.push(sprite);
			}

			material.callbackOnLoad(() => {
				const { image } = material.mtl.map;
				const scaleY = f.geom.size * image.height / image.width;

				for (const sprite of sprites) {
					sprite.scale.set(f.geom.size, scaleY, 1);
					sprite.updateMatrixWorld();
				}
			});

			this.addFeature(fidx + startIndex, f, sprites);
		});
	}

	buildModels(features, startIndex) {
		const q = new THREE.Quaternion(),
			  e = new THREE.Euler(),
			  deg2rad = Q3D.deg2rad;

		features.forEach((f, fidx) => {
			const model = this.models.get(f.model);

			if (!model) {
				console.warn(`[${this.properties.name}] 3D Model: There is a missing model.`);
				return;
			}

			const groups = [];

			for (const pt of f.geom.pts) {
				const group = new Q3DGroup();

				group.position.fromArray(pt);
				group.scale.set(1, 1, this.sceneData.zScale);
				group.userData.properties = f.prop;

				groups.push(group);
			}

			model.callbackOnLoad((loadedModel) => {
				const {
					scale,
					rotateX,
					rotateY,
					rotateZ,
					rotateO = "XYZ"
				} = f.geom;

				for (const group of groups) {
					const obj = loadedModel.scene.clone();

					obj.scale.setScalar(scale);

					q.setFromEuler(
						e.set(
							rotateX * deg2rad,
							rotateY * deg2rad,
							rotateZ * deg2rad,
							rotateO
						)
					);

					if (obj.rotation.x) {
						// Reset coordinate system to z-up and apply the specified rotation.
						obj.rotation.set(0, 0, 0);
						obj.quaternion.multiply(q);
					} else {
						// Convert y-up to z-up and apply the specified rotation.
						obj.quaternion.multiply(q);
						obj.quaternion.multiply(q.setFromEuler(e.set(Math.PI / 2, 0, 0)));
					}

					group.add(obj);
				}
			});

			this.addFeature(fidx + startIndex, f, groups);
		});
	}

	buildLabels(features) {
		super.buildLabels(features, f => f.geom.pts);
	}

}


class Q3DLineLayer extends Q3DVectorLayer {

	constructor() {
		super();
		this.type = Q3D.LayerType.Line;
	}

	clearObjects() {
		super.clearObjects();

		if (this.origMtls) {
			this.origMtls.dispose();
			this.origMtls = undefined;
		}
	}

	build(features, startIndex) {

		if (this._lastObjType !== this.properties.objType) this._createObject = null;

		const createObject = this._createObject || this.createObjFunc(this.properties.objType);

		for (let fidx = 0; fidx < features.length; fidx++) {
			const f = features[fidx];
			const objs = [];

			for (const line of f.geom.lines) {
				const obj = createObject(f, line);

				obj.userData.properties = f.prop;
				obj.userData.mtl = f.mtl;

				objs.push(obj);
			}

			this.addFeature(fidx + startIndex, f, objs);
		}

		this._lastObjType = this.properties.objType;
		this._createObject = createObject;
	}

	createObjFunc(objType) {
		const materials = this.materials;

		if (objType == "Line") {
			return (f, vertices) => {
				const obj = new THREE.Line(
					new THREE.BufferGeometry().setAttribute("position", new THREE.Float32BufferAttribute(vertices, 3)),
					materials.mtl(f.mtl.idx)
				);
				if (obj.material instanceof THREE.LineDashedMaterial) obj.computeLineDistances();
				return obj;
			};
		}
		else if (objType == "Thick Line") {
			return (f, vertices) => {
				const geom = new THREE_EX.meshline.MeshLineGeometry();
				geom.setPoints(vertices);

				const mesh = new THREE.Mesh(geom, materials.mtl(f.mtl.idx));
				mesh.raycast = THREE_EX.meshline.raycast;
				return mesh;
			};
		}
		else if (objType == "Pipe" || objType == "Cone") {
			let jointGeom, cylinGeom;
			if (objType == "Pipe") {
				jointGeom = new THREE.SphereGeometry(1, 32, 32);
				cylinGeom = new THREE.CylinderGeometry(1, 1, 1, 32);
			}
			else {
				cylinGeom = new THREE.CylinderGeometry(0, 1, 1, 32);
			}

			const axis = Q3D.uv.j;
			const pt0 = new THREE.Vector3();
			const pt1 = new THREE.Vector3();
			const sub = new THREE.Vector3();

			return (f, points) => {
				const group = new Q3DGroup();
				const material = materials.mtl(f.mtl.idx);

				pt0.fromArray(points[0]);
				for (let i = 1; i < points.length; i++) {
					pt1.fromArray(points[i]);

					const cylinder = new THREE.Mesh(cylinGeom, material);
					cylinder.scale.set(f.geom.r, pt0.distanceTo(pt1), f.geom.r);
					cylinder.position.set(
						(pt0.x + pt1.x) / 2,
						(pt0.y + pt1.y) / 2,
						(pt0.z + pt1.z) / 2
					);
					cylinder.quaternion.setFromUnitVectors(axis, sub.subVectors(pt1, pt0).normalize());

					group.add(cylinder);

					if (jointGeom && i < points.length - 1) {
						const joint = new THREE.Mesh(jointGeom, material);
						joint.scale.setScalar(f.geom.r);
						joint.position.copy(pt1);

						group.add(joint);
					}

					pt0.copy(pt1);
				}
				return group;
			};
		}
		else if (objType == "Box") {
			// In this method, box corners are exposed near joint when both azimuth and slope of
			// the segments of both sides are different. Also, some unnecessary faces are created.
			const jnt_idx = [
				0, 5, 4, 4, 5, 1,   // left turn - top, side, bottom
				3, 0, 7, 7, 0, 4,
				6, 3, 2, 2, 3, 7,
				4, 1, 0, 0, 1, 5,   // right turn - top, side, bottom
				1, 2, 5, 5, 2, 6,
				2, 7, 6, 6, 7, 3
			];

			return (f, points) => {
				const geometries = [];

				let geom, vf4;
				const pt0 = new THREE.Vector3(),
					  pt1 = new THREE.Vector3(),
					  sub = new THREE.Vector3(),
					  pt = new THREE.Vector3(),
					  ptM = new THREE.Vector3(),
					  scale1 = new THREE.Vector3(1, 1, 1),
					  matrix = new THREE.Matrix4(),
					  quat = new THREE.Quaternion();

				pt0.fromArray(points[0]);

				for (let i = 1, l = points.length; i < l; i++) {
					pt1.fromArray(points[i]);

					const dist = pt0.distanceTo(pt1);

					sub.subVectors(pt1, pt0);

					const rx = Math.atan2(sub.z, Math.sqrt(sub.x * sub.x + sub.y * sub.y));
					const rz = Math.atan2(sub.y, sub.x) - Math.PI / 2;

					ptM.set(
						(pt0.x + pt1.x) / 2,
						(pt0.y + pt1.y) / 2,
						(pt0.z + pt1.z) / 2
					);

					quat.setFromEuler(new THREE.Euler(rx, 0, rz, "ZXY"));
					matrix.compose(ptM, quat, scale1);

					// segment box
					geom = new THREE.BoxGeometry(f.geom.w, dist, f.geom.h);
					geom.deleteAttribute("normal");
					geom.deleteAttribute("uv");
					geom.applyMatrix4(matrix);
					geometries.push(geom);

					// joint
					// backward side
					const wh4 = [
						[-f.geom.w / 2,  f.geom.h / 2],
						[ f.geom.w / 2,  f.geom.h / 2],
						[ f.geom.w / 2, -f.geom.h / 2],
						[-f.geom.w / 2, -f.geom.h / 2]
					];

					const vb4 = [];

					for (let j = 0; j < 4; j++) {
						pt.set(wh4[j][0], -dist / 2, wh4[j][1]);
						pt.applyMatrix4(matrix);

						vb4.push(pt.x, pt.y, pt.z);
					}

					if (vf4) {
						geom = new THREE.BufferGeometry();
						geom.setAttribute("position", new THREE.Float32BufferAttribute(vf4.concat(vb4), 3));
						geom.setIndex(jnt_idx);
						geometries.push(geom);
					}

					// forward side
					vf4 = [];

					for (let j = 0; j < 4; j++) {
						pt.set(wh4[j][0], dist / 2, wh4[j][1]);
						pt.applyMatrix4(matrix);

						vf4.push(pt.x, pt.y, pt.z);
					}

					pt0.copy(pt1);
				}

				return new THREE.Mesh(
					THREE_EX.BufferGeometryUtils.mergeGeometries(geometries, false),
					materials.mtl(f.mtl.idx)
				);
			};
		}
		else if (objType == "Wall") {
			return (f, vertices) => {
				return new THREE.Mesh(
					Q3D.Utils.createWallGeometry(vertices, () => f.geom.bh),
					materials.mtl(f.mtl.idx)
				);
			};
		}
	}

	buildLabels(features) {
		// Line layer doesn't support label
		// super.buildLabels(features);
	}

	// prepare for growing line animation
	prepareAnimation(sequential) {

		if (this.origMtls !== undefined) return;

		const computeLineDistances = (obj) => {
			if (!obj.material.isLineDashedMaterial) return;

			obj.computeLineDistances();

			const dists = obj.geometry.attributes.lineDistance.array;
			obj.lineLength = dists[dists.length - 1];

			for (let i = 0; i < dists.length; i++) {
				dists[i] /= obj.lineLength;
			}
		}

		this.origMtls = new Q3DMaterials();
		this.origMtls.array = this.materials.array;

		this.materials.array = [];

		if (sequential) {
			for (const f of this.features) {
				const m = f.objs[0].material;
				let mtl;

				if (m.isMeshLineMaterial) {
					mtl = new THREE_EX.meshline.MeshLineMaterial();
					mtl.color = m.color;
					mtl.opacity = m.opacity;
					mtl.lineWidth = m.lineWidth;
					mtl.dashArray = 2;
					mtl.transparent = true;
				}
				else {
					if (m.isLineDashedMaterial) {
						mtl = m.clone();
					}
					else {
						mtl = new THREE.LineDashedMaterial({
							color: m.color,
							opacity: m.opacity
						});
					}
					mtl.gapSize = 1;
				}

				for (const obj of f.objs) {
					obj.material = mtl;
					computeLineDistances(obj);
				}

				this.materials.add(mtl);
			}
		}
		else {
			for (const origMtl of this.origMtls.array) {
				let mtl = origMtl.mtl;

				if (mtl.isLineDashedMaterial) {
					mtl.gapSize = 1;
				}
				else if (mtl.isMeshLineMaterial) {
					mtl.dashArray = 2;
					mtl.transparent = true;
				}
				else if (mtl.isLineBasicMaterial) {
					mtl = new THREE.LineDashedMaterial({
						color: mtl.color,
						opacity: mtl.opacity
					});
				}

				this.materials.add(mtl);
			}

			this.objectGroup.traverse((obj) => {
				if (obj.userData.mtl === undefined) return;

				obj.material = this.materials.mtl(obj.userData.mtl.idx);
				computeLineDistances(obj);
			});
		}
	}

	// length: number [0 - 1]
	setLineLength(length, featureIdx) {
		if (this.origMtls === undefined) return;

		const setLength = (m) => {
			if (m.isLineDashedMaterial) {
				m.dashSize = length;
			}
			else if (m.isMeshLineMaterial) {
				m.uniforms.dashOffset.value = -length;
			}
		};

		if (featureIdx === undefined) {
			for (const { mtl } of this.materials.array) {
				setLength(mtl);
			}
		}
		else {
			setLength(this.features[featureIdx].objs[0].material);
		}
	}

}


class Q3DPolygonLayer extends Q3DVectorLayer {

	constructor() {
		super();

		this.type = Q3D.LayerType.Polygon;

		// for overlay
		this.borderVisible = true;
		this.sideVisible = true;
	}

	build(features, startIndex) {

		if (this.properties.objType !== this._lastObjType) this._createObject = null;

		const createObject = this._createObject || this.createObjFunc(this.properties.objType);

		for (let fidx = 0; fidx < features.length; fidx++) {
			const f = features[fidx];
			const obj = createObject(f);

			obj.userData.properties = f.prop;

			this.addFeature(fidx + startIndex, f, [obj]);
		}

		this._lastObjType = this.properties.objType;
		this._createObject = createObject;
	}

	createObjFunc(objType) {
		const materials = this.materials;

		if (objType == "Polygon") {
			return (f) => {
				const geom = new THREE.BufferGeometry();
				geom.setAttribute("position", new THREE.Float32BufferAttribute(f.geom.triangles.v, 3));
				geom.setIndex(f.geom.triangles.f);
				return new THREE.Mesh(geom, materials.mtl(f.mtl.idx));
			};
		}
		else if (objType == "Extruded") {
			const createSubObject = (f, polygon, z) => {
				const shape = new THREE.Shape(Q3D.Utils.arrayToVec2Array(polygon[0]));

				for (let i = 1; i < polygon.length; i++) {
					shape.holes.push(new THREE.Path(Q3D.Utils.arrayToVec2Array(polygon[i])));
				}

				const { h } = f.geom;

				const mesh = new THREE.Mesh(
					new THREE.ExtrudeGeometry(shape, {
						bevelEnabled: false,
						depth: h
					}),
					materials.mtl(f.mtl.idx)
				);
				mesh.position.z = z;

				if (f.mtl.edge !== undefined) {
					const edgeMtl = materials.mtl(f.mtl.edge);

					for (const boundary of polygon) {
						const v = [];

						for (const point of boundary) {
							v.push(point[0], point[1], 0);
						}

						const hGeom = new THREE.BufferGeometry().setAttribute("position", new THREE.Float32BufferAttribute(v, 3));

						const bottomEdge = new THREE.Line(hGeom, edgeMtl);
						mesh.add(bottomEdge);

						const topEdge = new THREE.Line(hGeom, edgeMtl);
						topEdge.position.z = h;
						mesh.add(topEdge);

						// vertical edges
						for (let i = 0; i < boundary.length - 1; i++) {
							const [x, y] = boundary[i];

							const vGeom = new THREE.BufferGeometry().setAttribute("position", new THREE.Float32BufferAttribute([x, y, 0, x, y, h], 3));
							mesh.add(new THREE.Line(vGeom, edgeMtl));
						}
					}
				}
				return mesh;
			};

			return (f) => {
				const { polygons, centroids } = f.geom;

				if (polygons.length === 1) {
					return createSubObject(f, polygons[0], centroids[0][2]);
				}

				const group = new THREE.Group();

				for (let i = 0; i < polygons.length; i++) {
					group.add(createSubObject(f, polygons[i], centroids[i][2]));
				}

				return group;
			};
		}
		else if (objType == "Overlay") {

			return (f) => {
				const geom = new THREE.BufferGeometry();
				geom.setIndex(f.geom.triangles.f);
				geom.setAttribute("position", new THREE.Float32BufferAttribute(f.geom.triangles.v, 3));
				geom.computeVertexNormals();

				const mesh = new THREE.Mesh(geom, materials.mtl(f.mtl.idx));

				const { rotation } = this.sceneData.baseExtent;
				if (rotation) {
					// rotate around center of base extent
					mesh.position.copy(this.sceneData.pivot).negate();
					mesh.position.applyAxisAngle(Q3D.uv.k, rotation * Q3D.deg2rad);
					mesh.position.add(this.sceneData.pivot);
					mesh.rotateOnAxis(Q3D.uv.k, rotation * Q3D.deg2rad);
				}

				// borders
				if (f.geom.brdr !== undefined) {
					const bMtl = materials.mtl(f.mtl.brdr);

					for (const boundaries of f.geom.brdr) {
						for (const vertices of boundaries) {
							const bGeom = new THREE.BufferGeometry().setAttribute("position", new THREE.Float32BufferAttribute(vertices, 3));

							mesh.add(new THREE.Line(bGeom, bMtl));
						}
					}
				}
				return mesh;
			};
		}
	}

	buildLabels(features) {
		super.buildLabels(features, f => f.geom.centroids);
	}

	setBorderVisible(visible) {
		if (this.properties.objType != "Overlay") return;

		this.objectGroup.children.forEach((parent) => {
			for (var i = 0, l = parent.children.length; i < l; i++) {
				var obj = parent.children[i];
				if (obj instanceof THREE.Line) obj.visible = visible;
			}
		});
		this.borderVisible = visible;
	}

	setSideVisible(visible) {
		if (this.properties.objType != "Overlay") return;

		this.objectGroup.children.forEach((parent) => {
			for (const obj of parent.children) {
				if (obj instanceof THREE.Mesh) obj.visible = visible;
			}
		});
		this.sideVisible = visible;
	}

}


class Q3DModel {

	constructor() {
		this.loaded = false;
	}

	// callback is called when model has been completely loaded
	load(url, callback) {
		Q3D.application.loadModelFile(url, (model) => {
			this.model = model;
			this._loadCompleted(callback);
		});
	}

	loadBytes(data, ext, resourcePath, callback) {
		Q3D.application.loadModelData(data, ext, resourcePath, (model) => {
			this.model = model;
			this._loadCompleted(callback);
		});
	}

	loadData(data, callback) {
		if (data.url !== undefined) {
			this.load(data.url, callback);
		}
		else {
			const bytes = Q3D.Utils.base64ToUint8Array(data.base64);
			this.loadBytes(bytes.buffer, data.ext, data.resourcePath, callback);
		}
	}

	_loadCompleted(anotherCallback) {
		this.loaded = true;

		if (this._callbacks !== undefined) {
			for (const callback of this._callbacks) {
				callback(this.model);
			}
			this._callbacks = [];
		}

		if (anotherCallback) anotherCallback(this.model);
	}

	callbackOnLoad(callback) {
		if (this.loaded) return callback(this.model);

		if (this._callbacks === undefined) this._callbacks = [];
		this._callbacks.push(callback);
	}

}


class Q3DModels extends THREE.EventDispatcher {

	constructor() {
		super();

		this.models = [];
		this.cache = {};
	}

	loadData(data) {
		const callback = (model) => {
			this.dispatchEvent({type: "modelLoaded", model: model});
		};

		for (const modelData of data) {
			const { url } = modelData;

			let model = this.cache[url];

			if (model === undefined) {
				model = new Q3DModel();
				model.loadData(modelData, callback);

				if (url !== undefined) {
					this.cache[url] = model;
				}
			}

			this.models.push(model);
		}
	}

	get(index) {
		return this.models[index];
	}

	clear() {
		this.models = [];
	}

}

Q3D.Group = Q3DGroup;
Q3D.Scene = Q3DScene;
Q3D.Material = Q3DMaterial;
Q3D.Materials = Q3DMaterials;
Q3D.DEMBlock = Q3DDEMBlock;
Q3D.DEMTileBlock = Q3DDEMTileBlock;
Q3D.ClippedDEMBlock = Q3DClippedDEMBlock;
Q3D.MapLayer = Q3DMapLayer;
Q3D.DEMLayer = Q3DDEMLayer;
Q3D.VectorLayer = Q3DVectorLayer;
Q3D.PointLayer = Q3DPointLayer;
Q3D.LineLayer = Q3DLineLayer;
Q3D.PolygonLayer = Q3DPolygonLayer;
Q3D.Model = Q3DModel;
Q3D.Models = Q3DModels;


// Q3D.Utils - Utilities
Q3D.Utils = {};

// Put a stick to given position (for debugging)
Q3D.Utils.putStick = (x, y, zFunc, h) => {
	if (Q3D.Utils._stick_mat === undefined) Q3D.Utils._stick_mat = new THREE.LineBasicMaterial({color: 0xff0000});
	if (h === undefined) h = 0.2;
	const z = zFunc(x, y);
	const geom = new THREE.BufferGeometry().setFromPoints([
		new THREE.Vector3(x, y, z + h),
		new THREE.Vector3(x, y, z)
	]);
	const stick = new THREE.Line(geom, Q3D.Utils._stick_mat);
	Q3D.application.scene.add(stick);
};

// convert latitude and longitude in degrees to the following format
// Ndd°mm′ss.ss″, Eddd°mm′ss.ss″
Q3D.Utils.convertToDMS = (lat, lon) => {
	const toDMS = (degrees) => {
		var deg = Math.floor(degrees),
			m = (degrees - deg) * 60,
			min = Math.floor(m),
			sec = (m - min) * 60;
		return deg + "°" + ("0" + min).slice(-2) + "′" + ((sec < 10) ? "0" : "") + sec.toFixed(2) + "″";
	}

	return ((lat < 0) ? "S" : "N") + toDMS(Math.abs(lat)) + ", " +
		   ((lon < 0) ? "W" : "E") + toDMS(Math.abs(lon));
};

Q3D.Utils.createWallGeometry = (vert, bzFunc) => {
	const positions = [];
	const indices = [];

	for (let i = 0; i < vert.length; i += 3) {
		const x = vert[i];
		const y = vert[i + 1];

		positions.push(
			x, y, vert[i + 2],
			x, y, bzFunc(x, y)
		);
	}

	for (let i = 1, v = 1, n = vert.length / 3; i < n; i++, v += 2) {
		indices.push(
			v - 1, v, v + 1,
			v + 1, v, v + 2
		);
	}

	const geom = new THREE.BufferGeometry();
	geom.setAttribute("position", new THREE.Float32BufferAttribute(positions, 3));
	geom.setIndex(indices);
	return geom;
};

Q3D.Utils.arrayToVec2Array = (points) => {
	return points.map(([x, y]) => new THREE.Vector2(x, y));
};

Q3D.Utils.flatArrayToVec2Array = (vertices, itemSize) => {
	itemSize = itemSize || 2;
	const pts = [];
	for (let i = 0; i < vertices.length; i += itemSize) {
		pts.push(new THREE.Vector2(vertices[i], vertices[i + 1]));
	}
	return pts;
};

Q3D.Utils.setGeometryUVs = (geom, baseWidth, baseHeight) => {
	const uvs = geom.vertices.map(({ x, y }) => new THREE.Vector2(x / baseWidth + 0.5, y / baseHeight + 0.5));

	geom.faceVertexUvs[0] = geom.faces.map(({ a, b, c }) => [uvs[a], uvs[b], uvs[c]]);
};

Q3D.Utils.base64ToUint8Array = (base64) => {
	var bin = atob(base64);
	var len = bin.length;
	var bytes = new Uint8Array(len);
	for (var i = 0; i < len; i++) {
		bytes[i] = bin.charCodeAt(i);
	}
	return bytes;
};


// Q3D.Tweens
Q3D.Tweens = {};

Q3D.Tweens.cameraMotion = {

	type: Q3D.KeyframeType.CameraMotion,

	curveFactor: 0,

	init: function (track) {
		const app = Q3D.application;
		const { origin, zScale } = app.scene.userData;
		const { keyframes } = track;
		const propList = [];
		const distList = [];

		const curveFactor = this.curveFactor;
		const vec3 = new THREE.Vector3();

		let prevCamera;

		for (let i = 0; i < keyframes.length; i++) {
			const camera = keyframes[i].camera;

			vec3.set(
				camera.x - camera.fx,
				camera.y - camera.fy,
				(camera.z - camera.fz) * zScale
			);

			const dist = vec3.length();
			const theta = Math.acos(vec3.z / dist);
			const phi = Math.atan2(vec3.y, vec3.x);

			camera.phi = phi;

			propList.push({
				p: i,
				fx: camera.fx - origin.x,
				fy: camera.fy - origin.y,
				fz: (camera.fz - origin.z) * zScale,
				d: dist,
				theta
			});

			if (prevCamera) {
				distList.push(
					Math.hypot(
						camera.x - prevCamera.x,
						camera.y - prevCamera.y
					)
				);
			}

			prevCamera = camera;
		}

		track.prop_list = propList;

		track.onUpdate = (obj, elapsed, isFirst) => {
			const p = obj.p - track.currentIndex;

			const phi0 = keyframes[track.currentIndex].camera.phi;
			let phi1 = isFirst ? phi0 : keyframes[track.currentIndex + 1].camera.phi;

			if (Math.abs(phi1 - phi0) > Math.PI) {
				// Take the shortest orbiting path.
				phi1 += Math.PI * (phi1 > phi0 ? -2 : 2);
			}

			const phi = phi0 * (1 - p) + phi1 * p;

			vec3.set(
				Math.cos(phi) * Math.sin(obj.theta),
				Math.sin(phi) * Math.sin(obj.theta),
				Math.cos(obj.theta)
			).setLength(obj.d);

			const dz = curveFactor ? (1 - (2 * p - 1) ** 2) * distList[track.currentIndex] * curveFactor : 0;

			app.camera.position.set(
				obj.fx + vec3.x,
				obj.fy + vec3.y,
				obj.fz + vec3.z + dz
			);

			app.camera.lookAt(obj.fx, obj.fy, obj.fz);
			app.controls.target.set(obj.fx, obj.fy, obj.fz);
		};

		// initial position
		track.onUpdate(track.prop_list[0], 1, true);
	}

};

Q3D.Tweens.opacity = {

	type: Q3D.KeyframeType.Opacity,

	init: function (track, layer) {

		for (const keyframe of track.keyframes) {
			track.prop_list.push({opacity: keyframe.opacity});
		}

		track.onUpdate = (obj, elapsed) => {
			layer.opacity = obj.opacity;
		};

		// initial opacity
		track.onUpdate(track.prop_list[0]);
	}

};

Q3D.Tweens.texture = {

	type: Q3D.KeyframeType.Texture,

	init: function (track, layer) {
		const { keyframes } = track;

		let effect;

		track.onStart = () => {
			const i = track.currentIndex;
			const from = keyframes[i].mtlIndex;
			const to = keyframes[i + 1].mtlIndex;

			effect = keyframes[i].effect;

			layer.prepareTexAnimation(from, to);
			layer.setTextureAt(null, effect);
		};

		track.onUpdate = (obj, elapsed) => {
			layer.setTextureAt(obj.p - track.currentIndex, effect);
		};

		for (let i = 0; i < keyframes.length; i++) {
			track.prop_list.push({ p: i });
		}
	}
};

Q3D.Tweens.lineGrowing = {

	type: Q3D.KeyframeType.GrowingLine,

	init: function (track, layer) {
		if (track._keyframes === undefined) {
			track._keyframes = track.keyframes;
		}

		const effectItem = track._keyframes[0];

		if (effectItem.sequential) {
			track.keyframes = [];
			track.prop_list = [];

			for (let i = 0; i < layer.features.length; i++) {
				const item = layer.features[i].anim;

				item.easing = effectItem.easing;
				track.keyframes.push(item);
				track.prop_list.push({ p: i });
			}

			track.keyframes.push({});
			track.prop_list.push({ p: layer.features.length });

			track.onUpdate = (obj, elapsed) => {
				layer.setLineLength(obj.p - track.currentIndex, track.currentIndex);
			};
		}
		else {
			track.keyframes = [effectItem, {}];
			track.prop_list = [{ p: 0 }, { p: 1 }];

			track.onUpdate = (obj, elapsed) => {
				layer.setLineLength(obj.p);
			};
		}

		layer.prepareAnimation(effectItem.sequential);
		layer.setLineLength(0);
	}

};
