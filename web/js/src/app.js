// (C) 2014 Minoru Akagi
// SPDX-License-Identifier: MIT

import { THREE } from "./three.js";
import { OrbitControls } from "three/controls/OrbitControls.js";

import { app, conf, deg2rad, gui, Group, LayerType, Tweens, THREE_EX } from "./core.js";
import { Scene } from "./scene.js";
import { E } from "./utils.js";

const vec3 = new THREE.Vector3();


(() => {	// event system for the application
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
})();

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
    app.scene = new Scene();

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
            app.scene2.buildLights(conf.lights.directional, event.rotation);
        }
    });

    // camera
    app.buildCamera(conf.orthoCamera);

    // controls
    app.controls = new OrbitControls(app.camera, app.renderer.domElement);
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
    app.queryMarker = new THREE.Mesh(
        new THREE.SphereGeometry(opt.radius, 32, 32),
        new THREE.MeshLambertMaterial({color: opt.color, opacity: opt.opacity, transparent: (opt.opacity < 1)})
    );
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

    app.scene2 = new Scene();
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
    if (declination) mesh.rotation.z = -declination * deg2rad;

    app.scene2.add(mesh);
};

app.anim_timer = new THREE.Timer();

(() => {	// view helper
    let _pupListenerAdded = false;

    app.buildViewHelper = (container) => {
        app.viewHelper = new THREE_EX.ViewHelper(app.camera, container);
        app.viewHelper.center = app.controls.target;
        app.viewHelper.setLabels("X", "Y", "Z");
        app.viewHelper.location.top = conf.navigation.top;
        app.viewHelper.location.bottom = conf.navigation.bottom;

        if (_pupListenerAdded) return;

        container.addEventListener("pointerup", (event) => {
            if (app.viewHelper && app.viewHelper.handleClick(event)) {
                app.anim_timer.update();
                requestAnimationFrame(app.animate);
            }
        });
        _pupListenerAdded = true;
    };
})();

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

        app.anim_timer.update();
        app.viewHelper.update(app.anim_timer.getDelta());
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
                const f = TWEEN.Easing[conf.animation.easingCurve];
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
                for (const p in Tweens) {
                    if (Tweens[p].type == track.type) {
                        tween = Tweens[p];
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

(() => {	// rendering
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
    if (!layer || layer.type == LayerType.DEM || layer.type == LayerType.PointCloud) return;
    if (layer.properties.objType == "Billboard") return;

    // create a highlight object (if layer type is Point, slightly bigger than the object)
    const s = (layer.type == LayerType.Point) ? 1.01 : 1;

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

app.saveCanvasImage = (width, height, fill_background = true, saveImageFunc) => {
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

(() => {	// measurement
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
                this.markerGroup = new Group();
                this.markerGroup.name = "measure marker";
                this.lineGroup = new Group();
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
