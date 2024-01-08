"use strict";
// Qgis2threejs.js
// (C) 2014 Minoru Akagi | MIT License
// https://github.com/minorua/Qgis2threejs

var Q3D = {VERSION: "2.4"};

Q3D.Config = {
  // scene
  autoZShift: false,  // automatic z shift adjustment
  bgColor: null,      // null is sky
  // camera
  orthoCamera: false,
  viewpoint: {                    // note: y-up
    pos: {x: 0, y: 100, z: 100},  // initial camera position
    lookAt: {x: 0, y: 0, z:0}
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
      azimuth: 220,   // note: default light azimuth of gdaldem hillshade is 315.
      altitude: 45    // altitude angle
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
  dem: {
    side: {
      bottomZ: -1.5     // in the unit of world coordinates
    },
    frame: {
      bottomZ: -1.5
    }
  },
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
    queryable: true
  },
  // decoration
  northArrow: {
    color: 0x8b4513,
    cameraDistance: 30,
    visible: false
  },

  qmarker: {
    r: 0.25,
    c: 0xffff00,
    o: 0.8
  },
  allVisible: false,  // set every layer visible property to true on load if set to true
  debugMode: false,
  exportMode: false   // set to true in glTF export mode
};

// consts
Q3D.LayerType = {
  DEM: "dem",
  Point: "point",
  Line: "line",
  Polygon: "polygon"
};

Q3D.MaterialType = {
  MeshLambert: 0,
  MeshPhong: 1,
  MeshToon: 2,
  LineBasic: 3,
  LineDashed: 4,
  Sprite: 5,
  Point: 6,
  Unknown: -1
};

Q3D.uv = {
  i: new THREE.Vector3(1, 0, 0),
  j: new THREE.Vector3(0, 1, 0),
  k: new THREE.Vector3(0, 0, 1)
};

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
  for (var i = this.children.length - 1 ; i >= 0; i--) {
    this.remove(this.children[i]);
  }
};


/*
Q3D.Scene -> THREE.Scene -> THREE.Object3D

.mapLayers: an object that holds map layers contained in this scene. the key is layerId.
            use .loadJSONObject() to add a map layer to this scene.
.userData: an object that holds metadata (crs, proj, baseExtent, rotation, width, zExaggeration, zShift, wgs84Center)
           properties of the scene object in JSON data?

.add(object):
.getObjectByName(layerId): returns the layer object specified by the layer id.

--
custom function
.loadJSONObject(json_obj): 
.toMapCoordinates(x, y, z): converts world coordinates to map coordinates
._rotatePoint(point, degrees, origin): 
*/
Q3D.Scene = function () {
  THREE.Scene.call(this);
  this.autoUpdate = false;

  // scene is z-up
  this.rotation.x = -Math.PI / 2;
  this.updateMatrixWorld();

  this.mapLayers = {};

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
    // set properties
    if (jsonObject.properties !== undefined) {
      this.userData = jsonObject.properties;

      var w = (this.userData.baseExtent[2] - this.userData.baseExtent[0]),
          h = (this.userData.baseExtent[3] - this.userData.baseExtent[1]);

      this.userData.scale = this.userData.width / w;
      this.userData.zScale = this.userData.scale * this.userData.zExaggeration;

      this.userData.origin = {x: this.userData.baseExtent[0] + w / 2,
                              y: this.userData.baseExtent[1] + h / 2,
                              z: -this.userData.zShift};
    }

    // load lights
    if (jsonObject.lights !== undefined) {
      // remove all existing lights
      this.lightGroup.clear();

      // build lights if scene data has lights settings
      // [not implemented yet]
    }

    // build default lights if this scene has no lights yet
    if (this.lightGroup.children.length == 0) this.buildDefaultLights();

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
      else {
        // console.error("unknown layer type:" + type);
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

Q3D.Scene.prototype.buildLights = function (lights) {
  var p, light, lambda, phi, x, y, z;
  var deg2rad = Math.PI / 180;
  for (var i = 0; i < lights.length; i++) {
    p = lights[i];
    if (p.type == "ambient") {
      this.lightGroup.add(new THREE.AmbientLight(p.color, p.intensity));
    }
    else if (p.type == "directional") {
      lambda = (90 - p.azimuth) * deg2rad;
      phi = p.altitude * deg2rad;

      x = Math.cos(phi) * Math.cos(lambda);
      y = Math.cos(phi) * Math.sin(lambda);
      z = Math.sin(phi);

      light = new THREE.DirectionalLight(p.color, p.intensity);
      light.position.set(x, y, z);
      this.lightGroup.add(light);
    }
  }
};

Q3D.Scene.prototype.buildDefaultLights = function () {
  this.buildLights(Q3D.Config.lights);
};

Q3D.Scene.prototype.requestRender = function () {
  this.dispatchEvent({type: "renderRequest"});
};

Q3D.Scene.prototype.queryableObjects = function () {
  var objs = [];
  for (var id in this.mapLayers) {
    objs = objs.concat(this.mapLayers[id].queryableObjects());
  }
  return objs;
};

Q3D.Scene.prototype.toMapCoordinates = function (x, y, z) {
  if (this.userData.rotation) {
    var pt = this._rotatePoint({x: x, y: y}, this.userData.rotation);
    x = pt.x;
    y = pt.y;
  }
  return {x: x / this.userData.scale + this.userData.origin.x,
          y: y / this.userData.scale + this.userData.origin.y,
          z: z / this.userData.zScale + this.userData.origin.z};
};

// real (geodetic/projected) coordinates to 3D scene coordinates
Q3D.Scene.prototype.toLocalCoordinates = function (x, y, z, isProjected) {
  // project x and y coordinates from WGS84 (long, lat)
  var pt;
  if (!isProjected && typeof proj4 !== "undefined") {
    pt = proj4(this.userData.proj).forward([x, y]);
    x = pt[0];
    y = pt[1];
  }

  x = (x - this.userData.origin.x) * this.userData.scale;
  y = (y - this.userData.origin.y) * this.userData.scale;
  z = (z - this.userData.origin.z) * this.userData.zScale;

  if (this.userData.rotation) {
    pt = this._rotatePoint({x: x, y: y}, -this.userData.rotation);
    x = pt.x;
    y = pt.y;
  }
  return {x: x, y: y, z: z};
};

// Rotate a point counter-clockwise around an origin
Q3D.Scene.prototype._rotatePoint = function (point, degrees, origin) {
  var theta = degrees * Math.PI / 180,
      c = Math.cos(theta),
      s = Math.sin(theta),
      x = point.x,
      y = point.y;

  if (origin) {
    x -= origin.x;
    y -= origin.y;
  }

  var xd = x * c - y * s,
      yd = x * s + y * c;

  if (origin) {
    xd += origin.x;
    yd += origin.y;
  }
  return {x: xd, y: yd};
};

Q3D.Scene.prototype.adjustZShift = function () {
  // initialize
  this.userData.zShiftA = 0;
  this.position.y = 0;
  this.updateMatrixWorld();

  var box = new THREE.Box3();
  for (var id in this.mapLayers) {
    if (this.mapLayers[id].visible) {
      box.union(this.mapLayers[id].boundingBox());
    }
  }

  // bbox zmin in map coordinates
  var zmin = (box.min.y === Infinity) ? 0 : (box.min.y / this.userData.zScale - this.userData.zShift);

  // shift scene so that bbox zmin becomes zero
  this.userData.zShiftA = -zmin;
  this.position.y = this.userData.zShiftA * this.userData.zScale;

  // keep positions of lights in world coordinates
  this.lightGroup.position.z = -this.position.y;

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
  var dispatchEvent = function (event) {
    if (Q3D.Config.debugMode) console.log("about to dispatch " + event + " event.");

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
    app.running = false;        // if true, animation loop is continued.

    // URL parameters
    app.urlParams = app.parseUrlParameters();
    if ("popup" in app.urlParams) {
      // open popup window
      var c = window.location.href.split("?");
      window.open(c[0] + "?" + c[1].replace(/&?popup/, ""), "popup", "width=" + app.urlParams.width + ",height=" + app.urlParams.height);
      app.popup.show("Another window has been opened.");
      return;
    }

    if (app.urlParams.width && app.urlParams.height) {
      // set container size
      container.style.width = app.urlParams.width + "px";
      container.style.height = app.urlParams.height + "px";
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

    // set viewpoint if specified by URL parameters
    var vars = app.urlParams;
    if (vars.cx !== undefined) Q3D.Config.viewpoint.pos = {x: parseFloat(vars.cx), y: parseFloat(vars.cy), z: parseFloat(vars.cz)};
    if (vars.tx !== undefined) Q3D.Config.viewpoint.lookAt = {x: parseFloat(vars.tx), y: parseFloat(vars.ty), z: parseFloat(vars.tz)};

    // camera
    app.buildCamera(Q3D.Config.orthoCamera);

    // scene
    app.scene = new Q3D.Scene();
    app.scene.addEventListener("renderRequest", function (event) {
      app.render();
    });

    var controls;
    if (typeof THREE.OrbitControls !== "undefined") {
      controls = new THREE.OrbitControls(app.camera, app.renderer.domElement);
      controls.enableKeys = false;

      var t = Q3D.Config.viewpoint.lookAt;
      controls.target.set(t.x, t.y, t.z);

      // custom functions
      var offset = new THREE.Vector3();
      var spherical = new THREE.Spherical();

      controls.moveForward = function (delta) {
        offset.copy(controls.object.position).sub(controls.target);
        var targetDistance = offset.length() * Math.tan((controls.object.fov / 2) * Math.PI / 180.0);
        offset.y = 0;
        offset.normalize();
        offset.multiplyScalar(-2 * delta * targetDistance / app.renderer.domElement.clientHeight);

        controls.object.position.add(offset);
        controls.target.add(offset);
      };
      controls.cameraRotate = function (thetaDelta, phiDelta) {
        offset.copy(controls.target).sub(controls.object.position);
        spherical.setFromVector3(offset);

        spherical.theta += thetaDelta;
        spherical.phi -= phiDelta;

        // restrict theta/phi to be between desired limits
        spherical.theta = Math.max(controls.minAzimuthAngle, Math.min(controls.maxAzimuthAngle, spherical.theta));
        spherical.phi = Math.max(controls.minPolarAngle, Math.min(controls.maxPolarAngle, spherical.phi));
        spherical.makeSafe();

        offset.setFromSpherical(spherical);
        controls.target.copy(controls.object.position).add(offset);
        controls.object.lookAt(controls.target);
      };

      controls.addEventListener("change", function (event) {
        app.render();
      });
    }

    app.controls = controls;
    app.controls.update();

    app.labelVisible = Q3D.Config.label.visible;

    // root element of labels
    app.scene.labelRootElement = document.getElementById("labels");
    app.scene.labelRootElement.style.display = (app.labelVisible) ? "block" : "none";

    // create a marker for queried point
    var opt = Q3D.Config.qmarker;
    app.queryMarker = new THREE.Mesh(new THREE.SphereBufferGeometry(opt.r),
                                     new THREE.MeshLambertMaterial({color: opt.c, opacity: opt.o, transparent: (opt.o < 1)}));

    app.highlightMaterial = new THREE.MeshLambertMaterial({emissive: 0x999900, transparent: true, opacity: 0.5});
    if (!Q3D.isIE) app.highlightMaterial.side = THREE.DoubleSide;    // Shader compilation error occurs with double sided material on IE11

    app.selectedObject = null;
    app.highlightObject = null;

    app.modelBuilders = [];
    app._wireframeMode = false;

    // add event listeners
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

  app.initLoadingManager = function () {
    if (app.loadingManager) {
      app.loadingManager.onLoad = app.loadingManager.onProgress = app.loadingManager.onError = undefined;
    }

    app.loadingManager = new THREE.LoadingManager(function () {
      // onLoad
      app.loadingManager.isLoading = false;

      document.getElementById("bar").classList.add("fadeout");

      dispatchEvent({type: "sceneLoaded"});
    },
    function (url, loaded, total) {
      // onProgress
      document.getElementById("bar").style.width = (loaded / total * 100) + "%";
    },
    function () {
      app.loadingManager.isLoading = false;

      dispatchEvent({type: "sceneLoadError"});
    });

    app.loadingManager.onStart = function () {
      app.loadingManager.isLoading = true;
    };

    app.loadingManager.isLoading = false;
  };

  app.initLoadingManager();

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
  };

  app.loadJSONFile = function (url, callback) {
    app.loadFile(url, "json", function (obj) {
      app.loadJSONObject(obj);
      if (callback) callback(obj);
    });
  };

  app.loadSceneFile = function (url, callback) {
    var ext = url.split(".").pop();
    if (ext == "json") app.loadJSONFile(url, callback);
    else if (ext == "js") {
      var e = document.createElement("script");
      e.src = url;
      e.onload = callback;
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

  app.mouseDownPoint = new THREE.Vector2();
  app.mouseUpPoint = new THREE.Vector2();

  app.eventListener = {

    keydown: function (e) {
      var controls = app.controls;
      var panDelta = 3, rotateAngle = 2 * Math.PI / 180;
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
            controls.rotateLeft(rotateAngle);
            break;
          case 38:  // UP
            controls.rotateUp(rotateAngle);
            break;
          case 39:  // RIGHT
            controls.rotateLeft(-rotateAngle);
            break;
          case 40:  // DOWN
            controls.rotateUp(-rotateAngle);
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
            controls.cameraRotate(rotateAngle, 0);
            break;
          case 38:  // Ctrl + UP
            controls.cameraRotate(0, rotateAngle);
            break;
          case 39:  // Ctrl + RIGHT
            controls.cameraRotate(-rotateAngle, 0);
            break;
          case 40:  // Ctrl + DOWN
            controls.cameraRotate(0, -rotateAngle);
            break;
          default:
            return;
        }
      }
      else {
        switch (e.keyCode) {
          case 37:  // LEFT
            controls.panLeft(panDelta, controls.object.matrix);
            break;
          case 38:  // UP
            controls.moveForward(3 * panDelta);    // horizontally forward
            break;
          case 39:  // RIGHT
            controls.panLeft(-panDelta, controls.object.matrix);
            break;
          case 40:  // DOWN
            controls.moveForward(-3 * panDelta);
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
      app.camera = new THREE.OrthographicCamera(-app.width / 10, app.width / 10, app.height / 10, -app.height / 10, 0.1, 10000);
    }
    else {
      app.camera = new THREE.PerspectiveCamera(45, app.width / app.height, 0.1, 10000);
    }

    var v = Q3D.Config.viewpoint,
        p = v.pos,
        t = v.lookAt;
    app.camera.position.set(p.x, p.y, p.z);
    app.camera.lookAt(t.x, t.y, t.z);
  };

  // rotation: direction to North (clockwise from up (+y), in degrees)
  app.buildNorthArrow = function (container, rotation) {
    app.renderer2 = new THREE.WebGLRenderer({alpha: true, antialias: true});
    app.renderer2.setClearColor(0, 0);
    app.renderer2.setSize(container.clientWidth, container.clientHeight);

    app.container2 = container;
    app.container2.appendChild(app.renderer2.domElement);

    app.camera2 = new THREE.PerspectiveCamera(45, container.clientWidth / container.clientHeight, 1, 1000);
    app.camera2.up = app.camera.up;

    app.scene2 = new Q3D.Scene();
    app.scene2.buildDefaultLights();

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
    if (rotation) mesh.rotation.z = -rotation * Math.PI / 180;
    app.scene2.add(mesh);
  };

  app.currentViewUrl = function () {
    var c = app.camera.position, t = app.controls.target, u = app.camera.up;
    var hash = "#cx=" + c.x + "&cy=" + c.y + "&cz=" + c.z;
    if (t.x || t.y || t.z) hash += "&tx=" + t.x + "&ty=" + t.y + "&tz=" + t.z;
    return window.location.href.split("#")[0] + hash;
  };

  // enable the controls
  app.start = function () {
    if (app.controls) app.controls.enabled = true;
  };

  app.pause = function () {
    app.running = false;
    if (app.controls) app.controls.enabled = false;
  };

  app.resume = function () {
    if (app.controls) app.controls.enabled = true;
  };

  app.startAnimation = function () {
    app.running = true;
    app.animate();
  };

  app.stopAnimation = function () {
    app.running = false;
  };

  // animation loop
  app.animate = function () {
    if (app.running) requestAnimationFrame(app.animate);
    app.render(true);
  };

  app.render = function (updateControls) {
    if (updateControls) app.controls.update();
    app.renderer.render(app.scene, app.camera);

    // North arrow
    if (app.renderer2) {
      app.camera.getWorldDirection(vec3);
      app.camera2.position.copy(vec3.negate().setLength(Q3D.Config.northArrow.cameraDistance));
      app.camera2.quaternion.copy(app.camera.quaternion);

      app.renderer2.render(app.scene2, app.camera2);
    }

    // labels
    app.updateLabelPosition();
  };

  // TODO: remove [obsolete] app.setIntervalRender
  (function () {
    var _delay, _repeat, _times, _id = null;
    var func = function () {
      app.render();
      if (_repeat <= ++_times) {
        clearInterval(_id);
        _id = null;
      }
    };
    app.setIntervalRender = function (delay, repeat) {
      if (_id === null || _delay != delay) {
        if (_id !== null) {
          clearInterval(_id);
        }
        _id = setInterval(func, delay);
        _delay = delay;
      }
      _repeat = repeat;
      _times = 0;
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
          vec3.set(pt0.x, pt0.z, -pt0.y);

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
        vec3.set(pt0.x, pt0.z, -pt0.y).project(camera);
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
    app.controls.autoRotate = enabled;
    if (enabled) {
      app.startAnimation();
    }
    else {
      app.stopAnimation();
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
    return ray.intersectObjects(app.scene.queryableObjects());
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

  app.queryTargetPosition = new THREE.Vector3();  // y-up

  app.cameraAction = {

    move: function (x, y, z) {    // z-up
      if (x === undefined) app.camera.position.copy(app.queryTargetPosition);
      else app.camera.position.set(x, z, -y);   // y-up
      app.render(true);
    },

    vecZoom: new THREE.Vector3(0, 10, 10),    // y-up

    zoomIn: function (x, y, z) {    // z-up
      if (x === undefined) vec3.copy(app.queryTargetPosition);
      else vec3.set(x, z, -y);   // y-up

      app.camera.position.addVectors(vec3, app.cameraAction.vecZoom);
      app.camera.lookAt(vec3.x, vec3.y, vec3.z);
      if (app.controls.target !== undefined) app.controls.target.copy(vec3);
      app.render(true);
    },

    orbit: function (x, y, z) {   // z-up
      if (app.controls.target === undefined) return;

      if (x === undefined) app.controls.target.copy(app.queryTargetPosition);
      else app.controls.target.set(x, z, -y);   // y-up
      app.setRotateAnimationMode(true);
    }

  };

  app.showQueryResult = function (point, obj, hide_coords) {
    app.queryTargetPosition.set(point.x, point.z, -point.y);    // y-up

    var layer = app.scene.mapLayers[obj.userData.layerId],
        e = document.getElementById("qr_layername");

    // layer name
    if (layer && e) e.innerHTML = layer.properties.name;

    // clicked coordinates
    e = document.getElementById("qr_coords_table");
    if (e) {
      if (hide_coords) {
        e.classList.add("hidden");
      }
      else {
        e.classList.remove("hidden");

        var pt = app.scene.toMapCoordinates(point.x, point.y, point.z);
        e = document.getElementById("qr_coords");
        if (typeof proj4 === "undefined") {
          e.innerHTML = [pt.x.toFixed(2), pt.y.toFixed(2), pt.z.toFixed(2)].join(", ");
        }
        else {
          var lonLat = proj4(app.scene.userData.proj).inverse([pt.x, pt.y]);
          e.innerHTML = Q3D.Utils.convertToDMS(lonLat[1], lonLat[0]) + ", Elev. " + pt.z.toFixed(2);
        }
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
    if (s != 1) clone.scale.set(clone.scale.x * s, clone.scale.y * s, clone.scale.z * s);
    // highlightObject.add(clone);

    // add the highlight object to the scene
    app.scene.add(clone);

    app.selectedObject = object;
    app.highlightObject = clone;
  };

  app.canvasClicked = function (e) {
    var canvasOffset = app._offset(app.renderer.domElement);
    var objs = app.intersectObjects(e.clientX - canvasOffset.left, e.clientY - canvasOffset.top);
    var obj, pt;

    for (var i = 0, l = objs.length; i < l; i++) {
      obj = objs[i];

      // query marker
      pt = {x: obj.point.x, y: -obj.point.z, z: obj.point.y};  // obj's coordinate system is y-up
      app.queryMarker.position.set(pt.x, pt.y, pt.z);              // this is z-up
      app.scene.add(app.queryMarker);

      // get layerId of clicked object
      var layerId, object = obj.object;
      while (object) {
        layerId = object.userData.layerId;
        if (layerId !== undefined) break;
        object = object.parent;
      }

      app.highlightFeature(object);
      app.render();
      app.showQueryResult(pt, object);

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
          labels.push({pt: new THREE.Vector3(pt.x, pt.z, -pt.y),      // in world coordinates
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

      var label, text, x, y;
      for (var i = 0, l = idx_dist.length; i < l; i++) {
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
    app.renderer.render(app.scene, app.camera);

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

  // callback is called when material has been completely loaded
  loadJSONObject: function (jsonObject, callback) {
    this.origProp = jsonObject;

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
      }
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
    else if (m.type == Q3D.MaterialType.LineBasic) {
      this.mtl = new THREE.LineBasicMaterial(opt);
    }
    else if (m.type == Q3D.MaterialType.LineDashed) {
      opt.dashSize = Q3D.Config.line.dash.dashSize;
      opt.gapSize = Q3D.Config.line.dash.gapSize;
      this.mtl = new THREE.LineDashedMaterial(opt);
    }
    else {
      opt.color = 0xffffff;
      this.mtl = new THREE.SpriteMaterial(opt);
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

  set: function (material) {
    this.mtl = material;
    this.origProp = {};
  },

  type: function () {
    if (this.mtl instanceof THREE.MeshLambertMaterial) return Q3D.MaterialType.MeshLambert;
    if (this.mtl instanceof THREE.MeshPhongMaterial) return Q3D.MaterialType.MeshPhong;
    if (this.mtl instanceof THREE.LineBasicMaterial) return Q3D.MaterialType.LineBasic;
    if (this.mtl instanceof THREE.LineDashedMaterial) return Q3D.MaterialType.LineDashed;
    if (this.mtl instanceof THREE.SpriteMaterial) return Q3D.MaterialType.Sprite;
    if (this.mtl === undefined) return undefined;
    if (this.mtl === null) return null;
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
  this.materials = [];
};

Q3D.Materials.prototype = Object.create(THREE.EventDispatcher.prototype);
Q3D.Materials.prototype.constructor = Q3D.Materials;

// material: instance of Q3D.Material object or THREE.Material-based object
Q3D.Materials.prototype.add = function (material) {
  if (material instanceof Q3D.Material) this.materials.push(material);
  else {
    var mtl = new Q3D.Material();
    mtl.set(material);
    this.materials.push(mtl);
  }
};

Q3D.Materials.prototype.get = function (index) {
  return this.materials[index];
};

Q3D.Materials.prototype.mtl = function (index) {
  return this.materials[index].mtl;
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
  for (var i = 0, l = this.materials.length; i < l; i++) {
    this.materials[i].dispose();
  }
  this.materials = [];
};

Q3D.Materials.prototype.addFromObject3D = function (object) {
  var _this = this, mtls = [];

  object.traverse(function (obj) {
    if (obj.material === undefined) return;
    ((obj.material instanceof Array) ? obj.material : [obj.material]).forEach(function (mtl) {
      if (mtls.indexOf(mtl) == -1) {
        mtls.push(mtl);
      }
    });
  });

  var material;
  for (var i = 0, l = mtls.length; i < l; i++) {
    material = new Q3D.Material();
    material.set(mtls[i]);
    this.materials.push(material);
  }
};

// opacity
Q3D.Materials.prototype.opacity = function () {
  if (this.materials.length == 0) return 1;

  var sum = 0;
  for (var i = 0, l = this.materials.length; i < l; i++) {
    sum += this.materials[i].mtl.opacity;
  }
  return sum / this.materials.length;
};

Q3D.Materials.prototype.setOpacity = function (opacity) {
  var material;
  for (var i = 0, l = this.materials.length; i < l; i++) {
    material = this.materials[i];
    material.mtl.transparent = Boolean(material.origProp.t) || (opacity < 1);
    material.mtl.opacity = opacity;
  }
};

// wireframe: boolean
Q3D.Materials.prototype.setWireframeMode = function (wireframe) {
  var material;
  for (var i = 0, l = this.materials.length; i < l; i++) {
    material = this.materials[i];
    if (material.origProp.w || material.mtl instanceof THREE.LineBasicMaterial) continue;
    material.mtl.wireframe = wireframe;
  }
};


/*
Q3D.DEMBlock
*/
Q3D.DEMBlock = function () {};

Q3D.DEMBlock.prototype = {

  constructor: Q3D.DEMBlock,

  // obj: json object
  loadJSONObject: function (obj, layer, callback) {
    var _this = this,
        grid = obj.grid;
    this.data = obj;

    // load material
    this.material = new Q3D.Material();
    this.material.loadJSONObject(obj.material, function () {
      layer.requestRender();
    });
    layer.materials.add(this.material);

    // create a plane geometry
    var geom;
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
    var mesh = new THREE.Mesh(geom, this.material.mtl);
    mesh.position.fromArray(obj.translate);
    mesh.scale.z = obj.zScale;
    layer.addObject(mesh);

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

    var e0 =  z0 / this.data.zScale - this.data.zShift - (this.data.zShiftA || 0),
        band_width = -2 * e0;

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
    var geom;
    if (Q3D.Config.exportMode) {
      geom = new THREE.PlaneBufferGeometry(planeWidth, planeHeight, w - 1, h - 1);
    }
    else {
      geom = new THREE.PlaneBufferGeometry(planeWidth, planeHeight, 1, 1);
    }
    mesh = new THREE.Mesh(geom, material);
    mesh.rotation.x = Math.PI;
    mesh.position.z = e0;
    mesh.name = "bottom";
    parent.add(mesh);

    parent.updateMatrixWorld();
  },

  buildFrame: function (layer, parent, material, z0) {
    var grid = this.data.grid,
        planeWidth = this.data.width,
        planeHeight = this.data.height;

    // horizontal rectangle at bottom
    var hw = planeWidth / 2,
        hh = planeHeight / 2,
        e0 =  z0 / this.data.zScale - this.data.zShift - (this.data.zShiftA || 0);
    var v = [-hw, -hh, e0,
              hw, -hh, e0,
              hw,  hh, e0,
             -hw,  hh, e0,
             -hw, -hh, e0];

    var geom = new THREE.BufferGeometry();
    geom.addAttribute("position", new THREE.Float32BufferAttribute(v, 3));

    var obj = new THREE.Line(geom, material);
    obj.name = "frame";
    parent.add(obj);

    // vertical lines at corners
    v = [[-hw, -hh, grid.array[grid.array.length - grid.width]],
         [ hw, -hh, grid.array[grid.array.length - 1]],
         [ hw,  hh, grid.array[grid.width - 1]],
         [-hw,  hh, grid.array[0]]];

    v.forEach(function (p) {
      var geom = new THREE.BufferGeometry(),
          vl = [p[0], p[1], p[2], p[0], p[1], e0];
      geom.addAttribute("position", new THREE.Float32BufferAttribute(vl, 3));

      var obj = new THREE.Line(geom, material);
      obj.name = "frame";
      parent.add(obj);
    });

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
Q3D.ClippedDEMBlock = function () {};

Q3D.ClippedDEMBlock.prototype = {

  constructor: Q3D.ClippedDEMBlock,

  loadJSONObject: function (obj, layer, callback) {
    this.data = obj;
    var _this = this;

    // load material
    this.material = new Q3D.Material();
    this.material.loadJSONObject(obj.material, function () {
      layer.requestRender();
    });
    layer.materials.add(this.material);

    var geom = new THREE.BufferGeometry(),
        mesh = new THREE.Mesh(geom, this.material.mtl);
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
      geom.addAttribute("position", new THREE.Float32BufferAttribute(vertices, 3));
      geom.addAttribute("normal", new THREE.Float32BufferAttribute(normals, 3));
      geom.addAttribute("uv", new THREE.Float32BufferAttribute(uvs, 2));

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
        e0 =  z0 / this.data.zScale - this.data.zShift - (this.data.zShiftA || 0),
        bzFunc = function (x, y) { return e0; };

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
      for (var j = 1, m = bnds.length; j < m; j++) {
        shape.holes.push(new THREE.Path(Q3D.Utils.arrayToVec2Array(bnds[j])));
      }
      geom = new THREE.ShapeBufferGeometry(shape);
      mesh = new THREE.Mesh(geom, mat_back);
      mesh.position.z = e0;
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
  this.queryable = true;

  this.materials = new Q3D.Materials();
  this.materials.addEventListener("renderRequest", this.requestRender.bind(this));

  this.objectGroup = new Q3D.Group();
  this.queryObjs = [];
};

Q3D.MapLayer.prototype = Object.create(THREE.EventDispatcher.prototype);
Q3D.MapLayer.prototype.constructor = Q3D.MapLayer;

Q3D.MapLayer.prototype.addObject = function (object, queryable) {
  if (queryable === undefined) queryable = this.queryable;

  object.userData.layerId = this.id;
  this.objectGroup.add(object);

  if (queryable) {
    var queryObjs = this.queryObjs;
    object.traverse(function (obj) {
      queryObjs.push(obj);
    });
  }
  return this.objectGroup.children.length - 1;
};

Q3D.MapLayer.prototype.queryableObjects = function () {
  return (this.visible) ? this.queryObjs : [];
};

Q3D.MapLayer.prototype.removeAllObjects = function () {
  // dispose of geometries
  this.objectGroup.traverse(function (obj) {
    if (obj.geometry) obj.geometry.dispose();
  });

  // dispose of materials
  this.materials.dispose();

  // remove all child objects from object group
  for (var i = this.objectGroup.children.length - 1 ; i >= 0; i--) {
    this.objectGroup.remove(this.objectGroup.children[i]);
  }
  this.queryObjs = [];
};

Q3D.MapLayer.prototype.loadJSONObject = function (jsonObject, scene) {
  if (jsonObject.type == "layer") {
    // properties
    if (jsonObject.properties !== undefined) {
      this.properties = jsonObject.properties;
      this.visible = (jsonObject.properties.visible || Q3D.Config.allVisible) ? true : false;
    }

    if (jsonObject.data !== undefined) {
      this.removeAllObjects();

      // materials
      if (jsonObject.data.materials !== undefined) {
        this.materials.loadJSONObject(jsonObject.data.materials);
      }
    }

    this.sceneData = scene.userData;
    this._bbox = undefined;
  }
};

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
}

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
  Q3D.MapLayer.prototype.loadJSONObject.call(this, jsonObject, scene);
  if (jsonObject.type == "layer") {
    if (old_shading != jsonObject.properties.shading) {
      this.geometryCache = null;
    }

    if (jsonObject.data !== undefined) {
      jsonObject.data.forEach(function (obj) {
        this.buildBlock(obj, scene);
      }, this);
    }
  }
  else if (jsonObject.type == "block") {
    this.buildBlock(jsonObject, scene);
  }
};

Q3D.DEMLayer.prototype.buildBlock = function (jsonObject, scene) {
  var _this = this;

  var index = jsonObject.block;
  this.blocks[index] = (jsonObject.grid !== undefined) ? (new Q3D.DEMBlock()) : (new Q3D.ClippedDEMBlock());
  this.blocks[index].loadJSONObject(jsonObject, this, function (m) {

    if (jsonObject.sides || jsonObject.frame) {

      _this.sideVisible = true;

      var buildSides = function () {
        var material;
        // build sides and bottom
        if (jsonObject.sides) {
          material = new Q3D.Material();
          material.loadJSONObject(jsonObject.sides.mtl);
          _this.materials.add(material);

          _this.blocks[index].buildSides(_this, m, material.mtl, Q3D.Config.dem.side.bottomZ);
        }
        // build frame
        if (jsonObject.frame) {
          material = new Q3D.Material();
          material.loadJSONObject(jsonObject.frame.mtl);
          _this.materials.add(material);

          _this.blocks[index].buildFrame(_this, m, material.mtl, Q3D.Config.dem.frame.bottomZ);
        }
        _this.requestRender();
      };

      if (Q3D.Config.autoZShift) {
        scene.addEventListener("zShiftAdjusted", function listener(event) {
          // set adjusted z shift to every block
          _this.blocks.forEach(function (block) {
            block.data.zShiftA = event.sceneData.zShiftA;
          });
          buildSides();
          scene.removeEventListener("zShiftAdjusted", listener);
        });
      }
      else {
        buildSides();
      }
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

    // console.log(x, y, mx0, my0, sdx, sdy);

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

Q3D.DEMLayer.prototype.setSideVisible = function (visible) {
  this.sideVisible = visible;
  this.objectGroup.traverse(function (obj) {
    if (obj.name == "side" || obj.name == "bottom" || obj.name == "frame") obj.visible = visible;
  });
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

      if (Q3D.Config.label.queryable) {
        var obj = this.objectGroup.children[f.objIndices[0]];
        e.onclick = function () {
          app.scene.remove(app.queryMarker);
          app.highlightFeature(obj);
          app.render();
          app.showQueryResult({x: pt[0], y: pt[1], z: pt[2]}, obj, true);
        };
        e.classList.add("queryable");
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
  Q3D.VectorLayer.prototype.loadJSONObject.call(this, jsonObject, scene);
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
};

Q3D.PointLayer.prototype.build = function (features) {
  var objType = this.properties.objType;
  if (objType == "Point") { this.buildPoints(features); return; }
  if (objType == "Icon") { this.buildIcons(features); return; }
  if (objType == "Model File") { this.buildModels(features); return; }

  var deg2rad = Math.PI / 180, rx = 90 * deg2rad;
  var setSR, unitGeom;

  if (this.cachedGeometryType == objType) {
    unitGeom = this.geometryCache;
  }

  if (objType == "Sphere") {
    setSR = function (mesh, geom) {
      mesh.scale.set(geom.r, geom.r, geom.r);
    };
    unitGeom = unitGeom || new THREE.SphereBufferGeometry(1, 32, 32);
  }
  else if (objType == "Box") {
    setSR = function (mesh, geom) {
      mesh.scale.set(geom.w, geom.h, geom.d);
      mesh.rotation.x = rx;
    };
    unitGeom = unitGeom || new THREE.BoxBufferGeometry(1, 1, 1);
  }
  else if (objType == "Disk") {
    var sz = this.sceneData.zExaggeration;    // set 1 if not to be elongated
    setSR = function (mesh, geom) {
      mesh.scale.set(geom.r, geom.r * sz, 1);
      mesh.rotateOnWorldAxis(Q3D.uv.i, -geom.d * deg2rad);
      mesh.rotateOnWorldAxis(Q3D.uv.k, -geom.dd * deg2rad);
    };
    unitGeom = unitGeom || new THREE.CircleBufferGeometry(1, 32);
  }
  else if (objType == "Plane") {
    var sz = this.sceneData.zExaggeration;    // set 1 if not to be elongated
    setSR = function (mesh, geom) {
      mesh.scale.set(geom.w, geom.l * sz, 1);
      mesh.rotateOnWorldAxis(Q3D.uv.i, -geom.d * deg2rad);
      mesh.rotateOnWorldAxis(Q3D.uv.k, -geom.dd * deg2rad);
    };
    unitGeom = unitGeom || new THREE.PlaneBufferGeometry(1, 1, 1, 1);
  }
  else {  // Cylinder or Cone
    setSR = function (mesh, geom) {
      mesh.scale.set(geom.r, geom.h, geom.r);
      mesh.rotation.x = rx;
    };
    unitGeom = unitGeom || ((objType == "Cylinder") ? new THREE.CylinderBufferGeometry(1, 1, 1, 32) : new THREE.CylinderBufferGeometry(0, 1, 1, 32));
  }

  // iteration for features
  var materials = this.materials;
  var f, geom, z_addend, i, l, mesh, pt;
  for (var fidx = 0, flen = features.length; fidx < flen; fidx++) {
    f = features[fidx];
    f.objIndices = []

    geom = f.geom;
    z_addend = (geom.h) ? geom.h / 2 : 0;
    for (i = 0, l = geom.pts.length; i < l; i++) {
      mesh = new THREE.Mesh(unitGeom, materials.mtl(f.mtl));
      setSR(mesh, geom);

      pt = geom.pts[i];
      mesh.position.set(pt[0], pt[1], pt[2] + z_addend);
      mesh.userData.properties = f.prop;

      f.objIndices.push(this.addObject(mesh));
    }
  }

  this.geometryCache = unitGeom;
  this.cachedGeometryType = objType;
};

Q3D.PointLayer.prototype.buildPoints = function (features) {
  var f, geom, obj;
  for (var fidx = 0, flen = features.length; fidx < flen; fidx++) {
    f = features[fidx];

    geom = new THREE.BufferGeometry();
    geom.addAttribute("position",
                      new THREE.BufferAttribute(new Float32Array(f.geom.pts), 3));

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
      deg2rad = Math.PI / 180;

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
        obj.scale.set(f.geom.scale, f.geom.scale, f.geom.scale);

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
        parent.scale.set(1, 1, _this.sceneData.zExaggeration);
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

Q3D.LineLayer.prototype.loadJSONObject = function (jsonObject, scene) {
  Q3D.VectorLayer.prototype.loadJSONObject.call(this, jsonObject, scene);
};

Q3D.LineLayer.prototype.build = function (features) {
  var createObject,
      objType = this.properties.objType,
      materials = this.materials,
      sceneData = this.sceneData;

  if (objType == this._lastObjType && this._createObject !== undefined) {
    createObject = this._createObject;
  }
  else if (objType == "Line") {
    createObject = function (f, line) {
      var pt, vertices = [];
      for (var i = 0, l = line.length; i < l; i++) {
        pt = line[i];
        vertices.push(pt[0], pt[1], pt[2]);
      }
      var geom = new THREE.BufferGeometry();
      geom.addAttribute("position", new THREE.Float32BufferAttribute(vertices, 3));

      var obj = new THREE.Line(geom, materials.mtl(f.mtl));
      if (obj.material instanceof THREE.LineDashedMaterial) obj.computeLineDistances();
      return obj;
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

    var mesh, pt0 = new THREE.Vector3(), pt1 = new THREE.Vector3(), sub = new THREE.Vector3(), axis = Q3D.uv.j;

    createObject = function (f, line) {
      var group = new Q3D.Group();

      pt0.set(line[0][0], line[0][1], line[0][2]);
      for (var i = 1, l = line.length; i < l; i++) {
        pt1.set(line[i][0], line[i][1], line[i][2]);

        mesh = new THREE.Mesh(cylinGeom, materials.mtl(f.mtl));
        mesh.scale.set(f.geom.r, pt0.distanceTo(pt1), f.geom.r);
        mesh.position.set((pt0.x + pt1.x) / 2, (pt0.y + pt1.y) / 2, (pt0.z + pt1.z) / 2);
        mesh.quaternion.setFromUnitVectors(axis, sub.subVectors(pt1, pt0).normalize());
        group.add(mesh);

        if (jointGeom && i < l - 1) {
          mesh = new THREE.Mesh(jointGeom, materials.mtl(f.mtl));
          mesh.scale.set(f.geom.r, f.geom.r, f.geom.r);
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

    createObject = function (f, line) {
      var geometry = new THREE.Geometry(),
          group = new Q3D.Group();      // used in debug mode

      var geom, mesh, dist, quat, rx, rz, wh4, vb4, vf4;
      var pt0 = new THREE.Vector3(), pt1 = new THREE.Vector3(), sub = new THREE.Vector3(),
          pt = new THREE.Vector3(), ptM = new THREE.Vector3(), scale1 = new THREE.Vector3(1, 1, 1),
          matrix = new THREE.Matrix4(), quat = new THREE.Quaternion();

      pt0.set(line[0][0], line[0][1], line[0][2]);
      for (var i = 1, l = line.length; i < l; i++) {
        pt1.set(line[i][0], line[i][1], line[i][2]);
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
      if (Q3D.Config.exportMode) geometry = new THREE.BufferGeometry().fromGeometry(geometry);
      return new THREE.Mesh(geometry, materials.mtl(f.mtl));
    };
  }
  else if (objType == "Wall") {
    var z0 = sceneData.zShift * sceneData.zScale;

    createObject = function (f, line) {
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

  // each feature in this layer
  var f, i, l, obj;
  for (var fidx = 0, flen = features.length; fidx < flen; fidx++) {
    f = features[fidx];
    f.objIndices = [];

    for (i = 0, l = f.geom.lines.length; i < l; i++) {
      obj = createObject(f, f.geom.lines[i]);
      obj.userData.properties = f.prop;

      f.objIndices.push(this.addObject(obj));
    }
  }

  this._lastObjType = objType;
  this._createObject = createObject;
};

Q3D.LineLayer.prototype.buildLabels = function (features) {
  // Line layer doesn't support label
  // Q3D.VectorLayer.prototype.buildLabels.call(this, features);
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
  var createObject,
      materials = this.materials,
      sceneData = this.sceneData;

  if (this.properties.objType == this._lastObjType && this._createObject !== undefined) {
    createObject = this._createObject;
  }
  else if (this.properties.objType == "Polygon") {
    createObject = function (f) {
      var geom = new THREE.BufferGeometry();
      geom.addAttribute("position", new THREE.Float32BufferAttribute(f.geom.triangles.v, 3));
      geom.setIndex(f.geom.triangles.f);
      if (!Q3D.Config.exportMode) {
        geom = new THREE.Geometry().fromBufferGeometry(geom); // Flat shading doesn't work with combination of
                                                              // BufferGeometry and Lambert/Toon material.
      }
      return new THREE.Mesh(geom, materials.mtl(f.mtl));
    };
  }
  else if (this.properties.objType == "Extruded") {
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
        var edge, bnd, p, v,
            h = f.geom.h,
            mtl = materials.mtl(f.mtl.edge);

        for (i = 0, l = polygon.length; i < l; i++) {
          bnd = polygon[i];

          v = [];
          for (j = 0, m = bnd.length; j < m; j++) {
            v.push(bnd[j][0], bnd[j][1], 0);
          }

          geom = new THREE.BufferGeometry();
          geom.addAttribute("position", new THREE.Float32BufferAttribute(v, 3));

          edge = new THREE.Line(geom, mtl);
          mesh.add(edge);

          edge = new THREE.Line(geom, mtl);
          edge.position.z = h;
          mesh.add(edge);

          // vertical lines
          for (j = 0, m = bnd.length - 1; j < m; j++) {
            v = [bnd[j][0], bnd[j][1], 0,
                 bnd[j][0], bnd[j][1], h];

            geom = new THREE.BufferGeometry();
            geom.addAttribute("position", new THREE.Float32BufferAttribute(v, 3));

            edge = new THREE.Line(geom, mtl);
            mesh.add(edge);
          }
        }
      }
      return mesh;
    };

    createObject = function (f) {
      if (f.geom.polygons.length == 1) return createSubObject(f, f.geom.polygons[0], f.geom.centroids[0][2]);

      var group = new THREE.Group();
      for (var i = 0, l = f.geom.polygons.length; i < l; i++) {
        group.add(createSubObject(f, f.geom.polygons[i], f.geom.centroids[i][2]));
      }
      return group;
    };
  }
  else if (this.properties.objType == "Overlay") {
    createObject = function (f) {

      var vertices = f.geom.triangles.v,
          base_width = sceneData.width,
          base_height = sceneData.height,
          uvs = [];

      for (var i = 0, l = vertices.length; i < l; i += 3) {
        uvs.push(vertices[i] / base_width + 0.5, vertices[i + 1] / base_height + 0.5);
      }

      var geom = new THREE.BufferGeometry();
      geom.setIndex(f.geom.triangles.f);
      geom.addAttribute("position", new THREE.Float32BufferAttribute(vertices, 3));
      geom.addAttribute("uv", new THREE.Float32BufferAttribute(uvs, 2));
      geom.computeVertexNormals();

      var mesh = new THREE.Mesh(geom, materials.mtl(f.mtl.face));

      // borders
      if (f.geom.brdr !== undefined) {
        var bnds, i, l, j, m;
        for (i = 0, l = f.geom.brdr.length; i < l; i++) {
          bnds = f.geom.brdr[i];
          for (j = 0, m = bnds.length; j < m; j++) {
            geom = new THREE.BufferGeometry(),
            geom.addAttribute("position", new THREE.Float32BufferAttribute(bnds[j], 3));

            mesh.add(new THREE.Line(geom, materials.mtl(f.mtl.brdr)));
          }
        }
      }
      return mesh;
    };
  }

  // each feature in this layer
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

  loadJSONObject: function (jsonObject, callback) {
    this.load(jsonObject.url, callback);
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

    if (this.cache[url] !== undefined) {
      model = this.cache[url];
    }
    else {
      model = new Q3D.Model();
      model.load(url, callback);
      this.cache[url] = model;
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

  if (buffer_geom || Q3D.Config.exportMode) {
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
