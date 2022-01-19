"use strict";
// Qgis2threejs.js
// (C) 2014 Minoru Akagi | MIT License
// https://github.com/minorua/Qgis2threejs

var Q3D = {VERSION: "2.6"};

Q3D.Config = {
  // renderer
  texture: {
    anisotropy: null    // use max available value if this is set to null
  },

  // scene
  autoZShift: false,  // automatic z shift adjustment
  bgColor: null,      // null is sky

  // camera
  orthoCamera: false,
  viewpoint: {      // z-up
    default: {      // assumed that origin is (0, 0, 0) and base extent width in 3D world coordinates is 1
      pos: new THREE.Vector3(0, -1, 1),
      lookAt: new THREE.Vector3()
    }
  },

  // controls
  controls: {
    panSpeed: 1,
    rotateSpeed: 0.5,
    zoomSpeed: 1,
    keyPanSpeed: 4,
    keyRotateSpeed: 0.5   // per one key event, in degrees
  },

  // navigation widget
  navigation: {
    enabled: true
  },

  // light
  lights: [
    {
      type: "ambient",
      color: 0x999999,
      intensity: 0.8
    },
    {
      type: "directional",
      color: 0xffffff,
      intensity: 0.7,
      azimuth: 220,   // azimuth of light, in degrees. default light azimuth of gdaldem hillshade is 315.
      altitude: 45    // altitude angle in degrees.
    },
    {
      type: "directional",
      color: 0xffffff,
      intensity: 0.1,
      azimuth: 40,
      altitude: -45
    }
  ],

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
    connectorColor: 0xc0c0d0,
    fixedSize: false,
    minFontSize: 8,
    clickable: true
  },

  // decoration
  northArrow: {
    color: 0x8b4513,
    cameraDistance: 30,
    visible: false
  },

  qmarker: {
    r: 0.004,
    c: 0xffff00,
    o: 0.8
  },

  coord: {
    visible: true,
    latlon: false
  },

  debugMode: false
};

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
  Material: 66,
  GrowingLine: 67
};

Q3D.uv = {
  i: new THREE.Vector3(1, 0, 0),
  j: new THREE.Vector3(0, 1, 0),
  k: new THREE.Vector3(0, 0, 1)
};

Q3D.deg2rad = Math.PI / 180;

Q3D.ua = window.navigator.userAgent.toLowerCase();
Q3D.isIE = (Q3D.ua.indexOf("msie") != -1 || Q3D.ua.indexOf("trident") != -1);
Q3D.isTouchDevice = ("ontouchstart" in window);

Q3D.$ = function (elementId) {
  return document.getElementById(elementId);
};

/*
Q3D.Group -> THREE.Group -> THREE.Object3D
*/
Q3D.Group = function () {
  THREE.Group.call(this);
};

Q3D.Group.prototype = Object.create(THREE.Group.prototype);
Q3D.Group.prototype.constructor = Q3D.Group;

Q3D.Group.prototype.add = function (object) {
  THREE.Group.prototype.add.call(this, object);
  object.updateMatrixWorld();
};

Q3D.Group.prototype.clear = function () {
  for (var i = this.children.length - 1; i >= 0; i--) {
    this.remove(this.children[i]);
  }
};


/*
Q3D.Scene -> THREE.Scene -> THREE.Object3D

.userData: scene properties - baseExtent(cx, cy, width, height, rotation), origin, zScale, zShift, (proj))
*/
Q3D.Scene = function () {
  THREE.Scene.call(this);
  this.autoUpdate = false;

  this.mapLayers = {};    // map layers contained in this scene. key is layerId.

  this.lightGroup = new Q3D.Group();
  this.add(this.lightGroup);

  this.labelConnectorGroup = new Q3D.Group();
  this.add(this.labelConnectorGroup);

  this.labelRootElement = null;
};

Q3D.Scene.prototype = Object.create(THREE.Scene.prototype);
Q3D.Scene.prototype.constructor = Q3D.Scene;

Q3D.Scene.prototype.add = function (object) {
  THREE.Scene.prototype.add.call(this, object);
  object.updateMatrixWorld();
};

Q3D.Scene.prototype.loadJSONObject = function (jsonObject) {
  if (jsonObject.type == "scene") {
    var p = jsonObject.properties;
    if (p !== undefined) {
      // fog
      if (p.fog) {
        this.fog = new THREE.FogExp2(p.fog.color, p.fog.density / p.baseExtent.width);
      }

      // set initial camera position and parameters
      if (this.userData.origin === undefined) {

        var be = p.baseExtent,
            s = be.width,
            v = Q3D.Config.viewpoint,
            pos, focal;

        if (v.pos === undefined) {
          v = v.default;
          if (be.rotation) {
            v = {
              pos: v.pos.clone().applyAxisAngle(Q3D.uv.k, be.rotation * Q3D.deg2rad),
              lookAt: v.lookAt.clone().applyAxisAngle(Q3D.uv.k, be.rotation * Q3D.deg2rad)
            };
          }
          var vec3 = new THREE.Vector3(be.cx, be.cy, 0).sub(p.origin);
          pos = v.pos.clone().multiplyScalar(s).add(vec3);
          focal = v.lookAt.clone().multiplyScalar(s).add(vec3);
        }
        else {
          pos = new THREE.Vector3().copy(v.pos).sub(p.origin);
          focal = new THREE.Vector3().copy(v.lookAt).sub(p.origin);
        }

        var near = 0.001 * s,
            far = 100 * s;

        this.requestCameraUpdate(pos, focal, near, far);
      }

      p.zShift = -p.origin.z;
      this.userData = p;
    }

    // remove all existing lights
    if (jsonObject.lights !== undefined) this.lightGroup.clear();

    // build lights
    if (this.lightGroup.children.length == 0) this.buildDefaultLights(p.baseExtent.rotation);

    // load layers
    if (jsonObject.layers !== undefined) {
      jsonObject.layers.forEach(function (layer) {
        this.loadJSONObject(layer);
      }, this);
    }
  }
  else if (jsonObject.type == "layer") {
    var layer = this.mapLayers[jsonObject.id];
    if (layer === undefined) {
      // console.assert(jsonObject.properties !== undefined);

      // create a layer
      var type = jsonObject.properties.type;
      if (type == "dem") layer = new Q3D.DEMLayer();
      else if (type == "point") layer = new Q3D.PointLayer();
      else if (type == "line") layer = new Q3D.LineLayer();
      else if (type == "polygon") layer = new Q3D.PolygonLayer();
      else if (type == "pc") layer = new Q3D.PointCloudLayer();
      else {
        console.error("unknown layer type:" + type);
        return;
      }
      layer.id = jsonObject.id;
      layer.addEventListener("renderRequest", this.requestRender.bind(this));

      this.mapLayers[jsonObject.id] = layer;
      this.add(layer.objectGroup);
    }

    layer.loadJSONObject(jsonObject, this);

    this.requestRender();
  }
  else if (jsonObject.type == "block") {
    var layer = this.mapLayers[jsonObject.layer];
    if (layer === undefined) {
      // console.error("layer not exists:" + jsonObject.layer);
      return;
    }
    layer.loadJSONObject(jsonObject, this);

    this.requestRender();
  }
};

Q3D.Scene.prototype.buildLights = function (lights, rotation) {
  var p, light;
  for (var i = 0; i < lights.length; i++) {
    p = lights[i];
    if (p.type == "ambient") {
      this.lightGroup.add(new THREE.AmbientLight(p.color, p.intensity));
    }
    else if (p.type == "directional") {
      light = new THREE.DirectionalLight(p.color, p.intensity);
      light.position.copy(Q3D.uv.j)
                    .applyAxisAngle(Q3D.uv.i, p.altitude * Q3D.deg2rad)
                    .applyAxisAngle(Q3D.uv.k, (rotation - p.azimuth) * Q3D.deg2rad);

      this.lightGroup.add(light);
    }
  }
};

Q3D.Scene.prototype.buildDefaultLights = function (rotation) {
  this.buildLights(Q3D.Config.lights, rotation);
};

Q3D.Scene.prototype.requestRender = function () {
  this.dispatchEvent({type: "renderRequest"});
};

Q3D.Scene.prototype.requestCameraUpdate = function (pos, focal, near, far) {
  this.dispatchEvent({type: "cameraUpdateRequest", pos: pos, focal: focal, near: near, far: far});
};

Q3D.Scene.prototype.visibleObjects = function () {
  var objs = [];
  for (var id in this.mapLayers) {
    if (this.mapLayers[id].visible) {
      objs = objs.concat(this.mapLayers[id].objects);
    }
  }
  return objs;
};

// 3D world coordinates to map coordinates
Q3D.Scene.prototype.toMapCoordinates = function (pt) {
  var p = this.userData;
  return {
    x: p.origin.x + pt.x,
    y: p.origin.y + pt.y,
    z: p.origin.z + pt.z / p.zScale
  };
};

// map coordinates to 3D world coordinates
Q3D.Scene.prototype.toWorldCoordinates = function (pt, isLonLat) {
  var p = this.userData;
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
};

Q3D.Scene.prototype.adjustZShift = function () {
  // initialize
  this.userData.zShiftA = 0;
  this.position.z = 0;
  this.updateMatrixWorld();

  var box = new THREE.Box3();
  for (var id in this.mapLayers) {
    if (this.mapLayers[id].visible) {
      box.union(this.mapLayers[id].boundingBox());
    }
  }

  // bbox zmin in map coordinates
  var zmin = (box.min.z === Infinity) ? 0 : (box.min.z / this.userData.zScale - this.userData.zShift);

  // shift scene so that bbox zmin becomes zero
  this.userData.zShiftA = -zmin;
  this.position.z = this.userData.zShiftA * this.userData.zScale;

  // keep light positions in world coordinates
  this.lightGroup.position.z = -this.position.z;

  this.updateMatrixWorld();

  this.userData.origin.z = -(this.userData.zShift + this.userData.zShiftA);

  console.log("z shift adjusted: " + this.userData.zShiftA);

  this.dispatchEvent({type: "zShiftAdjusted", sceneData: this.userData});

  this.requestRender();
};


/*
Q3D.application

limitations:
- one renderer
- one scene
*/
(function () {
  // the application
  var app = {};
  Q3D.application = app;

  var vec3 = new THREE.Vector3();

  var listeners = {};
  app.dispatchEvent = function (event) {
    var ls = listeners[event.type] || [];
    for (var i = 0; i < ls.length; i++) {
      ls[i](event);
    }
  };

  app.addEventListener = function (type, listener, prepend) {
    listeners[type] = listeners[type] || [];
    if (prepend) {
      listeners[type].unshift(listener);
    }
    else {
      listeners[type].push(listener);
    }
  };

  app.init = function (container) {

    app.container = container;

    app.selectedObject = null;
    app.highlightObject = null;

    app.modelBuilders = [];
    app._wireframeMode = false;

    // URL parameters
    var params = app.parseUrlParameters();
    app.urlParams = params;

    if ("popup" in params) {
      // open popup window
      var c = window.location.href.split("?");
      window.open(c[0] + "?" + c[1].replace(/&?popup/, ""), "popup", "width=" + params.width + ",height=" + params.height);
      app.popup.show("Another window has been opened.");
      return;
    }

    if (params.anisotropy) Q3D.Config.texture.anisotropy = parseFloat(params.anisotropy) || Q3D.Config.texture.anisotropy;

    if (params.cx !== undefined) Q3D.Config.viewpoint.pos = new THREE.Vector3(parseFloat(params.cx), parseFloat(params.cy), parseFloat(params.cz));
    if (params.tx !== undefined) Q3D.Config.viewpoint.lookAt  = new THREE.Vector3(parseFloat(params.tx), parseFloat(params.ty), parseFloat(params.tz));

    if (params.width && params.height) {
      container.style.width = params.width + "px";
      container.style.height = params.height + "px";
    }

    app.width = container.clientWidth;
    app.height = container.clientHeight;

    var bgcolor = Q3D.Config.bgColor;
    if (bgcolor === null) container.classList.add("sky");

    // WebGLRenderer
    app.renderer = new THREE.WebGLRenderer({alpha: true, antialias: true});
    app.renderer.setSize(app.width, app.height);
    app.renderer.setClearColor(bgcolor || 0, (bgcolor === null) ? 0 : 1);
    app.container.appendChild(app.renderer.domElement);

    if (Q3D.Config.texture.anisotropy === null) Q3D.Config.texture.anisotropy = app.renderer.capabilities.getMaxAnisotropy() || 1;

    // outline effect
    if (THREE.OutlineEffect !== undefined) app.effect = new THREE.OutlineEffect(app.renderer);

    // camera
    app.buildCamera(Q3D.Config.orthoCamera);

    // scene
    app.scene = new Q3D.Scene();

    app.scene.addEventListener("renderRequest", function (event) {
      app.render();
    });

    app.scene.addEventListener("cameraUpdateRequest", function (event) {
      app.camera.position.copy(event.pos);
      app.camera.lookAt(event.focal);
      if (app.controls.target !== undefined) app.controls.target.copy(event.focal);
      if (app.controls.saveState !== undefined) app.controls.saveState();

      if (event.near !== undefined) {
        app.camera.near = event.near;
        app.camera.far = event.far;
        app.camera.updateProjectionMatrix();
      }
    });

    // controls
    if (THREE.OrbitControls) {
      app.initOrbitControls(app.camera, app.renderer.domElement);
      app.controls.update();
    }

    // navigation
    if (Q3D.Config.navigation.enabled && typeof ViewHelper !== "undefined") {
      app.buildViewHelper(document.getElementById("navigation"));
    }

    // labels
    app.labelVisible = Q3D.Config.label.visible;
    app.scene.labelRootElement = document.getElementById("labels");
    app.scene.labelRootElement.style.display = (app.labelVisible) ? "block" : "none";

    // create a marker for queried point
    var opt = Q3D.Config.qmarker;
    app.queryMarker = new THREE.Mesh(new THREE.SphereBufferGeometry(opt.r, 32, 32),
                                     new THREE.MeshLambertMaterial({color: opt.c, opacity: opt.o, transparent: (opt.o < 1)}));

    app.highlightMaterial = new THREE.MeshLambertMaterial({emissive: 0x999900, transparent: true, opacity: 0.5});

    if (!Q3D.isIE) app.highlightMaterial.side = THREE.DoubleSide;    // Shader compilation error occurs with double sided material on IE11

    // loading manager
    app.initLoadingManager();

    // event listeners
    app.addEventListener("sceneLoaded", function () {
      if (Q3D.Config.autoZShift) {
        app.scene.adjustZShift();
      }
      app.render();
    }, true);

    window.addEventListener("keydown", app.eventListener.keydown);
    window.addEventListener("resize", app.eventListener.resize);

    app.renderer.domElement.addEventListener("mousedown", app.eventListener.mousedown);
    app.renderer.domElement.addEventListener("mouseup", app.eventListener.mouseup);

    var e = Q3D.$("closebtn");
    if (e) e.addEventListener("click", app.closePopup);

    e = Q3D.$("nextbtn");
    if (e) e.addEventListener("click", function () {
      var e = document.getElementById("narrativebox");
      if (e) e.classList.remove("visible");

      app.animation.keyframes.resume();
    });

    // attribution
    if (typeof proj4 === "undefined") {
      e = Q3D.$("lib_proj4js");
      if (e) e.style.display = "none";
    }
  };

  app.parseUrlParameters = function () {
    var p, vars = {};
    var params = window.location.search.substring(1).split('&').concat(window.location.hash.substring(1).split('&'));
    params.forEach(function (param) {
      p = param.split('=');
      vars[p[0]] = p[1];
    });
    return vars;
  };

  app.initOrbitControls = function (camera, domElement) {

    var controls = new THREE.OrbitControls(camera, domElement);
    controls.enableKeys = false;    // key events are handled in app.eventListener.keydown

    controls.panSpeed = Q3D.Config.controls.panSpeed;
    controls.rotateSpeed = Q3D.Config.controls.rotateSpeed;
    controls.zoomSpeed = Q3D.Config.controls.zoomSpeed;
    controls.keyPanSpeed = Q3D.Config.controls.keyPanSpeed;
    controls.keyRotateAngle = Q3D.Config.controls.keyRotateSpeed * Q3D.deg2rad;

    // custom actions
    var offset = new THREE.Vector3(),
        spherical = new THREE.Spherical(),
        quat = new THREE.Quaternion().setFromUnitVectors(camera.up, new THREE.Vector3(0, 1, 0)),
        quatInverse = quat.clone().inverse();

    controls.cameraRotate = function (thetaDelta, phiDelta) {
      offset.copy(controls.target).sub(controls.object.position);
      offset.applyQuaternion(quat);

      spherical.setFromVector3(offset);

      spherical.theta += thetaDelta;
      spherical.phi -= phiDelta;

      // restrict theta/phi to be between desired limits
      spherical.theta = Math.max(controls.minAzimuthAngle, Math.min(controls.maxAzimuthAngle, spherical.theta));
      spherical.phi = Math.max(controls.minPolarAngle, Math.min(controls.maxPolarAngle, spherical.phi));
      spherical.makeSafe();

      offset.setFromSpherical(spherical);
      offset.applyQuaternion(quatInverse);

      controls.target.copy(controls.object.position).add(offset);
      controls.object.lookAt(controls.target);
    };

    controls.addEventListener("change", function (event) {
      app.render();
    });

    app.controls = controls;
  };

  app.initLoadingManager = function () {
    if (app.loadingManager) {
      app.loadingManager.onLoad = app.loadingManager.onProgress = app.loadingManager.onError = undefined;
    }

    app.loadingManager = new THREE.LoadingManager(function () {   // onLoad
      app.loadingManager.isLoading = false;

      document.getElementById("bar").classList.add("fadeout");

      app.dispatchEvent({type: "sceneLoaded"});
    },
    function (url, loaded, total) {   // onProgress
      document.getElementById("bar").style.width = (loaded / total * 100) + "%";
    },
    function () {   // onError
      app.loadingManager.isLoading = false;

      app.dispatchEvent({type: "sceneLoadError"});
    });

    app.loadingManager.onStart = function () {
      app.loadingManager.isLoading = true;
    };

    app.loadingManager.isLoading = false;
  };

  app.loadFile = function (url, type, callback) {

    var loader = new THREE.FileLoader(app.loadingManager);
    loader.setResponseType(type);

    var onError = function (e) {
      if (location.protocol == "file:") {
        app.popup.show("This browser doesn't allow loading local files via Ajax. See <a href='https://github.com/minorua/Qgis2threejs/wiki/Browser-Support'>plugin wiki page</a> for details.", "Error", true);
      }
    };

    try {
      loader.load(url, callback, undefined, onError);
    }
    catch (e) {      // for IE
      onError(e);
    }
  };

  app.loadJSONObject = function (jsonObject) {
    app.scene.loadJSONObject(jsonObject);
    if (jsonObject.animation !== undefined) app.animation.keyframes.load(jsonObject.animation.groups);
  };

  app.loadJSONFile = function (url, callback) {
    app.loadFile(url, "json", function (obj) {
      app.loadJSONObject(obj);
      if (callback) callback(obj);
    });
  };

  app.loadSceneFile = function (url, sceneFileLoadedCallback, sceneLoadedCallback) {

    var onload = function () {
      // build North arrow widget
      if (Q3D.Config.northArrow.visible) app.buildNorthArrow(document.getElementById("northarrow"), app.scene.userData.baseExtent.rotation);

      if (sceneFileLoadedCallback) sceneFileLoadedCallback(app.scene);
    };

    if (sceneLoadedCallback) {
      app.addEventListener("sceneLoaded", function () {
        sceneLoadedCallback(app.scene);
      });
    }

    var ext = url.split(".").pop();
    if (ext == "json") app.loadJSONFile(url, onload);
    else if (ext == "js") {
      var e = document.createElement("script");
      e.src = url;
      e.onload = onload;
      document.body.appendChild(e);
    }
  };

  app.loadTextureFile = function (url, callback) {
    return new THREE.TextureLoader(app.loadingManager).load(url, callback);
  };

  app.loadModelFile = function (url, callback) {
    var loader,
        ext = url.split(".").pop();
    if (ext == "dae") {
      loader = new THREE.ColladaLoader(app.loadingManager);
    }
    else if (ext == "gltf" || ext == "glb") {
      loader = new THREE.GLTFLoader(app.loadingManager);
    }
    else {
      console.log("Model file type not supported: " + url);
      return;
    }

    app.loadingManager.itemStart("M" + url);

    loader.load(url, function (model) {
      if (callback) callback(model);
      app.loadingManager.itemEnd("M" + url);
    },
    undefined,
    function (e) {
      console.log("Failed to load model: " + url);
      app.loadingManager.itemError("M" + url);
    });
  };

  app.loadModelData = function (data, ext, resourcePath, callback) {

    if (ext == "dae") {
      var model = new THREE.ColladaLoader(app.loadingManager).parse(data, resourcePath);
      if (callback) callback(model);
    }
    else if (ext == "gltf" || ext == "glb") {
      new THREE.GLTFLoader(app.loadingManager).parse(data, resourcePath, function (model) {
        if (callback) callback(model);
      }, function (e) {
        console.log("Failed to load a glTF model: " + e);
      });
    }
    else {
      console.log("Model file type not supported: " + ext);
      return;
    }
  };

  app.mouseDownPoint = new THREE.Vector2();
  app.mouseUpPoint = new THREE.Vector2();

  app.eventListener = {

    keydown: function (e) {
      var controls = app.controls;

      if (e.shiftKey && e.ctrlKey) {
        switch (e.keyCode) {
          case 38:  // Shift + Ctrl + UP
            controls.dollyOut(controls.getZoomScale());
            break;
          case 40:  // Shift + Ctrl + DOWN
            controls.dollyIn(controls.getZoomScale());
            break;
          default:
            return;
        }
      }
      else if (e.shiftKey) {
        switch (e.keyCode) {
          case 37:  // LEFT
            controls.rotateLeft(controls.keyRotateAngle);
            break;
          case 38:  // UP
            controls.rotateUp(controls.keyRotateAngle);
            break;
          case 39:  // RIGHT
            controls.rotateLeft(-controls.keyRotateAngle);
            break;
          case 40:  // DOWN
            controls.rotateUp(-controls.keyRotateAngle);
            break;
          case 82:  // Shift + R
            controls.reset();
            break;
          case 83:  // Shift + S
            app.showPrintDialog();
            return;
          default:
            return;
        }
      }
      else if (e.ctrlKey) {
        switch (e.keyCode) {
          case 37:  // Ctrl + LEFT
            controls.cameraRotate(controls.keyRotateAngle, 0);
            break;
          case 38:  // Ctrl + UP
            controls.cameraRotate(0, controls.keyRotateAngle);
            break;
          case 39:  // Ctrl + RIGHT
            controls.cameraRotate(-controls.keyRotateAngle, 0);
            break;
          case 40:  // Ctrl + DOWN
            controls.cameraRotate(0, -controls.keyRotateAngle);
            break;
          default:
            return;
        }
      }
      else {
        switch (e.keyCode) {
          case 37:  // LEFT
            controls.pan(controls.keyPanSpeed, 0);    // horizontally left
            break;
          case 38:  // UP
            controls.pan(0, controls.keyPanSpeed);    // horizontally forward
            break;
          case 39:  // RIGHT
            controls.pan(-controls.keyPanSpeed, 0);
            break;
          case 40:  // DOWN
            controls.pan(0, -controls.keyPanSpeed);
            break;
          case 27:  // ESC
            if (Q3D.$("popup").style.display != "none") {
              app.closePopup();
            }
            else if (app.controls.autoRotate) {
              app.setRotateAnimationMode(false);
            }
            return;
          case 73:  // I
            app.showInfo();
            return;
          case 76:  // L
            app.setLabelVisible(!app.labelVisible);
            return;
          case 82:  // R
            app.setRotateAnimationMode(!controls.autoRotate);
            return;
          case 87:  // W
            app.setWireframeMode(!app._wireframeMode);
            return;
          default:
            return;
        }
      }
      app.controls.update();
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

  app.setCanvasSize = function (width, height) {
    app.width = width;
    app.height = height;
    app.camera.aspect = width / height;
    app.camera.updateProjectionMatrix();
    app.renderer.setSize(width, height);
  };

  app.buildCamera = function (is_ortho) {
    if (is_ortho) {
      app.camera = new THREE.OrthographicCamera(-app.width / 10, app.width / 10, app.height / 10, -app.height / 10);
    }
    else {
      app.camera = new THREE.PerspectiveCamera(45, app.width / app.height);
    }

    // magic to change y-up world to z-up
    app.camera.up.set(0, 0, 1);
  };

  // rotation: direction to North (clockwise from up (+y), in degrees)
  app.buildNorthArrow = function (container, rotation) {
    container.style.display = "block";

    app.renderer2 = new THREE.WebGLRenderer({alpha: true, antialias: true});
    app.renderer2.setClearColor(0, 0);
    app.renderer2.setSize(container.clientWidth, container.clientHeight);

    app.container2 = container;
    app.container2.appendChild(app.renderer2.domElement);

    app.camera2 = new THREE.PerspectiveCamera(45, container.clientWidth / container.clientHeight, 1, 1000);
    app.camera2.up = app.camera.up;

    app.scene2 = new Q3D.Scene();
    app.scene2.buildDefaultLights(rotation);

    // an arrow object
    var geometry = new THREE.Geometry();
    geometry.vertices.push(
      new THREE.Vector3(-5, -10, 0),
      new THREE.Vector3(0, 10, 0),
      new THREE.Vector3(0, -7, 3),
      new THREE.Vector3(5, -10, 0)
    );
    geometry.faces.push(
      new THREE.Face3(0, 1, 2),
      new THREE.Face3(2, 1, 3)
    );
    geometry.computeFaceNormals();

    var material = new THREE.MeshLambertMaterial({color: Q3D.Config.northArrow.color, side: THREE.DoubleSide});
    var mesh = new THREE.Mesh(geometry, material);
    if (rotation) mesh.rotation.z = -rotation * Q3D.deg2rad;
    app.scene2.add(mesh);
  };

  var clock = new THREE.Clock();

  app.buildViewHelper = function (container) {

    if (app.renderer3 === undefined) {
      container.style.display = "block";

      app.renderer3 = new THREE.WebGLRenderer({alpha: true, antialias: true});
      app.renderer3.setClearColor(0, 0);
      app.renderer3.setSize(container.clientWidth, container.clientHeight);

      app.container3 = container;
      app.container3.appendChild(app.renderer3.domElement);
    }

    app.viewHelper = new ViewHelper(app.camera, {dom: container});
    app.viewHelper.controls = app.controls;

    app.viewHelper.addEventListener("requestAnimation", function (event) {
      clock.start();
      requestAnimationFrame(app.animate);
    });
  };

  app.currentViewUrl = function () {
    var c = app.scene.toMapCoordinates(app.camera.position),
        t = app.scene.toMapCoordinates(app.controls.target),
        hash = "#cx=" + c.x + "&cy=" + c.y + "&cz=" + c.z;
    if (t.x || t.y || t.z) hash += "&tx=" + t.x + "&ty=" + t.y + "&tz=" + t.z;
    return window.location.href.split("#")[0] + hash;
  };

  // enable the controls
  app.start = function () {
    if (app.controls) app.controls.enabled = true;
  };

  app.pause = function () {
    app.animation.isActive = false;
    if (app.controls) app.controls.enabled = false;
  };

  app.resume = function () {
    if (app.controls) app.controls.enabled = true;
  };

  // animation loop
  app.animate = function () {

    if (app.animation.isActive) {
      requestAnimationFrame(app.animate);

      if (app.animation.keyframes.isActive) TWEEN.update();
      else if (app.controls.enabled) app.controls.update();
    }
    else if (app.viewHelper && app.viewHelper.animating) {
      requestAnimationFrame(app.animate);

      app.viewHelper.update(clock.getDelta());
    }

    app.render();
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
        var e = (easing || "").split(" "),
            f = TWEEN.Easing[e[0]];

        if (f && f[e[1]]) return f[e[1]];

        return TWEEN.Easing.Linear.None;    // default easing
      },

      keyframeGroups: [],

      clear: function () {
        this.keyframeGroups = [];
      },

      load: function (group) {
        if (!Array.isArray(group)) group = [group];

        this.keyframeGroups = this.keyframeGroups.concat(group);
      },

      start: function () {

        if (this.isActive || this.isPaused) this.stop();

        var _this = this,
            e = document.getElementById("narrativebox"),
            currentNarElem;

        this.keyframeGroups.forEach(function (group) {

          var keyframes = group.keyframes;
          if (keyframes.length == 0) {
            console.warn("A keyframe group has no keyframes.");
            return;
          }

          var geFunc = _this.easingFunction(group.easing),
              prop_list = [];

          group.completed = false;
          group.currentIndex = 0;

          var showNBox = function (idx) {
            // narrative box
            var n = keyframes[idx].narration;
            if (n && e) {
              if (currentNarElem) {
                currentNarElem.style.display = "none";
              }
              currentNarElem = document.getElementById(n.id);
              if (currentNarElem) {
                currentNarElem.style.display = "block";
              }
              else {    // preview
                document.getElementById("narbody").innerHTML = n.text;
              }

              setTimeout(function () {
                e.classList.add("visible");
              }, 0);
            }
          };

          var onUpdate, _onStart, _onComplete;

          if (group.type == Q3D.KeyframeType.CameraMotion) {
            var c = _this.curveFactor, p, p0, phi, theta, dist, dist_list = [];
            var vec3 = new THREE.Vector3();
            for (var i = 0; i < keyframes.length; i++) {
              p = keyframes[i].camera;
              vec3.set(p.x - p.fx, p.y - p.fy, p.z - p.fz);
              dist = vec3.length();
              theta = Math.acos(vec3.z / dist);
              phi = Math.atan2(vec3.y, vec3.x);
              p.phi = phi;
              prop_list.push({fx: p.fx, fy: p.fy, fz: p.fz, d: dist, theta: theta});

              if (i > 0) {
                dist_list.push(Math.sqrt((p.x - p0.x) * (p.x - p0.x) + (p.y - p0.y) * (p.y - p0.y)));
              }
              p0 = p;
            }

            var phi0, phi1, dz;
            onUpdate = function (obj, elapsed, is_first) {
              phi0 = keyframes[group.currentIndex].camera.phi;
              phi1 = (is_first) ? phi0 : keyframes[group.currentIndex + 1].camera.phi;

              if (Math.abs(phi1 - phi0) > Math.PI) {  // take the shortest orbiting path
                phi1 += Math.PI * ((phi1 > phi0) ? -2 : 2);
              }

              phi = phi0 * (1 - elapsed) + phi1 * elapsed;

              vec3.set(Math.cos(phi) * Math.sin(obj.theta),
                       Math.sin(phi) * Math.sin(obj.theta),
                       Math.cos(obj.theta)).setLength(obj.d);

              dz = (c) ? (1 - Math.pow(2 * elapsed - 1, 2)) * dist_list[group.currentIndex] * c : 0;

              app.camera.position.set(obj.fx + vec3.x, obj.fy + vec3.y, obj.fz + vec3.z + dz);
              app.camera.lookAt(obj.fx, obj.fy, obj.fz);
              app.controls.target.set(obj.fx, obj.fy, obj.fz);
            };

            // move to camera position of the first keyframe
            onUpdate(prop_list[0], 1, true);
          }
          else {
            // layer animation
            var layer = app.scene.mapLayers[group.layerId];

            if (group.type == Q3D.KeyframeType.Opacity) {

              onUpdate = function (obj, elapsed) {
                layer.opacity = obj.opacity;
              };

              for (var i = 0; i < keyframes.length; i++) {
                prop_list.push({opacity: keyframes[i].opacity});
              }
            }
            else if (group.type == Q3D.KeyframeType.Material) {

              var idx_from, from, to, effect;

              _onStart = function () {
                idx_from = group.currentIndex;
                from = keyframes[idx_from].mtlIndex;
                to = keyframes[idx_from + 1].mtlIndex;
                effect = keyframes[idx_from + 1].effect;

                layer.prepareMtlAnimation(from, to);
              };

              onUpdate = function (obj, elapsed) {
                layer.setTextureAt(elapsed, effect);
              };

              for (var i = 0; i < keyframes.length; i++) {
                prop_list.push({idx: i});
              }
            }
            else if (group.type == Q3D.KeyframeType.GrowingLine) {

              onUpdate = function (obj, elapsed) {
                layer.setLengthPercentage(elapsed);
              };

              // one effect item to two keyframes
              var to, kfs = [];
              for (var i = 0; i < keyframes.length; i++) {
                to = Object.assign({}, keyframes[i]);
                to.delay = 0;
                kfs.push(keyframes[i], to);

                prop_list.push({p: 0}, {p: 1});
              }
              keyframes = kfs;

              layer.prepareGrowingAnimation();
            }
            else return;
          }

          var onStart = function () {
            if (_onStart) _onStart();

            app.dispatchEvent({type: "tweenStarted", index: group.currentIndex});

            // pause if narrative box is shown
            if (keyframes[group.currentIndex].narration) _this.pause();
            else if (e) e.classList.remove("visible");
          };

          var onComplete = function (obj) {
            if (_onComplete) _onComplete(obj);

            var index = ++group.currentIndex;
            if (index == keyframes.length - 1) {
              group.completed = true;

              var completed = true;
              for (var i = 0; i < _this.keyframeGroups.length; i++) {
                if (!_this.keyframeGroups[i].completed) completed = false;
              }

              if (completed) _this.stop();
            }

            // show narrative box if the current keyframe has a narrative content
            showNBox(index);
          };

          var tween, t1, t2;
          for (i = 1; i < keyframes.length; i++) {
            t2 = new TWEEN.Tween(prop_list[i - 1])
                             .to(prop_list[i], keyframes[i].duration)
                             .delay(keyframes[i - 1].delay)
                             .easing((keyframes[i].easing) ? _this.easingFunction(keyframes[i].easing) : geFunc)
                             .onStart(onStart)
                             .onUpdate(onUpdate)
                             .onComplete(onComplete);
            // delay -> [onStart] -> transition [onUpdate] -> [onComplete]

            if (i == 1) {
              tween = t2;
            }
            else {
              t1.chain(t2);
            }
            t1 = t2;
          }

          showNBox(0);

          // start animation
          tween.start();
        });

        app.animation.isActive = this.isActive = true;
        app.animate();
      },

      stop: function () {

        var tweens = TWEEN.getAll();
        for (var i = 0; i < tweens.length; i++) {
          tweens[i].stop();
        }

        app.animation.isActive = this.isActive = this.isPaused = false;
        this._pausedTweens = null;

        app.dispatchEvent({type: "animationStopped"});  // to notify the exporter that animation has been stopped
      },

      pause: function () {

        this._pausedTweens = TWEEN.getAll();

        if (this._pausedTweens.length) {
          for (var i = 0; i < this._pausedTweens.length; i++) {
            this._pausedTweens[i].pause();
          }
          this.isPaused = true;
        }
        app.animation.isActive = this.isActive = false;
      },

      resume: function () {

        if (!this.isPaused) return;

        for (var i = 0; i < this._pausedTweens.length; i++) {
          this._pausedTweens[i].resume();
        }
        this._pausedTweens = null;

        app.animation.isActive = this.isActive = true;
        this.isPaused = false;

        app.animate();
      },
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
    }};

  app.render = function (updateControls) {
    if (updateControls) app.controls.update();

    // render
    if (app.effect) {
      app.effect.render(app.scene, app.camera);
    }
    else {
      app.renderer.render(app.scene, app.camera);
    }

    // North arrow
    if (app.renderer2) {
      app.camera.getWorldDirection(vec3);
      app.camera2.position.copy(vec3.negate().setLength(Q3D.Config.northArrow.cameraDistance));
      app.camera2.quaternion.copy(app.camera.quaternion);

      app.renderer2.render(app.scene2, app.camera2);
    }

    // navigation widget
    if (app.viewHelper) {
      app.viewHelper.render(app.renderer3);
    }

    // labels
    app.updateLabelPosition();
  };

  (function () {
    var dly, rpt, times, id = null;
    var func = function () {
      app.render();
      if (rpt <= ++times) {
        clearInterval(id);
        id = null;
      }
    };
    app.setIntervalRender = function (delay, repeat) {
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

  // app.updateLabelPosition()
  (function () {
    var camera,
        c2t = new THREE.Vector3(),
        c2l = new THREE.Vector3();

    app.updateLabelPosition = function () {
      var rootGroup = app.scene.labelConnectorGroup;
      if (!app.labelVisible || rootGroup.children.length == 0) return;

      camera = app.camera;
      camera.getWorldDirection(c2t);

      // make list of [connector object, pt, distance to camera]
      var obj_dist = [],
          i, l, k, m,
          connGroup, conn, pt0;

      for (i = 0, l = rootGroup.children.length; i < l; i++) {
        connGroup = rootGroup.children[i];
        if (!connGroup.visible) continue;
        for (k = 0, m = connGroup.children.length; k < m; k++) {
          conn = connGroup.children[k];
          pt0 = conn.geometry.vertices[0];
          vec3.copy(pt0);

          if (c2l.subVectors(vec3, camera.position).dot(c2t) > 0)      // label is in front
            obj_dist.push([conn, pt0, camera.position.distanceTo(vec3)]);
          else    // label is in back
            conn.userData.elem.style.display = "none";
        }
      }

      if (obj_dist.length == 0) return;

      // sort label objects in descending order of distances
      obj_dist.sort(function (a, b) {
        if (a[2] < b[2]) return 1;
        if (a[2] > b[2]) return -1;
        return 0;
      });

      var widthHalf = app.width / 2,
          heightHalf = app.height / 2,
          fixedSize = Q3D.Config.label.fixedSize,
          minFontSize = Q3D.Config.label.minFontSize;

      var label, dist, x, y, e, t, fontSize;
      for (i = 0, l = obj_dist.length; i < l; i++) {
        label = obj_dist[i][0];
        pt0 = obj_dist[i][1];
        dist = obj_dist[i][2];

        // calculate label position
        vec3.copy(pt0).project(camera);
        x = (vec3.x * widthHalf) + widthHalf;
        y = -(vec3.y * heightHalf) + heightHalf;

        // set label position
        e = label.userData.elem;
        t = "translate(" + (x - (e.offsetWidth / 2)) + "px," + (y - (e.offsetHeight / 2)) + "px)";
        e.style.display = "block";
        e.style.zIndex = i + 1;
        e.style.webkitTransform = t;
        e.style.transform = t;

        // set font size
        if (!fixedSize) {
          if (dist < 10) dist = 10;
          fontSize = Math.max(Math.round(1000 / dist), minFontSize);
          e.style.fontSize = fontSize + "px";
        }
      }
    };
  })();

  app.setLabelVisible = function (visible) {
    app.labelVisible = visible;
    app.scene.labelRootElement.style.display = (visible) ? "block" : "none";
    app.scene.labelConnectorGroup.visible = visible;
    app.render();
  };

  app.setRotateAnimationMode = function (enabled) {
    if (enabled) {
      app.animation.orbit.start();
    }
    else {
      app.animation.orbit.stop();
    }
  };

  app.setWireframeMode = function (wireframe) {
    if (wireframe == app._wireframeMode) return;

    for (var id in app.scene.mapLayers) {
      app.scene.mapLayers[id].setWireframeMode(wireframe);
    }

    app._wireframeMode = wireframe;
    app.render();
  };

  app.intersectObjects = function (offsetX, offsetY) {
    var vec2 = new THREE.Vector2((offsetX / app.width) * 2 - 1,
                                 -(offsetY / app.height) * 2 + 1);
    var ray = new THREE.Raycaster();
    ray.linePrecision = 0.2;
    ray.setFromCamera(vec2, app.camera);
    return ray.intersectObjects(app.scene.visibleObjects());
  };

  app._offset = function (elm) {
    var top = 0, left = 0;
    do {
      top += elm.offsetTop || 0; left += elm.offsetLeft || 0; elm = elm.offsetParent;
    } while (elm);
    return {top: top, left: left};
  };

  app.popup = {

    timerId: null,

    modal: false,

    // show box
    // obj: html, element or content id ("queryresult" or "pageinfo")
    // modal: boolean
    // duration: int [milliseconds]
    show: function (obj, title, modal, duration) {

      if (modal) app.pause();
      else if (this.modal) app.resume();

      this.modal = Boolean(modal);

      var content = Q3D.$("popupcontent");
      [content, Q3D.$("queryresult"), Q3D.$("pageinfo")].forEach(function (e) {
        if (e) e.style.display = "none";
      });

      if (obj == "queryresult" || obj == "pageinfo") {
        Q3D.$(obj).style.display = "block";
      }
      else {
        if (obj instanceof HTMLElement) {
          content.innerHTML = "";
          content.appendChild(obj);
        }
        else {
          content.innerHTML = obj;
        }
        content.style.display = "block";
      }
      Q3D.$("popupbar").innerHTML = title || "";
      Q3D.$("popup").style.display = "block";

      if (app.popup.timerId !== null) {
        clearTimeout(app.popup.timerId);
        app.popup.timerId = null;
      }

      if (duration) {
        app.popup.timerId = setTimeout(function () {
          app.popup.hide();
        }, duration);
      }
    },

    hide: function () {
      Q3D.$("popup").style.display = "none";
      if (app.popup.timerId !== null) clearTimeout(app.popup.timerId);
      app.popup.timerId = null;
      if (this.modal) app.resume();
    }

  };

  app.showInfo = function () {
    var url = Q3D.$("urlbox");
    if (url) url.value = app.currentViewUrl();
    app.popup.show("pageinfo");
  };

  app.queryTargetPosition = new THREE.Vector3();

  app.cameraAction = {

    move: function (x, y, z) {
      if (x === undefined) app.camera.position.copy(app.queryTargetPosition);
      else app.camera.position.set(x, y, z);
      app.render(true);
    },

    vecZoom: new THREE.Vector3(0, -10, 10),

    zoomIn: function (x, y, z) {
      if (x === undefined) vec3.copy(app.queryTargetPosition);
      else vec3.set(x, y, z);

      app.camera.position.addVectors(vec3, app.cameraAction.vecZoom);
      app.camera.lookAt(vec3);
      if (app.controls.target !== undefined) app.controls.target.copy(vec3);
      app.render(true);
    },

    orbit: function (x, y, z) {
      if (app.controls.target === undefined) return;

      if (x === undefined) app.controls.target.copy(app.queryTargetPosition);
      else app.controls.target.set(x, y, z);
      app.setRotateAnimationMode(true);
    }

  };

  app.showQueryResult = function (point, obj, show_coords) {
    app.queryTargetPosition.copy(point);

    var layer = app.scene.mapLayers[obj.userData.layerId],
        e = document.getElementById("qr_layername");

    // layer name
    if (layer && e) e.innerHTML = layer.properties.name;

    // clicked coordinates
    e = document.getElementById("qr_coords_table");
    if (e) {
      if (show_coords) {
        e.classList.remove("hidden");

        var pt = app.scene.toMapCoordinates(point);

        e = document.getElementById("qr_coords");

        if (Q3D.Config.coord.latlon) {
          var lonLat = proj4(app.scene.userData.proj).inverse([pt.x, pt.y]);
          e.innerHTML = Q3D.Utils.convertToDMS(lonLat[1], lonLat[0]) + ", Elev. " + pt.z.toFixed(2);
        }
        else {
          e.innerHTML = [pt.x.toFixed(2), pt.y.toFixed(2), pt.z.toFixed(2)].join(", ");
        }

        if (Q3D.Config.debugMode) {
          var p = app.scene.userData,
              be = p.baseExtent;
          e.innerHTML += "<br>WLD: " + [point.x.toFixed(8), point.y.toFixed(8), point.z.toFixed(8)].join(", ");
          e.innerHTML += "<br><br>ORG: " + [p.origin.x.toFixed(8), p.origin.y.toFixed(8), p.origin.z.toFixed(8)].join(", ");
          e.innerHTML += "<br>BE CNTR: " + [be.cx.toFixed(8), be.cy.toFixed(8)].join(", ");
          e.innerHTML += "<br>BE SIZE: " + [be.width.toFixed(8), be.height.toFixed(8)].join(", ");
          e.innerHTML += "<br>ROT: " + be.rotation + "<br>Z SC: " + p.zScale;
        }
      }
      else {
        e.classList.add("hidden");
      }
    }

    e = document.getElementById("qr_attrs_table");
    if (e) {
      for (var i = e.children.length - 1; i >= 0; i--) {
        if (e.children[i].tagName.toUpperCase() == "TR") e.removeChild(e.children[i]);
      }

      if (layer && layer.properties.propertyNames !== undefined) {
        var row;
        for (var i = 0, l = layer.properties.propertyNames.length; i < l; i++) {
          row = document.createElement("tr");
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
    app.popup.show("queryresult");
  };

  app.showPrintDialog = function () {

    function e(tagName, parent, innerHTML) {
      var elem = document.createElement(tagName);
      if (parent) parent.appendChild(elem);
      if (innerHTML) elem.innerHTML = innerHTML;
      return elem;
    }

    var f = e("form");
    f.className = "print";

    var d1 = e("div", f, "Image Size");
    d1.style.textDecoration = "underline";

    var d2 = e("div", f),
        l1 = e("label", d2, "Width:"),
        width = e("input", d2);
    d2.style.cssFloat = "left";
    l1.htmlFor = width.id = width.name = "printwidth";
    width.type = "text";
    width.value = app.width;
    e("span", d2, "px,");

    var d3 = e("div", f),
        l2 = e("label", d3, "Height:"),
        height = e("input", d3);
    l2.htmlFor = height.id = height.name = "printheight";
    height.type = "text";
    height.value = app.height;
    e("span", d3, "px");

    var d4 = e("div", f),
        ka = e("input", d4);
    ka.type = "checkbox";
    ka.checked = true;
    e("span", d4, "Keep Aspect Ratio");

    var d5 = e("div", f, "Option");
    d5.style.textDecoration = "underline";

    var d6 = e("div", f),
        bg = e("input", d6);
    bg.type = "checkbox";
    bg.checked = true;
    e("span", d6, "Fill Background");

    var d7 = e("div", f),
        ok = e("span", d7, "OK"),
        cancel = e("span", d7, "Cancel");
    d7.className = "buttonbox";

    e("input", f).type = "submit";

    // event handlers
    // width and height boxes
    var aspect = app.width / app.height;

    width.oninput = function () {
      if (ka.checked) height.value = Math.round(width.value / aspect);
    };

    height.oninput = function () {
      if (ka.checked) width.value = Math.round(height.value * aspect);
    };

    ok.onclick = function () {
      app.popup.show("Rendering...");
      window.setTimeout(function () {
        app.saveCanvasImage(width.value, height.value, bg.checked);
      }, 10);
    };

    cancel.onclick = app.closePopup;

    // enter key pressed
    f.onsubmit = function () {
      ok.onclick();
      return false;
    };

    app.popup.show(f, "Save Image", true);   // modal
  };

  app.closePopup = function () {
    app.popup.hide();
    app.scene.remove(app.queryMarker);
    app.highlightFeature(null);
    app.render();
    if (app._canvasImageUrl) {
      URL.revokeObjectURL(app._canvasImageUrl);
      app._canvasImageUrl = null;
    }
  };

  app.highlightFeature = function (object) {
    if (app.highlightObject) {
      // remove highlight object from the scene
      app.scene.remove(app.highlightObject);
      app.selectedObject = null;
      app.highlightObject = null;
    }

    if (object === null) return;

    var layer = app.scene.mapLayers[object.userData.layerId];
    if (layer === undefined || layer.type == Q3D.LayerType.DEM) return;
    if (["Icon", "JSON model", "COLLADA model"].indexOf(layer.objType) != -1) return;

    // create a highlight object (if layer type is Point, slightly bigger than the object)
    // var highlightObject = new Q3D.Group();
    var s = (layer.type == Q3D.LayerType.Point) ? 1.01 : 1;

    var clone = object.clone();
    clone.traverse(function (obj) {
      obj.material = app.highlightMaterial;
    });
    if (s != 1) clone.scale.multiplyScalar(s);
    // highlightObject.add(clone);

    // add the highlight object to the scene
    app.scene.add(clone);

    app.selectedObject = object;
    app.highlightObject = clone;
  };

  app.canvasClicked = function (e) {

    var canvasOffset = app._offset(app.renderer.domElement);
    var objs = app.intersectObjects(e.clientX - canvasOffset.left, e.clientY - canvasOffset.top);

    var obj, o, layer, layerId;
    for (var i = 0, l = objs.length; i < l; i++) {
      obj = objs[i];

      // get layerId of clicked object
      o = obj.object;
      while (o) {
        layerId = o.userData.layerId;
        if (layerId !== undefined) break;
        o = o.parent;
      }

      if (layerId === undefined) break;

      layer = app.scene.mapLayers[layerId];
      if (!layer.clickable) break;

      // query marker
      app.queryMarker.position.copy(obj.point);
      app.queryMarker.scale.setScalar(obj.distance);
      app.scene.add(app.queryMarker);

      app.highlightFeature(o);
      app.render();
      app.showQueryResult(obj.point, o, Q3D.Config.coord.visible);

      return;
    }
    app.closePopup();
  };

  app.saveCanvasImage = function (width, height, fill_background, saveImageFunc) {
    if (fill_background === undefined) fill_background = true;

    // set canvas size
    var old_size;
    if (width && height) {
      old_size = [app.width, app.height];
      app.setCanvasSize(width, height);
    }

    // functions
    var saveBlob = function (blob) {
      var filename = "image.png";

      // ie
      if (window.navigator.msSaveBlob !== undefined) {
        window.navigator.msSaveBlob(blob, filename);
        app.popup.hide();
      }
      else {
        // create object url
        if (app._canvasImageUrl) URL.revokeObjectURL(app._canvasImageUrl);
        app._canvasImageUrl = URL.createObjectURL(blob);

        // display a link to save the image
        var e = document.createElement("a");
        e.className = "download-link";
        e.href = app._canvasImageUrl;
        e.download = filename;
        e.innerHTML = "Save";
        app.popup.show("Click to save the image to a file." + e.outerHTML, "Image is ready");
      }
    };

    var saveCanvasImage = saveImageFunc || function (canvas) {
      if (canvas.toBlob !== undefined) {
        canvas.toBlob(saveBlob);
      }
      else {    // !HTMLCanvasElement.prototype.toBlob
        // https://developer.mozilla.org/en-US/docs/Web/API/HTMLCanvasElement.toBlob
        var binStr = atob(canvas.toDataURL("image/png").split(',')[1]),
            len = binStr.length,
            arr = new Uint8Array(len);

        for (var i = 0; i < len; i++) {
          arr[i] = binStr.charCodeAt(i);
        }

        saveBlob(new Blob([arr], {type: "image/png"}));
      }
    };

    var labels = [];    // list of [label point, text]
    if (app.labelVisible) {
      var rootGroup = app.scene.labelConnectorGroup, connGroup, conn, pt;
      for (var i = 0; i < rootGroup.children.length; i++) {
        connGroup = rootGroup.children[i];
        if (!connGroup.visible) continue;
        for (var k = 0; k < connGroup.children.length; k++) {
          conn = connGroup.children[k];
          pt = conn.geometry.vertices[0];
          labels.push({pt: new THREE.Vector3(pt.x, pt.y, pt.z),      // in world coordinates
                       text: conn.userData.elem.textContent});
        }
      }
    }

    var renderLabels = function (ctx) {
      // context settings
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";

      // get label style from css
      var elem = document.createElement("div");
      elem.className = "print-label";
      document.body.appendChild(elem);
      var style = document.defaultView.getComputedStyle(elem, ""),
          color = style.color;
      ctx.font = style.font;
      document.body.removeChild(elem);

      var widthHalf = width / 2,
          heightHalf = height / 2,
          camera = app.camera,
          c2t = new THREE.Vector3(),
          c2l = new THREE.Vector3(),
          v = new THREE.Vector3();

      camera.getWorldDirection(c2t);

      // make a list of [label index, distance to camera]
      var idx_dist = [];
      for (var i = 0, l = labels.length; i < l; i++) {
        idx_dist.push([i, camera.position.distanceTo(labels[i].pt)]);
      }

      // sort label indexes in descending order of distances
      idx_dist.sort(function (a, b) {
        if (a[1] < b[1]) return 1;
        if (a[1] > b[1]) return -1;
        return 0;
      });

      var label, x, y;
      for (i = 0, l = idx_dist.length; i < l; i++) {
        label = labels[idx_dist[i][0]];
        if (c2l.subVectors(label.pt, camera.position).dot(c2t) > 0) {    // label is in front
          // calculate label position
          v.copy(label.pt).project(camera);
          x = (v.x * widthHalf) + widthHalf;
          y = -(v.y * heightHalf) + heightHalf;
          if (x < 0 || width <= x || y < 0 || height <= y) continue;

          // outline effect
          ctx.fillStyle = "#FFF";
          for (var j = 0; j < 9; j++) {
            if (j != 4) ctx.fillText(label.text, x + Math.floor(j / 3) - 1, y + j % 3 - 1);
          }

          ctx.fillStyle = color;
          ctx.fillText(label.text, x, y);
        }
      }
    };

    var restoreCanvasSize = function () {
      // restore canvas size
      if (old_size) app.setCanvasSize(old_size[0], old_size[1]);
      app.render();
    };

    // background option
    if (!fill_background) app.renderer.setClearColor(0, 0);

    // render
    app.renderer.preserveDrawingBuffer = true;

    if (app.effect) {
      app.effect.render(app.scene, app.camera);
    }
    else {
      app.renderer.render(app.scene, app.camera);
    }

    // restore clear color
    var bgcolor = Q3D.Config.bgColor;
    app.renderer.setClearColor(bgcolor || 0, (bgcolor === null) ? 0 : 1);

    if ((fill_background && bgcolor === null) || labels.length > 0) {
      var canvas = document.createElement("canvas");
      canvas.width = width;
      canvas.height = height;

      var ctx = canvas.getContext("2d");
      if (fill_background && bgcolor === null) {
        // render "sky-like" background
        var grad = ctx.createLinearGradient(0, 0, 0, height);
        grad.addColorStop(0, "#98c8f6");
        grad.addColorStop(0.4, "#cbebff");
        grad.addColorStop(1, "#f0f9ff");
        ctx.fillStyle = grad;
        ctx.fillRect(0, 0, width, height);
      }

      var image = new Image();
      image.onload = function () {
        // draw webgl canvas image
        ctx.drawImage(image, 0, 0, width, height);

        // render labels
        if (labels.length > 0) renderLabels(ctx);

        // save canvas image
        saveCanvasImage(canvas);
        restoreCanvasSize();
      };
      image.src = app.renderer.domElement.toDataURL("image/png");
    }
    else {
      // save webgl canvas image
      saveCanvasImage(app.renderer.domElement);
      restoreCanvasSize();
    }
  };
})();


/*
Q3D.Material
*/
Q3D.Material = function () {
  this.loaded = false;
};

Q3D.Material.prototype = {

  constructor: Q3D.Material,

  // material: a THREE.Material-based object
  set: function (material) {
    this.mtl = material;
    this.origProp = {};
    return this;
  },

  // callback is called when material has been completely loaded
  loadJSONObject: function (jsonObject, callback) {
    this.origProp = jsonObject;
    this.groupId = jsonObject.mtlIndex;

    var m = jsonObject, opt = {}, defer = false;

    if (m.ds && !Q3D.isIE) opt.side = THREE.DoubleSide;

    if (m.flat) opt.flatShading = true;

    // texture
    if (m.image !== undefined) {
      var _this = this;
      if (m.image.url !== undefined) {
        opt.map = Q3D.application.loadTextureFile(m.image.url, function () {
          _this._loadCompleted(callback);
        });
        defer = true;
      }
      else if (m.image.object !== undefined) {    // WebKit Bridge
        opt.map = new THREE.Texture(m.image.object.toImageData());
        opt.map.needsUpdate = true;

        delete m.image.object
      }
      else {    // base64
        var img = new Image();
        img.onload = function () {
          opt.map.needsUpdate = true;
          _this._loadCompleted(callback);
        };
        img.src = m.image.base64;
        opt.map = new THREE.Texture(img);
        defer = true;

        delete m.image.base64
      }
      opt.map.anisotropy = Q3D.Config.texture.anisotropy;
    }

    if (m.c !== undefined) opt.color = m.c;

    if (m.o !== undefined && m.o < 1) {
      opt.opacity = m.o;
      opt.transparent = true;
    }

    if (m.t) opt.transparent = true;

    if (m.w) opt.wireframe = true;

    if (m.type == Q3D.MaterialType.MeshLambert) {
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

      // opt.resolution = new THREE.Vector2(window.innerWidth, window.innerHeight);
      // opt.sizeAttenuation = 1;

      this.mtl = new MeshLineMaterial(opt);
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
  },

  _loadCompleted: function (anotherCallback) {
    this.loaded = true;

    if (this._callbacks !== undefined) {
      for (var i = 0; i < this._callbacks.length; i++) {
        this._callbacks[i]();
      }
      this._callbacks = [];
    }

    if (anotherCallback) anotherCallback();
  },

  callbackOnLoad: function (callback) {
    if (this.loaded) return callback();

    if (this._callbacks === undefined) this._callbacks = [];
    this._callbacks.push(callback);
  },

  type: function () {
    if (this.mtl instanceof THREE.MeshLambertMaterial) return Q3D.MaterialType.MeshLambert;
    if (this.mtl instanceof THREE.MeshPhongMaterial) return Q3D.MaterialType.MeshPhong;
    if (this.mtl instanceof THREE.LineBasicMaterial) return Q3D.MaterialType.Line;
    if (this.mtl instanceof THREE.LineDashedMaterial) return Q3D.MaterialType.Line;
    if (this.mtl instanceof THREE.SpriteMaterial) return Q3D.MaterialType.Sprite;
    if (this.mtl instanceof THREE.MeshStandardMaterial) return Q3D.MaterialType.MeshStandard;
    if (this.mtl === undefined) return undefined;
    if (this.mtl === null) return null;
    if (this.mtl.isMeshLineMaterial) return Q3D.MaterialType.MeshLine;
    return Q3D.MaterialType.Unknown;
  },

  dispose: function () {
    if (!this.mtl) return;

    if (this.mtl.map) this.mtl.map.dispose();   // dispose of texture
    this.mtl.dispose();
    this.mtl = null;
  }
};

/*
Q3D.Materials
*/
Q3D.Materials = function () {
  this.array = [];
};

Q3D.Materials.prototype = Object.create(THREE.EventDispatcher.prototype);
Q3D.Materials.prototype.constructor = Q3D.Materials;

// material: instance of Q3D.Material object or THREE.Material-based object
Q3D.Materials.prototype.add = function (material) {
  if (material instanceof Q3D.Material) {
    this.array.push(material);
  }
  else {
    this.array.push(new Q3D.Material().set(material));
  }
};

Q3D.Materials.prototype.get = function (index) {
  return this.array[index];
};

Q3D.Materials.prototype.mtl = function (index) {
  return this.array[index].mtl;
};

Q3D.Materials.prototype.loadJSONObject = function (jsonObject) {
  var _this = this, iterated = false;
  var callback = function () {
    if (iterated) _this.dispatchEvent({type: "renderRequest"});
  };

  for (var i = 0, l = jsonObject.length; i < l; i++) {
    var mtl = new Q3D.Material();
    mtl.loadJSONObject(jsonObject[i], callback);
    this.add(mtl);
  }
  iterated = true;
};

Q3D.Materials.prototype.dispose = function () {
  for (var i = 0, l = this.array.length; i < l; i++) {
    this.array[i].dispose();
  }
  this.array = [];
};

Q3D.Materials.prototype.addFromObject3D = function (object) {
  var mtls = [];

  object.traverse(function (obj) {
    if (obj.material === undefined) return;
    ((obj.material instanceof Array) ? obj.material : [obj.material]).forEach(function (mtl) {
      if (mtls.indexOf(mtl) == -1) {
        mtls.push(mtl);
      }
    });
  });

  for (var i = 0, l = mtls.length; i < l; i++) {
    this.array.push(new Q3D.Material().set(mtls[i]));
  }
};

// opacity
Q3D.Materials.prototype.opacity = function () {
  if (this.array.length == 0) return 1;

  var sum = 0;
  for (var i = 0, l = this.array.length; i < l; i++) {
    sum += this.array[i].mtl.opacity;
  }
  return sum / this.array.length;
};

Q3D.Materials.prototype.setOpacity = function (opacity) {
  var m;
  for (var i = 0, l = this.array.length; i < l; i++) {
    m = this.array[i];
    m.mtl.transparent = Boolean(m.origProp.t) || (opacity < 1);
    m.mtl.opacity = opacity;
  }
};

// wireframe: boolean
Q3D.Materials.prototype.setWireframeMode = function (wireframe) {
  var m;
  for (var i = 0, l = this.array.length; i < l; i++) {
    m = this.array[i];
    if (m.origProp.w || m.mtl instanceof THREE.LineBasicMaterial) continue;
    m.mtl.wireframe = wireframe;
  }
};

Q3D.Materials.prototype.removeItem = function (material, dispose) {
  for (var i = this.array.length - 1; i >= 0; i--) {
    if (this.array[i].mtl === material) {
      this.array.splice(i, 1);
      break;
    }
  }
  if (dispose) material.dispose()
};

Q3D.Materials.prototype.removeGroupItems = function (groupId) {
  for (var i = this.array.length - 1; i >= 0; i--) {
    if (this.array[i].groupId === groupId) {
      this.array.splice(i, 1);
    }
  }
};

/*
Q3D.DEMBlock
*/
Q3D.DEMBlock = function () {
  this.materials = [];
  this.currentMtlIndex = 0;
};

Q3D.DEMBlock.prototype = {

  constructor: Q3D.DEMBlock,

  // obj: object decoded from JSON
  loadJSONObject: function (obj, layer, callback) {

    this.data = obj;

    // load material
    var m, mtl;
    for (var i = 0, l = (obj.materials || []).length; i < l; i++) {
      m = obj.materials[i];

      mtl = new Q3D.Material();
      mtl.loadJSONObject(m, function () {
        layer.requestRender();
      });
      this.materials[m.mtlIndex] = mtl;

      if (m.useNow) {
        if (this.obj) {
          layer.materials.removeItem(this.obj.material, true);

          this.obj.material = mtl.mtl;

          layer.materials.add(mtl);
          layer.requestRender();
        }
        this.currentMtlIndex = m.mtlIndex;
      }
    }

    if (obj.grid === undefined) return;

    // create a plane geometry
    var geom, grid = obj.grid;
    if (layer.geometryCache) {
      var params = layer.geometryCache.parameters || {};
      if (params.width === obj.width && params.height === obj.height &&
          params.widthSegments === grid.width - 1 && params.heightSegments === grid.height - 1) {
        geom = layer.geometryCache.clone();
        geom.parameters = layer.geometryCache.parameters;
      }
    }
    geom = geom || new THREE.PlaneBufferGeometry(obj.width, obj.height, grid.width - 1, grid.height - 1);
    layer.geometryCache = geom;

    // create a mesh
    var mesh = new THREE.Mesh(geom, (this.materials[this.currentMtlIndex] || {}).mtl);
    mesh.position.fromArray(obj.translate);
    mesh.scale.z = obj.zScale;
    layer.addObject(mesh);

    // TODO: this.transform
    var buildGeometry = function (grid_values) {
      var vertices = geom.attributes.position.array;
      for (var i = 0, j = 0, l = vertices.length; i < l; i++, j += 3) {
        vertices[j + 2] = grid_values[i];
      }
      geom.attributes.position.needsUpdate = true;

      if (layer.properties.shading) {
        geom.computeVertexNormals();
      }

      if (callback) callback(mesh);
    };

    if (grid.url !== undefined) {
      Q3D.application.loadFile(grid.url, "arraybuffer", function (buf) {
        grid.array = new Float32Array(buf);
        buildGeometry(grid.array);
      });
    }
    else {    // WebKit Bridge
      if (grid.binary !== undefined) grid.array = new Float32Array(grid.binary.buffer, 0, grid.width * grid.height);
      buildGeometry(grid.array);
    }

    this.obj = mesh;
    return mesh;
  },

  buildSides: function (layer, parent, material, z0) {
    var planeWidth = this.data.width,
        planeHeight = this.data.height,
        grid = this.data.grid,
        grid_values = grid.array,
        w = grid.width,
        h = grid.height,
        k = w * (h - 1);

    var band_width = -2 * z0;

    // front and back
    var geom_fr = new THREE.PlaneBufferGeometry(planeWidth, band_width, w - 1, 1),
        geom_ba = geom_fr.clone();

    var vertices_fr = geom_fr.attributes.position.array,
        vertices_ba = geom_ba.attributes.position.array;

    var i, mesh;
    for (i = 0; i < w; i++) {
      vertices_fr[i * 3 + 1] = grid_values[k + i];
      vertices_ba[i * 3 + 1] = grid_values[w - 1 - i];
    }
    mesh = new THREE.Mesh(geom_fr, material);
    mesh.rotation.x = Math.PI / 2;
    mesh.position.y = -planeHeight / 2;
    mesh.name = "side";
    parent.add(mesh);

    mesh = new THREE.Mesh(geom_ba, material);
    mesh.rotation.x = Math.PI / 2;
    mesh.rotation.y = Math.PI;
    mesh.position.y = planeHeight / 2;
    mesh.name = "side";
    parent.add(mesh);

    // left and right
    var geom_le = new THREE.PlaneBufferGeometry(band_width, planeHeight, 1, h - 1),
        geom_ri = geom_le.clone();

    var vertices_le = geom_le.attributes.position.array,
        vertices_ri = geom_ri.attributes.position.array;

    for (i = 0; i < h; i++) {
      vertices_le[(i * 2 + 1) * 3] = grid_values[w * i];
      vertices_ri[i * 2 * 3] = -grid_values[w * (i + 1) - 1];
    }
    mesh = new THREE.Mesh(geom_le, material);
    mesh.rotation.y = -Math.PI / 2;
    mesh.position.x = -planeWidth / 2;
    mesh.name = "side";
    parent.add(mesh);

    mesh = new THREE.Mesh(geom_ri, material);
    mesh.rotation.y = Math.PI / 2;
    mesh.position.x = planeWidth / 2;
    mesh.name = "side";
    parent.add(mesh);

    // bottom
    var geom = new THREE.PlaneBufferGeometry(planeWidth, planeHeight, 1, 1);
    mesh = new THREE.Mesh(geom, material);
    mesh.rotation.x = Math.PI;
    mesh.position.z = z0;
    mesh.name = "bottom";
    parent.add(mesh);

    parent.updateMatrixWorld();
  },

  addEdges: function (layer, parent, material, z0) {

    var i, x, y,
        grid = this.data.grid,
        grid_values = grid.array,
        w = grid.width,
        h = grid.height,
        k = w * (h - 1),
        planeWidth = this.data.width,
        planeHeight = this.data.height,
        hpw = planeWidth / 2,
        hph = planeHeight / 2,
        psw = planeWidth / (w - 1),
        psh = planeHeight / (h - 1);

    var vl = [];

    // terrain edges
    var vl_fr = [],
        vl_bk = [],
        vl_le = [],
        vl_ri = [];

    for (i = 0; i < w; i++) {
      x = -hpw + psw * i;
      vl_fr.push(x, -hph, grid_values[k + i]);
      vl_bk.push(x, hph, grid_values[i]);
    }

    for (i = 0; i < h; i++) {
      y = hph - psh * i;
      vl_le.push(-hpw, y, grid_values[w * i]);
      vl_ri.push(hpw, y, grid_values[w * (i + 1) - 1]);
    }

    vl.push(vl_fr, vl_bk, vl_le, vl_ri);

    if (z0 !== undefined) {
      // horizontal rectangle at bottom
      vl.push([-hpw, -hph, z0,
                hpw, -hph, z0,
                hpw,  hph, z0,
               -hpw,  hph, z0,
               -hpw, -hph, z0]);

      // vertical lines at corners
      [[-hpw, -hph, grid_values[grid_values.length - w]],
       [ hpw, -hph, grid_values[grid_values.length - 1]],
       [ hpw,  hph, grid_values[w - 1]],
       [-hpw,  hph, grid_values[0]]].forEach(function (v) {

        vl.push([v[0], v[1], v[2], v[0], v[1], z0]);

      });
    }

    vl.forEach(function (v) {

      var geom = new THREE.BufferGeometry().setAttribute("position", new THREE.Float32BufferAttribute(v, 3));
      var obj = new THREE.Line(geom, material);
      obj.name = "frame";
      parent.add(obj);

    });

    parent.updateMatrixWorld();
  },

  // add quad wireframe
  addWireframe: function (layer, parent, material) {

    var grid = this.data.grid,
        grid_values = grid.array,
        w = grid.width,
        h = grid.height,
        planeWidth = this.data.width,
        planeHeight = this.data.height,
        hpw = planeWidth / 2,
        hph = planeHeight / 2,
        psw = planeWidth / (w - 1),
        psh = planeHeight / (h - 1);

    var v, geom, line, x, y, vx, vy, group = new THREE.Group();

    for (x = w - 1; x >= 0; x--) {
      v = [];
      vx = -hpw + psw * x;

      for (y = h - 1; y >= 0; y--) {
        v.push(vx, hph - psh * y, grid_values[x + w * y]);
      }

      geom = new THREE.BufferGeometry().setAttribute("position", new THREE.Float32BufferAttribute(v, 3));

      group.add(new THREE.Line(geom, material));
    }

    for (y = h - 1; y >= 0; y--) {
      v = [];
      vy = hph - psh * y;

      for (x = w - 1; x >= 0; x--) {
        v.push(-hpw + psw * x, vy, grid_values[x + w * y]);
      }

      geom = new THREE.BufferGeometry().setAttribute("position", new THREE.Float32BufferAttribute(v, 3));

      group.add(new THREE.Line(geom, material));
    }

    parent.add(group);
    parent.updateMatrixWorld();
  },

  getValue: function (x, y) {
    var grid = this.data.grid;
    if (0 <= x && x < grid.width && 0 <= y && y < grid.height) return grid.array[x + grid.width * y];
    return null;
  },

  contains: function (x, y) {
    var translate = this.data.translate,
        xmin = translate[0] - this.data.width / 2,
        xmax = translate[0] + this.data.width / 2,
        ymin = translate[1] - this.data.height / 2,
        ymax = translate[1] + this.data.height / 2;
    if (xmin <= x && x <= xmax && ymin <= y && y <= ymax) return true;
    return false;
  }

};


/*
Q3D.ClippedDEMBlock
*/
Q3D.ClippedDEMBlock = function () {
  this.materials = [];
  this.currentMtlIndex = 0;
};

Q3D.ClippedDEMBlock.prototype = {

  constructor: Q3D.ClippedDEMBlock,

  loadJSONObject: function (obj, layer, callback) {
    this.data = obj;
    var _this = this;

    // load material
    var m, mtl;
    for (var i = 0, l = (obj.materials || []).length; i < l; i++) {
      m = obj.materials[i];

      mtl = new Q3D.Material();
      mtl.loadJSONObject(m, function () {
        layer.requestRender();
      });
      this.materials[m.mtlIndex] = mtl;

      if (m.useNow) {
        if (this.obj) {
          layer.materials.removeItem(this.obj.material, true);

          this.obj.material = mtl.mtl;

          layer.materials.add(mtl);
          layer.requestRender();
        }
        this.currentMtlIndex = m.mtlIndex;
      }
    }

    if (obj.geom === undefined) return;

    var geom = new THREE.BufferGeometry(),
        mesh = new THREE.Mesh(geom, (this.materials[this.currentMtlIndex] || {}).mtl);
    mesh.position.fromArray(obj.translate);
    mesh.scale.z = obj.zScale;
    layer.addObject(mesh);

    var buildGeometry = function (obj) {

      var vertices = obj.triangles.v,
          base_width = layer.sceneData.width,
          base_height = layer.sceneData.height;
      var normals = [], uvs = [];
      for (var i = 0, l = vertices.length; i < l; i += 3) {
        normals.push(0, 0, 1);
        uvs.push(vertices[i] / base_width + 0.5, vertices[i + 1] / base_height + 0.5);
      }

      geom.setIndex(obj.triangles.f);
      geom.setAttribute("position", new THREE.Float32BufferAttribute(vertices, 3));
      geom.setAttribute("normal", new THREE.Float32BufferAttribute(normals, 3));
      geom.setAttribute("uv", new THREE.Float32BufferAttribute(uvs, 2));

      if (layer.properties.shading) {
        geom.computeVertexNormals();
      }

      geom.attributes.position.needsUpdate = true;
      geom.attributes.normal.needsUpdate = true;
      geom.attributes.uv.needsUpdate = true;

      _this.data.polygons = obj.polygons;
      if (callback) callback(mesh);
    };

    if (obj.geom.url !== undefined) {
      Q3D.application.loadFile(obj.geom.url, "json", function (obj) {
        buildGeometry(obj);
      });
    }
    else {    // WebKit Bridge
      buildGeometry(obj.geom);
    }

    this.obj = mesh;
    return mesh;
  },

  buildSides: function (layer, parent, material, z0) {
    var polygons = this.data.polygons,
        bzFunc = function (x, y) { return z0; };

    // make back-side material for bottom
    var mat_back = material.clone();
    mat_back.side = THREE.BackSide;
    layer.materials.add(mat_back);

    var geom, mesh, shape, vertices;
    for (var i = 0, l = polygons.length; i < l; i++) {
      var bnds = polygons[i];

      // sides
      for (var j = 0, m = bnds.length; j < m; j++) {
        vertices = Q3D.Utils.arrayToVec3Array(bnds[j]);
        geom = Q3D.Utils.createWallGeometry(vertices, bzFunc, true);
        mesh = new THREE.Mesh(geom, material);
        mesh.name = "side";
        parent.add(mesh);
      }

      // bottom
      shape = new THREE.Shape(Q3D.Utils.arrayToVec2Array(bnds[0]));
      for (j = 1, m = bnds.length; j < m; j++) {
        shape.holes.push(new THREE.Path(Q3D.Utils.arrayToVec2Array(bnds[j])));
      }
      geom = new THREE.ShapeBufferGeometry(shape);
      mesh = new THREE.Mesh(geom, mat_back);
      mesh.position.z = z0;
      mesh.name = "bottom";
      parent.add(mesh);
    }
    parent.updateMatrixWorld();
  },

  // not implemented
  getValue: function (x, y) {
    return null;
  },

  // not implemented
  contains: function (x, y) {
    return false;
  }

};

/*
Q3D.MapLayer
*/
Q3D.MapLayer = function () {
  this.properties = {};

  this.materials = new Q3D.Materials();
  this.materials.addEventListener("renderRequest", this.requestRender.bind(this));

  this.objectGroup = new Q3D.Group();
  this.objects = [];
};

Q3D.MapLayer.prototype = Object.create(THREE.EventDispatcher.prototype);
Q3D.MapLayer.prototype.constructor = Q3D.MapLayer;

Q3D.MapLayer.prototype.addObject = function (object) {

  object.userData.layerId = this.id;
  this.objectGroup.add(object);

  var o = this.objects;
  object.traverse(function (obj) {
    o.push(obj);
  });
  return this.objectGroup.children.length - 1;
};

Q3D.MapLayer.prototype.clearObjects = function () {
  // dispose of geometries
  this.objectGroup.traverse(function (obj) {
    if (obj.geometry) obj.geometry.dispose();
  });

  // dispose of materials
  this.materials.dispose();

  // remove all child objects from object group
  for (var i = this.objectGroup.children.length - 1; i >= 0; i--) {
    this.objectGroup.remove(this.objectGroup.children[i]);
  }
  this.objects = [];
};

Q3D.MapLayer.prototype.loadJSONObject = function (jsonObject, scene) {
  if (jsonObject.type == "layer") {
    // properties
    if (jsonObject.properties !== undefined) {
      this.properties = jsonObject.properties;
      this.visible = (jsonObject.properties.visible || Q3D.Config.allVisible) ? true : false;
    }

    if (jsonObject.data !== undefined) {
      this.clearObjects();

      // materials
      if (jsonObject.data.materials !== undefined) {
        this.materials.loadJSONObject(jsonObject.data.materials);
      }
    }

    this.sceneData = scene.userData;
    this._bbox = undefined;
  }
};

Object.defineProperty(Q3D.MapLayer.prototype, "clickable", {
  get: function () {
    return this.properties.clickable;
  }
});

Object.defineProperty(Q3D.MapLayer.prototype, "opacity", {
  get: function () {
    return this.materials.opacity();
  },
  set: function (value) {
    this.materials.setOpacity(value);
    this.requestRender();
  }
});

Object.defineProperty(Q3D.MapLayer.prototype, "visible", {
  get: function () {
    return this.objectGroup.visible;
  },
  set: function (value) {
    this.objectGroup.visible = value;
    this.requestRender();
  }
});

Q3D.MapLayer.prototype.boundingBox = function (forceUpdate) {
  if (!this._bbox || forceUpdate) {
    this._bbox = new THREE.Box3().setFromObject(this.objectGroup);
  }
  return this._bbox;
};

Q3D.MapLayer.prototype.setWireframeMode = function (wireframe) {
  this.materials.setWireframeMode(wireframe);
};

Q3D.MapLayer.prototype.requestRender = function () {
  this.dispatchEvent({type: "renderRequest"});
};


/*
Q3D.DEMLayer --> Q3D.MapLayer
*/
Q3D.DEMLayer = function () {
  Q3D.MapLayer.call(this);
  this.type = Q3D.LayerType.DEM;
  this.blocks = [];
};

Q3D.DEMLayer.prototype = Object.create(Q3D.MapLayer.prototype);
Q3D.DEMLayer.prototype.constructor = Q3D.DEMLayer;

Q3D.DEMLayer.prototype.loadJSONObject = function (jsonObject, scene) {
  var old_shading = this.properties.shading;
  var old_blockIsClipped = this.properties.clipped;

  Q3D.MapLayer.prototype.loadJSONObject.call(this, jsonObject, scene);
  if (jsonObject.type == "layer") {
    if (old_shading != jsonObject.properties.shading) {
      this.geometryCache = null;
      this.transformCache = null;
    }

    if (old_blockIsClipped !== jsonObject.properties.clipped) {
      // DEM type changed
      this.blocks = [];
    }

    var p = scene.userData,
        be = p.baseExtent;
    this.objectGroup.position.set(be.cx, be.cy, 0).sub(p.origin);
    this.objectGroup.position.z *= p.zScale;
    this.objectGroup.rotation.z = be.rotation * Q3D.deg2rad;
    this.objectGroup.updateMatrixWorld();

    if (jsonObject.data !== undefined) {
      jsonObject.data.forEach(function (obj) {
        this.buildBlock(obj, scene, this);
      }, this);
    }
  }
  else if (jsonObject.type == "block") {
    this.buildBlock(jsonObject, scene, this);
  }
};

Q3D.DEMLayer.prototype.buildBlock = function (jsonObject, scene, layer) {
  var _this = this,
      block = this.blocks[jsonObject.block];

  if (block === undefined) {
    block = (layer.properties.clipped) ? (new Q3D.ClippedDEMBlock()) : (new Q3D.DEMBlock());
    this.blocks[jsonObject.block] = block;
  }

  block.loadJSONObject(jsonObject, this, function (mesh) {

    var addEdges = function () {
      var material = new Q3D.Material();
      material.loadJSONObject(jsonObject.edges.mtl);
      _this.materials.add(material);

      block.addEdges(_this, mesh, material.mtl, (jsonObject.sides) ? jsonObject.sides.bottom : undefined);
    };

    var buildSides = function () {
      // sides and bottom
      var material = new Q3D.Material();
      material.loadJSONObject(jsonObject.sides.mtl);
      _this.materials.add(material);

      block.buildSides(_this, mesh, material.mtl, jsonObject.sides.bottom);
      _this.sideVisible = true;

      if (jsonObject.edges) addEdges();
    };

    if (jsonObject.wireframe) {
      var material = new Q3D.Material();
      material.loadJSONObject(jsonObject.wireframe.mtl);
      _this.materials.add(material);

      block.addWireframe(_this, mesh, material.mtl);

      var mtl = block.material.mtl;
      mtl.polygonOffset = true;
      mtl.polygonOffsetFactor = 1;
      mtl.polygonOffsetUnits = 1;
    }

    if (jsonObject.sides) {

      if (Q3D.Config.autoZShift) {
        scene.addEventListener("zShiftAdjusted", function listener(event) {

          // set adjusted z shift to every block
          _this.blocks.forEach(function (blk) {
            blk.data.zShiftA = event.sceneData.zShiftA;
          });
          buildSides();

          scene.removeEventListener("zShiftAdjusted", listener);

          _this.requestRender();
        });
      }
      else {
        buildSides();
      }
    }
    else if (jsonObject.edges) {
      addEdges();
    }

    _this.requestRender();
  });
};

// calculate elevation at the coordinates (x, y) on triangle face
Q3D.DEMLayer.prototype.getZ = function (x, y) {
  for (var i = 0, l = this.blocks.length; i < l; i++) {
    var block = this.blocks[i],
        data = block.data;
    if (!block.contains(x, y)) continue;

    var ix = data.width / (data.grid.width - 1),
        iy = data.height / (data.grid.height - 1);

    var xmin = data.translate[0] - data.width / 2,
        ymax = data.translate[1] + data.height / 2;

    var mx0 = Math.floor((x - xmin) / ix),
        my0 = Math.floor((ymax - y) / iy);

    var z = [block.getValue(mx0, my0),
             block.getValue(mx0 + 1, my0),
             block.getValue(mx0, my0 + 1),
             block.getValue(mx0 + 1, my0 + 1)];

    var px0 = xmin + ix * mx0,
        py0 = ymax - iy * my0;

    var sdx = (x - px0) / ix,
        sdy = (py0 - y) / iy;

    if (sdx <= 1 - sdy) return z[0] + (z[1] - z[0]) * sdx + (z[2] - z[0]) * sdy;
    else return z[3] + (z[2] - z[3]) * (1 - sdx) + (z[1] - z[3]) * (1 - sdy);
  }
  return null;
};

Q3D.DEMLayer.prototype.segmentizeLineString = function (lineString, zFunc) {
  // does not support multiple blocks
  if (zFunc === undefined) zFunc = function () { return 0; };
  var width = this.sceneData.width,
      height = this.sceneData.height;
  var xmin = -width / 2,
      ymax = height / 2;
  var grid = this.blocks[0].data.grid,
      ix = width / (grid.width - 1),
      iy = height / (grid.height - 1);
  var sort_func = function (a, b) { return a - b; };

  var pts = [];
  for (var i = 1, l = lineString.length; i < l; i++) {
    var pt1 = lineString[i - 1], pt2 = lineString[i];
    var x1 = pt1[0], x2 = pt2[0], y1 = pt1[1], y2 = pt2[1], z1 = pt1[2], z2 = pt2[2];
    var nx1 = (x1 - xmin) / ix,
        nx2 = (x2 - xmin) / ix;
    var ny1 = (ymax - y1) / iy,
        ny2 = (ymax - y2) / iy;
    var ns1 = Math.abs(ny1 + nx1),
        ns2 = Math.abs(ny2 + nx2);

    var p = [0], nvp = [[nx1, nx2], [ny1, ny2], [ns1, ns2]];
    for (var j = 0; j < 3; j++) {
      var v1 = nvp[j][0], v2 = nvp[j][1];
      if (v1 == v2) continue;
      var k = Math.ceil(Math.min(v1, v2));
      var n = Math.floor(Math.max(v1, v2));
      for (; k <= n; k++) {
        p.push((k - v1) / (v2 - v1));
      }
    }

    p.sort(sort_func);

    var x, y, z, lp = null;
    for (var j = 0, m = p.length; j < m; j++) {
      if (lp === p[j]) continue;
      if (p[j] == 1) break;

      x = x1 + (x2 - x1) * p[j];
      y = y1 + (y2 - y1) * p[j];

      if (z1 === undefined || z2 === undefined) z = zFunc(x, y);
      else z = z1 + (z2 - z1) * p[j];

      pts.push(new THREE.Vector3(x, y, z));

      // Q3D.Utils.putStick(x, y, zFunc);

      lp = p[j];
    }
  }
  // last point (= the first point)
  var pt = lineString[lineString.length - 1];
  pts.push(new THREE.Vector3(pt[0], pt[1], (pt[2] === undefined) ? zFunc(pt[0], pt[1]) : pt[2]));

  /*
  for (var i = 0, l = lineString.length - 1; i < l; i++) {
    Q3D.Utils.putStick(lineString[i][0], lineString[i][1], zFunc, 0.8);
  }
  */
  return pts;
};

Q3D.DEMLayer.prototype.setCurrentMaterial = function (mtlIndex) {

  this.materials.removeGroupItems(this.currentMtlIndex);

  this.currentMtlIndex = mtlIndex;

  var b, m;
  for (var i = 0, l = this.blocks.length; i < l; i++) {
    b = this.blocks[i];
    m = b.materials[mtlIndex];
    if (m !== undefined) {
      b.obj.material = m.mtl;
      this.materials.add(m);
    }
  }
  this.requestRender();
};

Q3D.DEMLayer.prototype.setSideVisible = function (visible) {
  this.sideVisible = visible;
  this.objectGroup.traverse(function (obj) {
    if (obj.name == "side" || obj.name == "bottom") obj.visible = visible;
  });
};

// texture animation
Q3D.DEMLayer.prototype.prepareMtlAnimation = function (from, to) {

  this.anim = [];

  var m, canvas, ctx, opt, mtl;
  var img_from, img_to;
  for (var i = 0; i < this.blocks.length; i++) {

    m = this.blocks[i].obj.material;

    img_from = this.blocks[i].materials[from].mtl.map.image;
    img_to = this.blocks[i].materials[to].mtl.map.image;

    canvas = document.createElement("canvas");
    canvas.width = img_to.width;
    canvas.height = img_to.height;

    ctx = canvas.getContext("2d");

    opt = {};
    opt.map = new THREE.CanvasTexture(canvas);
    opt.transparent = true;

    mtl = undefined;
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

    if (img_from instanceof ImageData) {    // WebKit Bridge
      var canvas_from = document.createElement("canvas");
      canvas_from.width = img_from.width;
      canvas_from.height = img_from.height;

      var canvas_to = document.createElement("canvas");
      canvas_to.width = img_to.width;
      canvas_to.height = img_to.height;

      var ctx_from = canvas_from.getContext("2d"),
          ctx_to = canvas_to.getContext("2d");

      ctx_from.putImageData(img_from, 0, 0);
      ctx_to.putImageData(img_to, 0, 0);

      img_from = canvas_from;
      img_to = canvas_to;
    }

    this.blocks[i].obj.material = mtl;

    this.materials.add(mtl);

    this.anim.push({
      img_from: img_from,
      img_to: img_to,
      ctx: ctx,
      tex: mtl.map
    });
  }
};

Q3D.DEMLayer.prototype.setTextureAt = function (elapsed, effect) {

  if (this.anim === undefined) return;

  effect = effect || 1;

  var a, w0, h0, w1, h1, ew0, ew1;
  for (var i = 0; i < this.anim.length; i++) {
    a = this.anim[i];
    w0 = a.img_from.width;
    h0 = a.img_from.height;
    w1 = a.img_to.width;
    h1 = a.img_to.height;

    if (effect == 1) {  // fade in
      a.ctx.globalAlpha = 1;    // (1 - elapsed);
      a.ctx.drawImage(a.img_from, 0, 0, w0, h0, 0, 0, w1, h1);

      a.ctx.globalAlpha = elapsed;
      a.ctx.drawImage(a.img_to, 0, 0, w0, h0, 0, 0, w1, h1);
    }
    else if (effect == 2) {  // slide
      if (elapsed === null) {
        a.ctx.drawImage(a.img_from, 0, 0, w0, h0, 0, 0, w1, h1);
      }
      else {
        ew0 = w0 * elapsed;
        ew1 = w1 * elapsed;
        a.ctx.drawImage(a.img_to, w0 - ew0, 0, ew0, h0, w1 - ew1, 0, ew1, h1);
      }
    }
    a.tex.needsUpdate = true;
  }
};

/*
Q3D.VectorLayer --> Q3D.MapLayer
*/
Q3D.VectorLayer = function () {
  Q3D.MapLayer.call(this);

  // this.labelConnectorGroup = undefined;
  // this.labelParentElement = undefined;
};

Q3D.VectorLayer.prototype = Object.create(Q3D.MapLayer.prototype);
Q3D.VectorLayer.prototype.constructor = Q3D.VectorLayer;

Q3D.VectorLayer.prototype.build = function (block) {};

Q3D.VectorLayer.prototype.clearLabels = function () {
  if (this.labelConnectorGroup) this.labelConnectorGroup.clear();

  // create parent element for labels
  var elem = this.labelParentElement;
  if (elem) {
    while (elem.lastChild) {
      elem.removeChild(elem.lastChild);
    }
  }
};

Q3D.VectorLayer.prototype.buildLabels = function (features, getPointsFunc) {
  if (this.properties.label === undefined || getPointsFunc === undefined) return;

  var zShift = this.sceneData.zShift,
      zScale = this.sceneData.zScale,
      z0 = zShift * zScale;
  var prop = this.properties.label,
      pIndex = prop.index,
      isRelative = prop.relative;

  var line_mat = new THREE.LineBasicMaterial({color: Q3D.Config.label.connectorColor});
  var f, text, e, pt0, pt1, geom, conn;

  for (var i = 0, l = features.length; i < l; i++) {
    f = features[i];
    text = f.prop[pIndex];
    if (text === null || text === "") continue;

    getPointsFunc(f).forEach(function (pt) {
      // create div element for label
      e = document.createElement("div");
      e.className = "label";
      e.innerHTML = text;
      this.labelParentElement.appendChild(e);

      pt0 = new THREE.Vector3(pt[0], pt[1], pt[2]);                                      // bottom
      pt1 = new THREE.Vector3(pt[0], pt[1], (isRelative) ? pt[2] + f.lh : z0 + f.lh);    // top

      if (Q3D.Config.label.clickable) {
        var obj = this.objectGroup.children[f.objIndices[0]];
        e.onclick = function () {
          app.scene.remove(app.queryMarker);
          app.highlightFeature(obj);
          app.render();
          app.showQueryResult({x: pt[0], y: pt[1], z: pt[2]}, obj, false);
        };
        e.classList.add("clickable");
      }
      else {
        e.classList.add("no-events");
      }

      // create connector
      geom = new THREE.Geometry();
      geom.vertices.push(pt1, pt0);

      conn = new THREE.Line(geom, line_mat);
      conn.userData.layerId = this.id;
      //conn.userData.featureId = i;
      conn.userData.elem = e;

      this.labelConnectorGroup.add(conn);

    }, this);
  }
};

Q3D.VectorLayer.prototype.loadJSONObject = function (jsonObject, scene) {
  Q3D.MapLayer.prototype.loadJSONObject.call(this, jsonObject, scene);
  if (jsonObject.type == "layer") {
    if (jsonObject.data !== undefined) {
      this.clearLabels();

      // build labels
      if (this.properties.label !== undefined) {
        // create a label connector group
        if (this.labelConnectorGroup === undefined) {
          this.labelConnectorGroup = new Q3D.Group();
          this.labelConnectorGroup.userData.layerId = this.id;
          this.labelConnectorGroup.visible = this.visible;
          scene.labelConnectorGroup.add(this.labelConnectorGroup);
        }

        // create a label parent element
        if (this.labelParentElement === undefined) {
          this.labelParentElement = document.createElement("div");
          this.labelParentElement.style.display = (this.visible) ? "block" : "none";
          scene.labelRootElement.appendChild(this.labelParentElement);
        }
      }

      (jsonObject.data.blocks || []).forEach(function (block) {
        if (block.url !== undefined) Q3D.application.loadJSONFile(block.url);
        else {
          this.build(block.features);
          if (this.properties.label !== undefined) this.buildLabels(block.features);
        }
      }, this);
    }
  }
  else if (jsonObject.type == "block") {
    this.build(jsonObject.features);
    if (this.properties.label !== undefined) this.buildLabels(jsonObject.features);
  }
};

Object.defineProperty(Q3D.VectorLayer.prototype, "visible", {
  get: function () {
    return Object.getOwnPropertyDescriptor(Q3D.MapLayer.prototype, "visible").get.call(this);
  },
  set: function (value) {
    if (this.labelParentElement) this.labelParentElement.style.display = (value) ? "block" : "none";
    if (this.labelConnectorGroup) this.labelConnectorGroup.visible = value;
    Object.getOwnPropertyDescriptor(Q3D.MapLayer.prototype, "visible").set.call(this, value);
  }
});


/*
Q3D.PointLayer --> Q3D.VectorLayer
*/
Q3D.PointLayer = function () {
  Q3D.VectorLayer.call(this);
  this.type = Q3D.LayerType.Point;
};

Q3D.PointLayer.prototype = Object.create(Q3D.VectorLayer.prototype);
Q3D.PointLayer.prototype.constructor = Q3D.PointLayer;

Q3D.PointLayer.prototype.loadJSONObject = function (jsonObject, scene) {
  if (jsonObject.type == "layer" && jsonObject.properties.objType == "Model File" && jsonObject.data !== undefined) {
    if (this.models === undefined) {
      var _this = this;

      this.models = new Q3D.Models();
      this.models.addEventListener("modelLoaded", function (event) {
        _this.materials.addFromObject3D(event.model.scene);
        _this.requestRender();
      });
    }
    else {
      this.models.clear();
    }
    this.models.loadJSONObject(jsonObject.data.models);
  }

  Q3D.VectorLayer.prototype.loadJSONObject.call(this, jsonObject, scene);
};

Q3D.PointLayer.prototype.build = function (features) {
  var objType = this.properties.objType;
  if (objType == "Point") {
    return this.buildPoints(features);
  }
  else if (objType == "Icon") {
    return this.buildIcons(features);
  }
  else if (objType == "Model File") {
    return this.buildModels(features);
  }

  var unitGeom, transform;
  if (this.cachedGeometryType === objType) {
    unitGeom = this.geometryCache;
    transform = this.transformCache;
  }
  else {
    var gt = this.geomAndTransformFunc(objType);
    unitGeom = gt[0];
    transform = gt[1];
  }

  var f, i, l, pts, mesh;
  for (var fidx = 0, flen = features.length; fidx < flen; fidx++) {
    f = features[fidx];
    f.objIndices = [];

    pts = f.geom.pts;
    for (i = 0, l = pts.length; i < l; i++) {

      mesh = new THREE.Mesh(unitGeom, this.materials.mtl(f.mtl));
      transform(mesh, f.geom, pts[i]);

      mesh.userData.properties = f.prop;

      f.objIndices.push(this.addObject(mesh));
    }
  }

  this.cachedGeometryType = objType;
  this.geometryCache = unitGeom;
  this.transformCache = transform;
};

Q3D.PointLayer.prototype.geomAndTransformFunc = function (objType) {

  var deg2rad = Q3D.deg2rad,
      rx = 90 * deg2rad;

  if (objType == "Sphere") {
    return [
      new THREE.SphereBufferGeometry(1, 32, 32),
      function (mesh, geom, pt) {
        mesh.scale.setScalar(geom.r);
        mesh.position.fromArray(pt);
      }
    ];
  }
  else if (objType == "Box") {
    return [
      new THREE.BoxBufferGeometry(1, 1, 1),
      function (mesh, geom, pt) {
        mesh.scale.set(geom.w, geom.h, geom.d);
        mesh.rotation.x = rx;
        mesh.position.set(pt[0], pt[1], pt[2] + geom.h / 2);
      }
    ];
  }
  else if (objType == "Disk") {
    var sz = this.sceneData.zScale;
    return [
      new THREE.CircleBufferGeometry(1, 32),
      function (mesh, geom, pt) {
        mesh.scale.set(geom.r, geom.r * sz, 1);
        mesh.rotateOnWorldAxis(Q3D.uv.i, -geom.d * deg2rad);
        mesh.rotateOnWorldAxis(Q3D.uv.k, -geom.dd * deg2rad);
        mesh.position.fromArray(pt);
      }
    ];
  }
  else if (objType == "Plane") {
    var sz = this.sceneData.zScale;
    return [
      new THREE.PlaneBufferGeometry(1, 1, 1, 1),
      function (mesh, geom, pt) {
        mesh.scale.set(geom.w, geom.l * sz, 1);
        mesh.rotateOnWorldAxis(Q3D.uv.i, -geom.d * deg2rad);
        mesh.rotateOnWorldAxis(Q3D.uv.k, -geom.dd * deg2rad);
        mesh.position.fromArray(pt);
      }
    ];
  }

  // Cylinder or Cone
  var radiusTop = (objType == "Cylinder") ? 1 : 0;
  return [
    new THREE.CylinderBufferGeometry(radiusTop, 1, 1, 32),
    function (mesh, geom, pt) {
      mesh.scale.set(geom.r, geom.h, geom.r);
      mesh.rotation.x = rx;
      mesh.position.set(pt[0], pt[1], pt[2] + geom.h / 2);
    }
  ];
};

Q3D.PointLayer.prototype.buildPoints = function (features) {
  var f, geom, obj;
  for (var fidx = 0, flen = features.length; fidx < flen; fidx++) {
    f = features[fidx];

    geom = new THREE.BufferGeometry().setAttribute("position", new THREE.Float32BufferAttribute(f.geom.pts, 3));

    obj = new THREE.Points(geom, this.materials.mtl(f.mtl));
    obj.userData.properties = f.prop;

    f.objIndices = [this.addObject(obj)];
  }
};

Q3D.PointLayer.prototype.buildIcons = function (features) {
  // each feature in this layer
  features.forEach(function (f) {
    var sprite,
        objs = [],
        material = this.materials.get(f.mtl);

    f.objIndices = [];
    for (var i = 0, l = f.geom.pts.length; i < l; i++) {
      sprite = new THREE.Sprite(material.mtl);
      sprite.position.fromArray(f.geom.pts[i]);
      sprite.userData.properties = f.prop;

      objs.push(sprite);
      f.objIndices.push(this.addObject(sprite));
    }

    material.callbackOnLoad(function () {
      var img = material.mtl.map.image;
      for (var i = 0; i < objs.length; i++) {
        // base size is 64 x 64
        objs[i].scale.set(img.width / 64 * f.geom.scale,
                          img.height / 64 * f.geom.scale,
                          1);
        objs[i].updateMatrixWorld();
      }
    });
  }, this);
};

Q3D.PointLayer.prototype.buildModels = function (features) {
  var _this = this,
      q = new THREE.Quaternion(),
      e = new THREE.Euler(),
      deg2rad = Q3D.deg2rad;

  // each feature in this layer
  features.forEach(function (f) {
    var model = _this.models.get(f.model);
    if (model === undefined) {
      console.log("Model File: There is a missing model.");
      return;
    }

    f.objIndices = [];
    f.geom.pts.forEach(function (pt) {
      model.callbackOnLoad(function (m) {
        var obj = m.scene.clone();
        obj.scale.setScalar(f.geom.scale);

        if (obj.rotation.x) {   // == -Math.PI / 2 (z-up model)
          // reset coordinate system to z-up and specified rotation
          obj.rotation.set(0, 0, 0);
          obj.quaternion.multiply(q.setFromEuler(e.set(f.geom.rotateX * deg2rad,
                                                       f.geom.rotateY * deg2rad,
                                                       f.geom.rotateZ * deg2rad,
                                                       f.geom.rotateO || "XYZ")));
        }
        else {
          // y-up to z-up and specified rotation
          obj.quaternion.multiply(q.setFromEuler(e.set(f.geom.rotateX * deg2rad,
                                                       f.geom.rotateY * deg2rad,
                                                       f.geom.rotateZ * deg2rad,
                                                       f.geom.rotateO || "XYZ")));
          obj.quaternion.multiply(q.setFromEuler(e.set(Math.PI / 2, 0, 0)));
        }

        var parent = new THREE.Group();
        parent.scale.set(1, 1, _this.sceneData.zScale);
        parent.position.fromArray(pt);
        parent.userData.properties = f.prop;
        parent.add(obj);

        f.objIndices.push(_this.addObject(parent));
      });
    });
  });
};

Q3D.PointLayer.prototype.buildLabels = function (features) {
  Q3D.VectorLayer.prototype.buildLabels.call(this, features, function (f) { return f.geom.pts; });
};


/*
Q3D.LineLayer --> Q3D.VectorLayer
*/
Q3D.LineLayer = function () {
  Q3D.VectorLayer.call(this);
  this.type = Q3D.LayerType.Line;
};

Q3D.LineLayer.prototype = Object.create(Q3D.VectorLayer.prototype);
Q3D.LineLayer.prototype.constructor = Q3D.LineLayer;

Q3D.LineLayer.prototype.clearObjects = function () {
  Q3D.VectorLayer.prototype.clearObjects.call(this);

  if (this.origMtls) {
    this.origMtls.dispose();
    this.origMtls = undefined;
  }
};

Q3D.LineLayer.prototype.build = function (features) {

  if (this._lastObjType !== this.properties.objType) this._createObject = null;

  var createObject = this._createObject || this.createObjFunc(this.properties.objType);

  var f, i, l, lines, obj;
  for (var fidx = 0, flen = features.length; fidx < flen; fidx++) {
    f = features[fidx];
    f.objIndices = [];

    lines = f.geom.lines;
    for (i = 0, l = lines.length; i < l; i++) {
      obj = createObject(f, lines[i]);
      obj.userData.properties = f.prop;
      obj.userData.mtl = f.mtl;

      f.objIndices.push(this.addObject(obj));
    }
  }

  this._lastObjType = this.properties.objType;
  this._createObject = createObject;
};

Q3D.LineLayer.prototype.createObjFunc = function (objType) {
  var materials = this.materials,
      sceneData = this.sceneData;

  if (objType == "Line") {
    return function (f, line) {
      var pt, vertices = [];
      for (var i = 0, l = line.length; i < l; i++) {
        pt = line[i];
        vertices.push(pt[0], pt[1], pt[2]);
      }
      var geom = new THREE.BufferGeometry().setAttribute("position", new THREE.Float32BufferAttribute(vertices, 3));

      var obj = new THREE.Line(geom, materials.mtl(f.mtl));
      if (obj.material instanceof THREE.LineDashedMaterial) obj.computeLineDistances();
      return obj;
    };
  }
  else if (objType == "Thick Line") {
    return function (f, line) {
      var pt, vertices = [];
      for (var i = 0, l = line.length; i < l; i++) {
        pt = line[i];
        vertices.push(pt[0], pt[1], pt[2]);
      }

      var line = new MeshLine();
      line.setPoints(vertices);

      return new THREE.Mesh(line, materials.mtl(f.mtl));
    };
  }
  else if (objType == "Pipe" || objType == "Cone") {
    var jointGeom, cylinGeom;
    if (objType == "Pipe") {
      jointGeom = new THREE.SphereBufferGeometry(1, 32, 32);
      cylinGeom = new THREE.CylinderBufferGeometry(1, 1, 1, 32);
    }
    else {
      cylinGeom = new THREE.CylinderBufferGeometry(0, 1, 1, 32);
    }

    var group, mesh, axis = Q3D.uv.j;
    var pt0 = new THREE.Vector3(), pt1 = new THREE.Vector3(), sub = new THREE.Vector3();

    return function (f, line) {
      group = new Q3D.Group();

      pt0.fromArray(line[0]);
      for (var i = 1, l = line.length; i < l; i++) {
        pt1.fromArray(line[i]);

        mesh = new THREE.Mesh(cylinGeom, materials.mtl(f.mtl));
        mesh.scale.set(f.geom.r, pt0.distanceTo(pt1), f.geom.r);
        mesh.position.set((pt0.x + pt1.x) / 2, (pt0.y + pt1.y) / 2, (pt0.z + pt1.z) / 2);
        mesh.quaternion.setFromUnitVectors(axis, sub.subVectors(pt1, pt0).normalize());
        group.add(mesh);

        if (jointGeom && i < l - 1) {
          mesh = new THREE.Mesh(jointGeom, materials.mtl(f.mtl));
          mesh.scale.setScalar(f.geom.r);
          mesh.position.copy(pt1);
          group.add(mesh);
        }

        pt0.copy(pt1);
      }
      return group;
    };
  }
  else if (objType == "Box") {
    // In this method, box corners are exposed near joint when both azimuth and slope of
    // the segments of both sides are different. Also, some unnecessary faces are created.
    var faces = [], vi;
    vi = [[0, 5, 4], [4, 5, 1],   // left turn - top, side, bottom
          [3, 0, 7], [7, 0, 4],
          [6, 3, 2], [2, 3, 7],
          [4, 1, 0], [0, 1, 5],   // right turn - top, side, bottom
          [1, 2, 5], [5, 2, 6],
          [2, 7, 6], [6, 7, 3]];

    for (var j = 0; j < 12; j++) {
      faces.push(new THREE.Face3(vi[j][0], vi[j][1], vi[j][2]));
    }

    return function (f, line) {
      var geometry = new THREE.Geometry();

      var geom, dist, rx, rz, wh4, vb4, vf4;
      var pt0 = new THREE.Vector3(), pt1 = new THREE.Vector3(), sub = new THREE.Vector3(),
          pt = new THREE.Vector3(), ptM = new THREE.Vector3(), scale1 = new THREE.Vector3(1, 1, 1),
          matrix = new THREE.Matrix4(), quat = new THREE.Quaternion();

      pt0.fromArray(line[0]);
      for (var i = 1, l = line.length; i < l; i++) {
        pt1.fromArray(line[i]);
        dist = pt0.distanceTo(pt1);
        sub.subVectors(pt1, pt0);
        rx = Math.atan2(sub.z, Math.sqrt(sub.x * sub.x + sub.y * sub.y));
        rz = Math.atan2(sub.y, sub.x) - Math.PI / 2;
        ptM.set((pt0.x + pt1.x) / 2, (pt0.y + pt1.y) / 2, (pt0.z + pt1.z) / 2);   // midpoint
        quat.setFromEuler(new THREE.Euler(rx, 0, rz, "ZXY"));
        matrix.compose(ptM, quat, scale1);

        // place a box to the segment
        geom = new THREE.BoxGeometry(f.geom.w, dist, f.geom.h);
        geom.applyMatrix(matrix);
        geometry.merge(geom);

        // joint
        // 4 vertices of backward side of current segment
        wh4 = [[-f.geom.w / 2, f.geom.h / 2],
              [f.geom.w / 2, f.geom.h / 2],
              [f.geom.w / 2, -f.geom.h / 2],
              [-f.geom.w / 2, -f.geom.h / 2]];
        vb4 = [];
        for (j = 0; j < 4; j++) {
          pt.set(wh4[j][0], -dist / 2, wh4[j][1]);
          pt.applyMatrix4(matrix);
          vb4.push(pt.clone());
        }

        if (vf4) {
          geom = new THREE.Geometry();
          geom.vertices = vf4.concat(vb4);
          geom.faces = faces;
          geometry.merge(geom);
        }

        // 4 vertices of forward side
        vf4 = [];
        for (j = 0; j < 4; j++) {
          pt.set(wh4[j][0], dist / 2, wh4[j][1]);
          pt.applyMatrix4(matrix);
          vf4.push(new THREE.Vector3(pt.x, pt.y, pt.z));
        }

        pt0.copy(pt1);
      }

      geometry.faceVertexUvs = [[]];
      geometry.mergeVertices();
      geometry.computeFaceNormals();
      return new THREE.Mesh(geometry, materials.mtl(f.mtl));
    };
  }
  else if (objType == "Wall") {
    var z0 = sceneData.zShift * sceneData.zScale;

    return function (f, line) {
      var pt;
      var vertices = [];
      for (var i = 0, l = line.length; i < l; i++) {
        pt = line[i];
        vertices.push(new THREE.Vector3(pt[0], pt[1], pt[2]));
      }
      var bzFunc = function (x, y) { return z0 + f.geom.bh; };
      return new THREE.Mesh(Q3D.Utils.createWallGeometry(vertices, bzFunc),
                            materials.mtl(f.mtl));
    };
  }
};

Q3D.LineLayer.prototype.buildLabels = function (features) {
  // Line layer doesn't support label
  // Q3D.VectorLayer.prototype.buildLabels.call(this, features);
};

// prepare for growing line animation
Q3D.LineLayer.prototype.prepareGrowingAnimation = function () {

  if (this.origMtls !== undefined) return;

  var _this = this;

  this.origMtls = new Q3D.Materials();
  this.origMtls.materials = this.materials.array;
  this.materials.array = [];

  var opt, m, mtls = this.origMtls.materials;

  for (var i = 0; i < mtls.length; i++) {

    m = mtls[i].mtl;

    if (m.isLineDashedMaterial) {
      m.gapSize = 1;
    }
    else if (m.isMeshLineMaterial) {
      m.dashArray = 2;
      m.transparent = true;
    }
    else if (m.isLineBasicMaterial) {
      m = new THREE.LineDashedMaterial({color: m.color});
    }

    this.materials.add(m);
  }

  // replace materials
  this.objectGroup.traverse(function (obj) {

    if (obj.userData.mtl !== undefined) {

      obj.material = _this.materials.mtl(obj.userData.mtl);

      if (obj.material.isLineDashedMaterial) {
        obj.computeLineDistances();

        var dists = obj.geometry.attributes.lineDistance.array;
        obj.lineLength = dists[dists.length - 1];

        for (i = 0; i < dists.length; i++) {
          dists[i] /= obj.lineLength;
        }
      }
    }
  });
};

Q3D.LineLayer.prototype.setLengthPercentage = function (percentage) {

  if (this.origMtls === undefined) return;

  var mtl, mtls = this.materials.array;
  for (var i = 0; i < mtls.length; i++) {
    mtl = mtls[i].mtl;
    if (mtl.isLineDashedMaterial) {
      mtl.dashSize = percentage;
    }
    else if (mtl.isMeshLineMaterial) {
      mtl.uniforms.dashOffset.value = -percentage;
    }
  }
};


/*
Q3D.PolygonLayer --> Q3D.VectorLayer
*/
Q3D.PolygonLayer = function () {
  Q3D.VectorLayer.call(this);
  this.type = Q3D.LayerType.Polygon;

  // for overlay
  this.borderVisible = true;
  this.sideVisible = true;
};

Q3D.PolygonLayer.prototype = Object.create(Q3D.VectorLayer.prototype);
Q3D.PolygonLayer.prototype.constructor = Q3D.PolygonLayer;

Q3D.PolygonLayer.prototype.loadJSONObject = function (jsonObject, scene) {
  Q3D.VectorLayer.prototype.loadJSONObject.call(this, jsonObject, scene);
};

Q3D.PolygonLayer.prototype.build = function (features) {

  if (this.properties.objType !== this._lastObjType) this._createObject = null;

  var createObject = this._createObject || this.createObjFunc(this.properties.objType);

  var f, obj;
  for (var i = 0, l = features.length; i < l; i++) {
    f = features[i];
    obj = createObject(f);
    obj.userData.properties = f.prop;

    f.objIndices = [this.addObject(obj)];
  }

  this._lastObjType = this.properties.objType;
  this._createObject = createObject;
};

Q3D.PolygonLayer.prototype.createObjFunc = function (objType) {

  var materials = this.materials;

  if (objType == "Polygon") {
    return function (f) {
      var geom = new THREE.BufferGeometry();
      geom.setAttribute("position", new THREE.Float32BufferAttribute(f.geom.triangles.v, 3));
      geom.setIndex(f.geom.triangles.f);
      geom = new THREE.Geometry().fromBufferGeometry(geom); // Flat shading doesn't work with combination of
                                                            // BufferGeometry and Lambert/Toon material.
      return new THREE.Mesh(geom, materials.mtl(f.mtl));
    };
  }
  else if (objType == "Extruded") {
    var createSubObject = function (f, polygon, z) {
      var i, l, j, m;

      var shape = new THREE.Shape(Q3D.Utils.arrayToVec2Array(polygon[0]));
      for (i = 1, l = polygon.length; i < l; i++) {
        shape.holes.push(new THREE.Path(Q3D.Utils.arrayToVec2Array(polygon[i])));
      }

      // extruded geometry
      var geom = new THREE.ExtrudeBufferGeometry(shape, {bevelEnabled: false, depth: f.geom.h});
      var mesh = new THREE.Mesh(geom, materials.mtl(f.mtl.face));
      mesh.position.z = z;

      if (f.mtl.edge !== undefined) {
        // edge
        var edge, bnd, v,
            h = f.geom.h,
            mtl = materials.mtl(f.mtl.edge);

        for (i = 0, l = polygon.length; i < l; i++) {
          bnd = polygon[i];

          v = [];
          for (j = 0, m = bnd.length; j < m; j++) {
            v.push(bnd[j][0], bnd[j][1], 0);
          }

          geom = new THREE.BufferGeometry().setAttribute("position", new THREE.Float32BufferAttribute(v, 3));

          edge = new THREE.Line(geom, mtl);
          mesh.add(edge);

          edge = new THREE.Line(geom, mtl);
          edge.position.z = h;
          mesh.add(edge);

          // vertical lines
          for (j = 0, m = bnd.length - 1; j < m; j++) {
            v = [bnd[j][0], bnd[j][1], 0,
                 bnd[j][0], bnd[j][1], h];

            geom = new THREE.BufferGeometry().setAttribute("position", new THREE.Float32BufferAttribute(v, 3));

            edge = new THREE.Line(geom, mtl);
            mesh.add(edge);
          }
        }
      }
      return mesh;
    };

    var polygons, centroids;

    return function (f) {
      polygons = f.geom.polygons;
      centroids = f.geom.centroids;

      if (polygons.length == 1) return createSubObject(f, polygons[0], centroids[0][2]);

      var group = new THREE.Group();
      for (var i = 0, l = polygons.length; i < l; i++) {
        group.add(createSubObject(f, polygons[i], centroids[i][2]));
      }
      return group;
    };
  }
  else if (objType == "Overlay") {

    return function (f) {

      var geom = new THREE.BufferGeometry();
      geom.setIndex(f.geom.triangles.f);
      geom.setAttribute("position", new THREE.Float32BufferAttribute(f.geom.triangles.v, 3));
      geom.computeVertexNormals();

      var mesh = new THREE.Mesh(geom, materials.mtl(f.mtl.face));

      // borders
      if (f.geom.brdr !== undefined) {
        var bnds, i, l, j, m;
        for (i = 0, l = f.geom.brdr.length; i < l; i++) {
          bnds = f.geom.brdr[i];
          for (j = 0, m = bnds.length; j < m; j++) {
            geom = new THREE.BufferGeometry().setAttribute("position", new THREE.Float32BufferAttribute(bnds[j], 3));

            mesh.add(new THREE.Line(geom, materials.mtl(f.mtl.brdr)));
          }
        }
      }
      return mesh;
    };
  }
};

Q3D.PolygonLayer.prototype.buildLabels = function (features) {
  Q3D.VectorLayer.prototype.buildLabels.call(this, features, function (f) { return f.geom.centroids; });
};

Q3D.PolygonLayer.prototype.setBorderVisible = function (visible) {
  if (this.properties.objType != "Overlay") return;

  this.objectGroup.children.forEach(function (parent) {
    for (var i = 0, l = parent.children.length; i < l; i++) {
      var obj = parent.children[i];
      if (obj instanceof THREE.Line) obj.visible = visible;
    }
  });
  this.borderVisible = visible;
};

Q3D.PolygonLayer.prototype.setSideVisible = function (visible) {
  if (this.properties.objType != "Overlay") return;

  this.objectGroup.children.forEach(function (parent) {
    for (var i = 0, l = parent.children.length; i < l; i++) {
      var obj = parent.children[i];
      if (obj instanceof THREE.Mesh) obj.visible = visible;
    }
  });
  this.sideVisible = visible;
};


/*
Q3D.Model
*/
Q3D.Model = function () {
  this.loaded = false;
};

Q3D.Model.prototype = {

  constructor: Q3D.Model,

  // callback is called when model has been completely loaded
  load: function (url, callback) {
    var _this = this;
    Q3D.application.loadModelFile(url, function (model) {
      _this.model = model;
      _this._loadCompleted(callback);
    });
  },

  loadData: function (data, ext, resourcePath, callback) {
    var _this = this;
    Q3D.application.loadModelData(data, ext, resourcePath, function (model) {
      _this.model = model;
      _this._loadCompleted(callback);
    });
  },

  loadJSONObject: function (jsonObject, callback) {
    if (jsonObject.url !== undefined) {
      this.load(jsonObject.url, callback);
    }
    else {
      this.loadData(atob(jsonObject.base64), jsonObject.ext, jsonObject.resourcePath, callback);
    }
  },

  _loadCompleted: function (anotherCallback) {
    this.loaded = true;

    if (this._callbacks !== undefined) {
      for (var i = 0; i < this._callbacks.length; i++) {
        this._callbacks[i](this.model);
      }
      this._callbacks = [];
    }

    if (anotherCallback) anotherCallback(this.model);
  },

  callbackOnLoad: function (callback) {
    if (this.loaded) return callback(this.model);

    if (this._callbacks === undefined) this._callbacks = [];
    this._callbacks.push(callback);
  }

};


/*
Q3D.Models
*/
Q3D.Models = function () {
  this.models = [];
  this.cache = {};
};

Q3D.Models.prototype = Object.create(THREE.EventDispatcher.prototype);
Q3D.Models.prototype.constructor = Q3D.Models;

Q3D.Models.prototype.loadJSONObject = function (jsonObject) {
  var _this = this;
  var callback = function (model) {
    _this.dispatchEvent({type: "modelLoaded", model: model});
  };

  var model, url;
  for (var i = 0, l = jsonObject.length; i < l; i++) {

    url = jsonObject[i].url;
    if (url !== undefined && this.cache[url] !== undefined) {
      model = this.cache[url];
    }
    else {
      model = new Q3D.Model();
      model.loadJSONObject(jsonObject[i], callback);

      if (url !== undefined) this.cache[url] = model;
    }
    this.models.push(model);
  }
};

Q3D.Models.prototype.get = function (index) {
  return this.models[index];
};

Q3D.Models.prototype.clear = function () {
  this.models = [];
};


// Q3D.Utils - Utilities
Q3D.Utils = {};

// Put a stick to given position (for debug)
Q3D.Utils.putStick = function (x, y, zFunc, h) {
  if (Q3D.Utils._stick_mat === undefined) Q3D.Utils._stick_mat = new THREE.LineBasicMaterial({color: 0xff0000});
  if (h === undefined) h = 0.2;
  if (zFunc === undefined) {
    zFunc = function (x, y) { return Q3D.application.scene.mapLayers[0].getZ(x, y); };
  }
  var z = zFunc(x, y);
  var geom = new THREE.Geometry();
  geom.vertices.push(new THREE.Vector3(x, y, z + h), new THREE.Vector3(x, y, z));
  var stick = new THREE.Line(geom, Q3D.Utils._stick_mat);
  Q3D.application.scene.add(stick);
};

// convert latitude and longitude in degrees to the following format
// Ndd°mm′ss.ss″, Eddd°mm′ss.ss″
Q3D.Utils.convertToDMS = function (lat, lon) {
  function toDMS(degrees) {
    var deg = Math.floor(degrees),
        m = (degrees - deg) * 60,
        min = Math.floor(m),
        sec = (m - min) * 60;
    return deg + "°" + ("0" + min).slice(-2) + "′" + ((sec < 10) ? "0" : "") + sec.toFixed(2) + "″";
  }

  return ((lat < 0) ? "S" : "N") + toDMS(Math.abs(lat)) + ", " +
         ((lon < 0) ? "W" : "E") + toDMS(Math.abs(lon));
};

Q3D.Utils.createWallGeometry = function (vertices, bzFunc, buffer_geom) {
  var geom = new THREE.Geometry(),
      pt = vertices[0];
  geom.vertices.push(
    new THREE.Vector3(pt.x, pt.y, pt.z),
    new THREE.Vector3(pt.x, pt.y, bzFunc(pt.x, pt.y)));

  for (var i = 1, i2 = 1, l = vertices.length; i < l; i++, i2+=2) {
    pt = vertices[i];
    geom.vertices.push(
      new THREE.Vector3(pt.x, pt.y, pt.z),
      new THREE.Vector3(pt.x, pt.y, bzFunc(pt.x, pt.y)));

    geom.faces.push(
      new THREE.Face3(i2 - 1, i2, i2 + 1),
      new THREE.Face3(i2 + 1, i2, i2 + 2));
  }
  geom.computeFaceNormals();

  if (buffer_geom) {
    return new THREE.BufferGeometry().fromGeometry(geom);
  }
  return geom;
};

Q3D.Utils.arrayToVec2Array = function (points) {
  var pt, pts = [];
  for (var i = 0, l = points.length; i < l; i++) {
    pt = points[i];
    pts.push(new THREE.Vector2(pt[0], pt[1]));
  }
  return pts;
};

Q3D.Utils.arrayToVec3Array = function (points, zFunc) {
  var pt, pts = [];
  if (zFunc === undefined) {
    for (var i = 0, l = points.length; i < l; i++) {
      pt = points[i];
      pts.push(new THREE.Vector3(pt[0], pt[1], pt[2]));
    }
  }
  else {
    for (var i = 0, l = points.length; i < l; i++) {
      pt = points[i];
      pts.push(new THREE.Vector3(pt[0], pt[1], zFunc(pt[0], pt[1])));
    }
  }
  return pts;
};

Q3D.Utils.arrayToFace3Array = function (faces) {
  var f, fs = [];
  for (var i = 0, l = faces.length; i < l; i++) {
    f = faces[i];
    fs.push(new THREE.Face3(f[0], f[1], f[2]));
  }
  return fs;
};

Q3D.Utils.setGeometryUVs = function (geom, base_width, base_height) {
  var face, v, uvs = [];
  for (var i = 0, l = geom.vertices.length; i < l; i++) {
    v = geom.vertices[i];
    uvs.push(new THREE.Vector2(v.x / base_width + 0.5, v.y / base_height + 0.5));
  }

  geom.faceVertexUvs[0] = [];
  for (var i = 0, l = geom.faces.length; i < l; i++) {
    face = geom.faces[i];
    geom.faceVertexUvs[0].push([uvs[face.a], uvs[face.b], uvs[face.c]]);
  }
};
