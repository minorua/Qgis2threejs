// (C) 2014 Minoru Akagi
// SPDX-License-Identifier: MIT

import { THREE } from "./three.js";

import { app, conf, deg2rad, gui, modules, LayerType } from "./core.js";
import { Scene } from "./scene.js";
import { E, decompress, transformObjectValues } from "./utils.js";

import type { AppData, ModelObject, Q3DEventListener } from "./types.js";

const _v = new THREE.Vector3();

app.anim_timer = new THREE.Timer();
app.mouseDownPoint = new THREE.Vector2();
app.mouseUpPoint = new THREE.Vector2();
app.queryTargetPosition = new THREE.Vector3();


const listeners: Record<string, Q3DEventListener[]> = {};

app.dispatchEvent = (event) => {
    for (const listener of listeners[event.type] || []) {
        listener(event);
    }
};

app.addEventListener = (type: string, listener: Q3DEventListener, prepend = false) => {
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
    app._wireframeMode = false;
    app.labelVisible = conf.label.visible;

    app.selectedObject = null;
    app.highlightObject = null;

    app.modelBuilders = [];

    if (!applyUrlParameters(container)) return;

    app.initLoadingManager();

    setupRenderer(container);

    setupScene();

    app.buildCamera();
    app.setupControls();

    setupWidgets();

    setupEventListeners();

    setupQueryMarker();
    app.highlightMaterial = new THREE.MeshLambertMaterial({ emissive: 0x999900, transparent: true, opacity: 0.5, side: THREE.DoubleSide });

    gui.init();
};

function applyUrlParameters(container: HTMLElement) {
    const params = Object.fromEntries([
        ...new URLSearchParams(window.location.search),
        ...new URLSearchParams(window.location.hash.slice(1)),
    ]);
    app.urlParams = params;

    if ("popup" in params) {
        const url = new URL(window.location.href);
        url.searchParams.delete("popup");
        window.open(url.toString(), "popup", `width=${params.width},height=${params.height}`);

        gui.popup.show("A new window has been opened.");
        return false;
    }

    if (params.hiDpi == "no") conf.renderer.hiDpi = false;
    if (params.anisotropy) conf.texture.anisotropy = parseFloat(params.anisotropy);

    if (params.cx !== undefined) {
        conf.viewpoint.preset = {
            pos: {
                x: parseFloat(params.cx),
                y: parseFloat(params.cy),
                z: parseFloat(params.cz)
            },
            lookAt: {
                x: parseFloat(params.tx),
                y: parseFloat(params.ty),
                z: parseFloat(params.tz)
            }
        };
    }

    if (params.width && params.height) {
        container.style.width = params.width + "px";
        container.style.height = params.height + "px";
    }
    return true;
}

function setupRenderer(container: HTMLElement) {
    app.renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
    app.renderer.autoClear = false;

    if (conf.renderer.hiDpi) {
        app.renderer.setPixelRatio(window.devicePixelRatio);
    }

    const { clientWidth: width, clientHeight: height } = container;
    app.width = width;
    app.height = height;
    app.renderer.setSize(width, height);

    const bgcolor = conf.bgColor;
    if (bgcolor === null) {
        container.classList.add("sky");
    }
    app.renderer.setClearColor(bgcolor || 0, (bgcolor === null) ? 0 : 1);

    container.appendChild(app.renderer.domElement);

    // set up effect
    if (modules.OutlineEffect) {
        app.effect = new modules.OutlineEffect(app.renderer);
    }

    // set an appropriate anisotropy value based on renderer's capabilities
    if (conf.texture.anisotropy <= 0) {
        const maxAnis = app.renderer.capabilities.getMaxAnisotropy() || 1;

        if (conf.texture.anisotropy == 0) {
            conf.texture.anisotropy = maxAnis;
        }
        else {
            conf.texture.anisotropy = (maxAnis > -conf.texture.anisotropy) ? -maxAnis / conf.texture.anisotropy : 1;
        }
    }
}

function setupScene() {
    app.scene = new Scene();

    app.scene.addEventListener("renderRequest", (event) => app.render());

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
}

app.setupControls = (name: string) => {
    if (!name) {
        if ("MapControls" in modules) name = "Map";
        else if ("OrbitControls" in modules) name = "Orbit";
    }

    if (name == "Map") {
        app.controls = new modules.MapControls(app.camera, app.renderer.domElement);
    }
    else if (name == "Orbit") {
        app.controls = new modules.OrbitControls(app.camera, app.renderer.domElement);
    }
    else {
        return;
    }
    app.controls.listenToKeyEvents(window);
    app.controls.addEventListener("change", () => {
        app.render();
    });
    app.controls.update();
};

function setupWidgets() {
    if (conf.navigation.enabled) {
        app.buildViewHelper();
    }

    if (conf.northArrow.enabled) {
        app.buildNorthArrow();
    }
}

function setupQueryMarker() {
    // create a marker for queried point
    var opt = conf.qmarker;
    app.queryMarker = new THREE.Mesh(
        new THREE.SphereGeometry(opt.radius, 32, 32),
        new THREE.MeshLambertMaterial({ color: opt.color, opacity: opt.opacity, transparent: (opt.opacity < 1) })
    );
    app.queryMarker.name = "marker";

    app.queryMarker.onBeforeRender = function (renderer, scene, camera, geometry, material, group) {
        const scale = camera instanceof THREE.OrthographicCamera ? conf.qmarker.k : 1;
        this.scale.setScalar(this.position.distanceTo(camera.position) * scale);
        this.updateMatrixWorld();
    };
}

function setupEventListeners() {
    app.addEventListener("sceneLoaded", () => {
        E("progressbar").classList.add("fadeout");

        if (conf.viewpoint.preset === null && conf.autoAdjustCameraPos) {
            app.adjustCameraPosition();
        }

        app.scene.sphereNeedsUpdate = true;
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
    app.renderer.domElement.addEventListener("dblclick", app.eventListener.dblclick);
}

app.initLoadingManager = () => {
    app.loadingManager = new THREE.LoadingManager(
        () => {   // onLoad
            app.loadingManager.isLoading = false;
            app.sceneLoaded = true;
            app.dispatchEvent({ type: "sceneLoaded" });
        },
        (url, loaded, total) => {   // onProgress
            E("progressbar").style.width = (loaded / total * 100) + "%";
        },
        () => {   // onError
            app.loadingManager.isLoading = false;
            app.dispatchEvent({ type: "loadError" });
        });

    app.loadingManager.isLoading = false;

    app.loadingManager.onStart = () => {
        app.loadingManager.isLoading = true;
    };
};

app.loadFile = async (url: string, type: XMLHttpRequestResponseType): Promise<any> => {
    const loader = new THREE.FileLoader(app.loadingManager);
    loader.setResponseType(type);

    return new Promise((resolve, reject) => {
        loader.load(url, resolve, undefined, reject);
    });
};

app.loadJSONFile = async (url: string): Promise<void> => {
    const data = await app.loadFile(url, "json") as AppData;
    app.loadData(data);
};

app.loadJSONBinaryFile = async (url: string): Promise<Record<string, ArrayBuffer | any>> => {
    app.loadingManager.itemStart(url);

    try {
        const response = await fetch(url);
        if (!response.ok) throw new Error(`Failed to load ${url}: ${response.status}`);

        const buf = await response.arrayBuffer();
        const view = new DataView(buf);

        const jsonSize = view.getUint32(0, true);
        const jsonStr = new TextDecoder().decode(new Uint8Array(buf, 4, jsonSize));
        const binaryOffset = 4 + jsonSize;

        const data = await transformObjectValues(JSON.parse(jsonStr), async (value) => {
            if (value.__type__ !== undefined) {
                let chunk = buf.slice(
                    binaryOffset + value.offset,
                    binaryOffset + value.offset + value.size
                );

                if (value.compressed) {
                    chunk = await decompress(chunk);
                }

                switch (value.__type__) {
                    case "f32":
                        return new Float32Array(chunk);
                    case "I32":
                        return new Uint32Array(chunk);
                }
            }
        });

        app.loadingManager.itemEnd(url);
        return data;
    }
    catch (error) {
        app.loadingManager.itemError(url);
        throw error;
    }
};

app.loadModelFile = async (url: string): Promise<ModelObject> => {
    const ext = url.split(".").pop();

    let loader;
    if (ext == "dae") {
        loader = new modules.ColladaLoader(app.loadingManager);
    }
    else if (ext == "gltf" || ext == "glb") {
        loader = new modules.GLTFLoader(app.loadingManager);
    }
    else {
        throw new Error("Model file type not supported: " + url);
    }

    app.loadingManager.itemStart("M" + url);

    const model = await new Promise<ModelObject>((resolve, reject) => {
        loader.load(url, resolve, undefined, (error) => {
            app.loadingManager.itemError("M" + url);
            reject(error);
        });
    });

    app.loadingManager.itemEnd("M" + url);
    return model;
};

app.loadSceneFile = async (url: string): Promise<Scene> => {
    app.loadingManager.itemStart("scene");

    try {
        const ext = url.split(".").pop();
        if (ext == "json") {
            await app.loadJSONFile(url);
        }
        else if (ext == "js") {
            await new Promise<void>((resolve, reject) => {
                const script = document.createElement("script");
                script.src = url;
                script.onload = () => resolve();
                script.onerror = (error) => reject(error);
                document.body.appendChild(script);
            });
        }
        else {
            throw new Error("Scene file type not supported: " + ext);
        }

        app.loadingManager.itemEnd("scene");
    }
    catch (error) {
        app.loadingManager.itemError("scene");
        throw error;
    }

    return app.scene;
};

/**
 * @returns true if no error occurs.
 */
app.loadData = (data: AppData): boolean => {
    try {
        app.scene.loadData(data);
        if (data.type == "scene" && data.animation) {
            app.animation.keyframes.load(data.animation.tracks);
        }
        return true;
    }
    catch (e) {
        console.error(e);
        return false;
    }
};

app.loadModelData = (data: Uint8Array, ext: string, resourcePath: string, callback: (scene: THREE.Group) => void) => {

    if (ext == "dae") {
        const model = new modules.ColladaLoader(app.loadingManager).parse(data, resourcePath);
        if (callback) callback(model);
    }
    else if (ext == "gltf" || ext == "glb") {
        new modules.GLTFLoader(app.loadingManager).parse(data, resourcePath, (model) => {
            if (callback) callback(model);
        }, (e) => {
            console.warn("Failed to load a glTF model: " + e);
        });
    }
    else {
        console.warn("Model file type not supported: " + ext);
    }
};

app.eventListener = {

    keydown: function (e) {
        if (e.ctrlKey) return;

        const key = e.key.toLowerCase();

        if (e.shiftKey) {
            switch (key) {
                case "r":
                    app.controls.reset();
                    return;
                case "s":
                    gui.showPrintDialog();
                    return;
            }
            return;
        }

        switch (key) {
            case "backspace":
                if (app.measure.isActive) app.measure.removeLastPoint();
                return;
            case "enter":
                app.animation.keyframes.resume();
                return;
            case "escape":
                if (gui.popup.isVisible()) {
                    app.cleanView();
                }
                else if (app.controls.autoRotate) {
                    app.setRotateAnimationMode(false);
                }
                return;
            case "i":
                gui.showHelp();
                return;
            case "l":
                app.setLabelVisible(!app.labelVisible);
                return;
            case "r":
                app.setRotateAnimationMode(!app.controls.autoRotate);
                return;
            case "w":
                app.setWireframeMode(!app._wireframeMode);
                return;
        }
    },

    mousedown: function (e) {
        app.mouseDownPoint.set(e.clientX, e.clientY);
    },

    mouseup: function (e) {
        app.mouseUpPoint.set(e.clientX, e.clientY);
        if (app.mouseDownPoint.equals(app.mouseUpPoint)) {
            clearTimeout(app._clickTimer);
            app._clickTimer = setTimeout(() => app.canvasClicked(e), 250);
        }
    },

    dblclick: function (e) {
        clearTimeout(app._clickTimer);
        if (app.measure.isActive) return;

        const canvasOffset = elemOffset(app.renderer.domElement);
        const objs = app.intersectObjects(e.clientX - canvasOffset.left, e.clientY - canvasOffset.top);
        if (objs.length) app.cameraAction.zoomToPoint(objs[0].point);
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

    if (changed) app.dispatchEvent({ type: "canvasSizeChanged" });
};

app.buildCamera = (is_ortho) => {
    is_ortho = is_ortho === undefined ? conf.orthoCamera : is_ortho;
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

// adjusts camera's near and far based on the scene's bounding sphere
app.adjustCameraNearFar = () => {
    const sphere = app.scene.boundingSphere();
    const cameraDistance = app.camera.position.distanceTo(sphere.center);
    const margin = Math.max(0.01 * sphere.radius, 0.1);
    const minRatio = 1e3;
    const maxRatio = 1e5;

    app.camera.far = Math.max(cameraDistance + sphere.radius + margin, 1);

    if (app.camera.isOrthographicCamera) {
        app.camera.near = 0;
    }
    else {
        const near = Math.max(cameraDistance - sphere.radius - margin, 0.001);
        app.camera.near = Math.max(app.camera.far / maxRatio, Math.min(near, app.camera.far / minRatio));
    }
    app.camera.updateProjectionMatrix();

    if (conf.debugMode && conf.preview.showCameraInfo) {
        E("cameraInfo").innerText = "[camera] radius: " + sphere.radius.toFixed(3) + ", dist: " + cameraDistance.toFixed(3) + ", near: " + app.camera.near.toFixed(3) + ", far: " + app.camera.far.toFixed(3);
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
    const bbox = app.scene.boundingBox();
    if (bbox.isEmpty()) return;

    bbox.getCenter(_v);
    app.cameraAction.zoom(_v.x, _v.y, (bbox.max.z + _v.z) / 2, app.scene.userData.baseExtent.width);
};

(() => {    // North arrow
    let naScene, naCamera, naMesh;

    const buildNorthArrowGeometry = () => {
        const vertices = [
            -5, -10, 0,
            0, 10, 0,
            0, -7, 3,
            5, -10, 0
        ];

        const index = [
            0, 1, 2,
            2, 1, 3
        ];

        const geometry = new THREE.BufferGeometry();
        geometry.setAttribute("position", new THREE.BufferAttribute(new Float32Array(vertices), 3));
        geometry.setIndex(index);
        return geometry;
    };

    /**
     * @param declination Clockwise from +y, in degrees
     */
    app.buildNorthArrow = (declination = 0) => {
        if (naMesh === undefined) {
            const geometry = buildNorthArrowGeometry();
            const material = new THREE.MeshLambertMaterial({
                color: conf.northArrow.color,
                flatShading: true,
                side: THREE.DoubleSide
            });

            naMesh = new THREE.Mesh(geometry, material);

            naScene = new Scene()
            naScene.buildLights(conf.lights.directional);
            naScene.add(naMesh);

            naCamera = new THREE.PerspectiveCamera(45, 1, 1, 1000);
            naCamera.up = app.camera.up;
            naCamera.position.set(0, 0, conf.northArrow.cameraDistance);
        }
        else {
            naMesh.material.color.set(conf.northArrow.color);
        }

        naMesh.rotation.z = -declination * deg2rad;
    };

    const viewport = new THREE.Vector4();

    app.renderNorthArrow = () => {
        if (naScene === undefined) return;

        naScene.quaternion.copy(app.camera.quaternion).invert();
        naScene.updateMatrixWorld();

        // based on three.js's ViewHelper.js.
        const location = conf.northArrow.location;
        const dim = conf.northArrow.size;

        const { renderer } = app;
        const { domElement } = renderer;

        let x, y;

        if ( location.left !== null ) {
            x = location.left;
        } else {
            x = domElement.offsetWidth - dim - location.right;
        }

        if ( location.top !== null ) {
            y = renderer.isWebGPURenderer ? location.top : domElement.offsetHeight - dim - location.top;
        } else {
            y = renderer.isWebGPURenderer ? domElement.offsetHeight - dim - location.bottom : location.bottom;
        }

        renderer.clearDepth();

        renderer.getViewport(viewport);
        renderer.setViewport(x, y, dim, dim);

        renderer.render(naScene, naCamera);

        renderer.setViewport(viewport.x, viewport.y, viewport.z, viewport.w);
    };
})();

(() => {	// view helper
    let _pupListenerAdded = false;

    app.buildViewHelper = () => {
        if (!modules.ViewHelper) return;

        const { container } = app;
        app.viewHelper = new modules.ViewHelper(app.camera, container);
        app.viewHelper.center = app.controls.target;
        app.viewHelper.setLabels("X", "Y", "Z");
        Object.assign(app.viewHelper.location, conf.navigation.location);

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

        for (const tilesRenderer of app.scene.tilesRenderers) {
            tilesRenderer.update();
        }

        app.adjustCameraNearFar();

        // rendering
        app.renderer.clear()
        if (app.effect) {
            app.effect.render(app.scene, app.camera);
        }
        else {
            app.renderer.render(app.scene, app.camera);
        }

        // North arrow
        if (conf.northArrow.enabled) {
            app.renderNorthArrow();
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
    const vec2 = new THREE.Vector2((offsetX / app.width) * 2 - 1, -(offsetY / app.height) * 2 + 1);
    const ray = new THREE.Raycaster();
    ray.params.Line.threshold = 0.5;
    ray.params.Points.threshold = 0.5;
    ray.setFromCamera(vec2, app.camera);
    return ray.intersectObjects(app.scene.visibleObjects(app.labelVisible));
};

app.cameraAction = {

    move: function (x, y, z) {
        if (x === undefined) app.camera.position.copy(app.queryTargetPosition);
        else app.camera.position.set(x, y, z);

        app.updateControlsAndRender();
        app.cleanView();
    },

    vecZoom: new THREE.Vector3(0, -1, 1).normalize(),

    zoom: function (x, y, z, dist) {
        if (x === undefined) _v.copy(app.queryTargetPosition);
        else _v.set(x, y, z);

        if (dist === undefined) dist = app.scene.userData.baseExtent.width * 0.1;

        app.camera.position.copy(app.cameraAction.vecZoom).multiplyScalar(dist).add(_v);
        app.camera.lookAt(_v);
        if (app.controls.target !== undefined) app.controls.target.copy(_v);
        app.updateControlsAndRender();
        app.cleanView();
    },

    zoomToPoint: function (point) {
        const dist = app.camera.position.distanceTo(point) / 2;
        const dir = new THREE.Vector3().subVectors(app.camera.position, point).normalize();

        app.camera.position.copy(dir).multiplyScalar(dist).add(point);
        app.camera.lookAt(point);
        if (app.controls.target !== undefined) app.controls.target.copy(point);
        app.updateControlsAndRender();
        app.cleanView();
    },

    zoomToLayer: function (layer) {
        if (!layer) return;

        const bbox = layer.boundingBox();
        bbox.getSize(_v);
        const dist = Math.max(_v.x, _v.y * 3 / 4) * 1.2;

        bbox.getCenter(_v);
        app.cameraAction.zoom(_v.x, _v.y, _v.z, dist);
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
    if (!layer || !("objType" in layer.properties) || layer.properties.objType == "Billboard") return;

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

const elemOffset = (elm) => {
    let top = 0, left = 0;
    do {
        top += elm.offsetTop || 0; left += elm.offsetLeft || 0; elm = elm.offsetParent;
    } while (elm);
    return { top: top, left: left };
};

app.canvasClicked = (e) => {
    // button 2: right click
    if (e.button == 2 && app.measure.isActive) {
        app.measure.removeLastPoint();
        return;
    }

    const canvasOffset = elemOffset(app.renderer.domElement);
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
                const markerOpt = conf.measure.marker;
                this.geom = new THREE.SphereGeometry(markerOpt.radius, 32, 32);
                this.mtl = new THREE.MeshLambertMaterial({ color: markerOpt.color, opacity: markerOpt.opacity, transparent: (markerOpt.opacity < 1) });

                const lineOpt = conf.measure.line;
                this.lineMtl = new THREE.LineBasicMaterial({ color: lineOpt.color });
                this.markerGroup = new THREE.Group();
                this.markerGroup.name = "measure marker";
                this.lineGroup = new THREE.Group();
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
