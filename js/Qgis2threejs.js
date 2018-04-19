"use strict";

// Qgis2threejs.js
// (C) 2014 Minoru Akagi | MIT License
// https://github.com/minorua/Qgis2threejs

var Q3D = {VERSION: "2.0.1"};
Q3D.Options = {
  bgcolor: null,
  light: {
    directional: {
      azimuth: 220,   // note: default light azimuth of gdaldem hillshade is 315.
      altitude: 45    // altitude angle
    }
  },
  side: {color: 0xc7ac92, bottomZ: -1.5},
  frame: {color: 0, bottomZ: -1.5},
  label: {visible: true, connectorColor: 0xc0c0d0, autoSize: false, minFontSize: 10},
  qmarker: {r: 0.25, c: 0xffff00, o: 0.8},
  debugMode: false,
  exportMode: false,
  jsonLoader: "JSONLoader"  // JSONLoader or ObjectLoader
};

Q3D.LayerType = {DEM: "dem", Point: "point", Line: "line", Polygon: "polygon"};
Q3D.MaterialType = {MeshLambert: 0, MeshPhong: 1, LineBasic: 2, Sprite: 3, Unknown: -1};
Q3D.uv = {i: new THREE.Vector3(1, 0, 0), j: new THREE.Vector3(0, 1, 0), k: new THREE.Vector3(0, 0, 1)};

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

      // TODO: [Light settings] load light settings and build lights
    }

    // create default lights if this scene has no lights
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

    /* TODO: [Point - Model] load models
    // load models
    if (project.models.length > 0) {
      project.models.forEach(function (model, index) {
        if (model.type == "COLLADA") {
          app.modelBuilders[index] = new Q3D.ModelBuilder.COLLADA(app.project, model);
        }
        else if (Q3D.Options.jsonLoader == "ObjectLoader") {
          app.modelBuilders[index] = new Q3D.ModelBuilder.JSONObject(app.project, model);
        }
        else {
          app.modelBuilders[index] = new Q3D.ModelBuilder.JSON(app.project, model);
        }
      });
    }
    */
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

Q3D.Scene.prototype.buildDefaultLights = function () {
  // ambient light
  this.lightGroup.add(new THREE.AmbientLight(0x999999));

  // directional lights
  var opt = Q3D.Options.light.directional, deg2rad = Math.PI / 180;
  var lambda = (90 - opt.azimuth) * deg2rad;
  var phi = opt.altitude * deg2rad;

  var x = Math.cos(phi) * Math.cos(lambda),
      y = Math.cos(phi) * Math.sin(lambda),
      z = Math.sin(phi);

  var light1 = new THREE.DirectionalLight(0xffffff, 0.5);
  light1.position.set(x, y, z);
  this.lightGroup.add(light1);

  // thin light from the opposite direction
  var light2 = new THREE.DirectionalLight(0xffffff, 0.1);
  light2.position.set(-x, -y, -z);
  this.lightGroup.add(light2);
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

// Rotate a point around an origin
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

  // rotate counter-clockwise
  var xd = x * c - y * s,
      yd = x * s + y * c;

  if (origin) {
    xd += origin.x;
    yd += origin.y;
  }
  return {x: xd, y: yd};
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

  var listeners = {};
  var dispatchEvent = function (event) {
    var ls = listeners[event.type] || [];
    for (var i = 0; i < ls.length; i++) {
      ls[i](event);
    }
  };

  app.addEventListener = function (type, listener) {
    listeners[type] = listeners[type] || [];
    listeners[type].push(listener);
  };

  app.init = function (container, isOrthoCamera) {
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

    if (container.clientWidth && container.clientHeight) {
      app.width = container.clientWidth;
      app.height = container.clientHeight;
      app._fullWindow = false;
    } else {
      app.width = window.innerWidth;
      app.height = window.innerHeight;
      app._fullWindow = true;
    }

    // WebGLRenderer
    var bgcolor = Q3D.Options.bgcolor;
    app.renderer = new THREE.WebGLRenderer({alpha: true, antialias: true});
    app.renderer.setSize(app.width, app.height);
    app.renderer.setClearColor(bgcolor || 0, (bgcolor === null) ? 0 : 1);
    app.container.appendChild(app.renderer.domElement);

    // camera
    app.buildCamera(isOrthoCamera);

    // scene
    app.scene = new Q3D.Scene();
    app.scene.addEventListener("renderRequest", function (event) {
      app.render();
    });

    // restore view (camera position and its target) from URL parameters
    var vars = app.urlParams;
    if (vars.cx !== undefined) app.camera.position.set(parseFloat(vars.cx), parseFloat(vars.cy), parseFloat(vars.cz));
    if (vars.ux !== undefined) app.camera.up.set(parseFloat(vars.ux), parseFloat(vars.uy), parseFloat(vars.uz));
    if (vars.tx !== undefined) app.camera.lookAt(parseFloat(vars.tx), parseFloat(vars.ty), parseFloat(vars.tz));

    // orbit controls
    var controls = new THREE.OrbitControls(app.camera, app.renderer.domElement);
    controls.enableKeys = false;

    var offset = new THREE.Vector3();
    var spherical = new THREE.Spherical();

    // orbit controls - custom functions
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

    app.controls = controls;
    controls.update();

    app.labelVisibility = Q3D.Options.label.visible;

    // root element of labels
    app.scene.labelRootElement = document.getElementById("labels");
    app.scene.labelRootElement.style.display = (app.labelVisibility) ? "block" : "none";

    // create a marker for queried point
    var opt = Q3D.Options.qmarker;
    app.queryMarker = new THREE.Mesh(new THREE.SphereBufferGeometry(opt.r),
                                      new THREE.MeshLambertMaterial({color: opt.c, opacity: opt.o, transparent: (opt.o < 1)}));
    app.queryMarker.visible = false;
    app.scene.add(app.queryMarker);

    app.highlightMaterial = new THREE.MeshLambertMaterial({emissive: 0x999900, transparent: true, opacity: 0.5});
    if (!Q3D.isIE) app.highlightMaterial.side = THREE.DoubleSide;    // Shader compilation error occurs with double sided material on IE11

    app.selectedObject = null;
    app.highlightObject = null;

    app.modelBuilders = [];
    app._wireframeMode = false;

    // add event listeners
    window.addEventListener("keydown", app.eventListener.keydown);
    window.addEventListener("resize", app.eventListener.resize);

    app.renderer.domElement.addEventListener("mousedown", app.eventListener.mousedown);
    app.renderer.domElement.addEventListener("mouseup", app.eventListener.mouseup);

    controls.addEventListener("change", function (event) {
      app.render();
    });

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

  app.loadJSONObject = function (jsonObject) {
    app.scene.loadJSONObject(jsonObject);
  };

  var reqCounter = 0;
  app.loadFile = function (url, type, callback) {
    var onError = function (e) {
      if (location.protocol == "file:") {
        app.popup.show("This browser doesn't allow loading local files via Ajax. See <a href='https://github.com/minorua/Qgis2threejs/wiki/BrowserSupport'>plugin wiki</a> for details.", "Error", true);
      }
    };
    reqCounter++;
    try {
      var xhr = new XMLHttpRequest();
      xhr.open("GET", url, true);
      xhr.responseType = type;
      xhr.onload = function () {
        reqCounter--;
        if (callback) callback(this.response);
        if (reqCounter == 0) dispatchEvent({type: "sceneLoaded"});
      };
      xhr.onerror = onError;    // for Chrome
      xhr.send(null);
    }
    catch (e) {      // for IE
      onError(e);
    }
  };

  app.loadJSONFile = function (url, callback) {
    app.loadFile(url, "json", function (obj) {
      app.loadJSONObject(obj);
      if (callback) callback(obj);
    });
  };

  app.loadTextureFile = function (url, callback) {
    reqCounter++;
    return new THREE.TextureLoader().load(url, function () {
      reqCounter--;
      if (callback) callback();
      if (reqCounter == 0) dispatchEvent({type: "sceneLoaded"});
    });
  };

  app.mouseDownPoint = new THREE.Vector2();
  app.mouseUpPoint = new THREE.Vector2();

  app.eventListener = {

    keydown: function (e) {
      var controls = app.controls, keyPressed = e.which;
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
      } else if (e.shiftKey) {
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
      } else if (e.ctrlKey) {
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
      } else {
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
            app.closePopup();
            return;
          case 73:  // I
            app.showInfo();
            return;
          case 76:  // L
            app.setLabelVisibility(!app.labelVisibility);
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
      if (app._fullWindow) app.setCanvasSize(window.innerWidth, window.innerHeight);
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

  app.buildCamera = function (isOrtho) {
    if (isOrtho) {
      app.camera = new THREE.OrthographicCamera(-app.width / 10, app.width / 10, app.height / 10, -app.height / 10, 0.1, 1000);
    }
    else {
      app.camera = new THREE.PerspectiveCamera(45, app.width / app.height, 0.1, 1000);
    }
    app.camera.position.set(0, 100, 100);
  };

  app.currentViewUrl = function () {
    var c = app.camera.position, t = app.controls.target, u = app.camera.up;
    var hash = "#cx=" + c.x + "&cy=" + c.y + "&cz=" + c.z;
    if (t.x || t.y || t.z) hash += "&tx=" + t.x + "&ty=" + t.y + "&tz=" + t.z;
    if (u.x || u.y || u.z != 1) hash += "&ux=" + u.x + "&uy=" + u.y + "&uz=" + u.z;
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
    app.updateLabelPosition();
  };

  // update label position
  app.updateLabelPosition = function () {
    var rootGroup = app.scene.labelConnectorGroup;
    if (!app.labelVisibility || rootGroup.children.length == 0) return;

    var camera = app.camera,
        camera_pos = camera.position,
        c2t = app.controls.target.clone().sub(camera_pos),
        c2l = new THREE.Vector3(),
        pt = new THREE.Vector3();

    // make list of [connector object, pt, distance to camera]
    var obj_dist = [], connGroup, conn, pt0;
    for (var i = 0, l = rootGroup.children.length; i < l; i++) {
      connGroup = rootGroup.children[i];
      if (!connGroup.visible) continue;
      for (var k = 0, m = connGroup.children.length; k < m; k++) {
        conn = connGroup.children[k];
        pt0 = conn.geometry.vertices[0];
        pt.set(pt0.x, pt0.z, -pt0.y);

        if (c2l.subVectors(pt, camera_pos).dot(c2t) > 0)      // label is in front
          obj_dist.push([conn, pt0, camera_pos.distanceTo(pt)]);
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
        autosize = Q3D.Options.label.autoSize,
        minFontSize = Q3D.Options.label.minFontSize;

    var label, dist, x, y, e, fontSize;
    for (var i = 0, l = obj_dist.length; i < l; i++) {
      label = obj_dist[i][0];
      pt0 = obj_dist[i][1];
      dist = obj_dist[i][2];

      // calculate label position
      pt.set(pt0.x, pt0.z, -pt0.y).project(camera);
      x = (pt.x * widthHalf) + widthHalf;
      y = -(pt.y * heightHalf) + heightHalf;

      // set label position
      e = label.userData.elem;
      e.style.display = "block";
      e.style.left = (x - (e.offsetWidth / 2)) + "px";
      e.style.top = (y - (e.offsetHeight / 2)) + "px";
      e.style.zIndex = i + 1;

      // set font size
      if (autosize) {
        if (dist < 10) dist = 10;
        fontSize = Math.max(Math.round(1000 / dist), minFontSize);
        e.style.fontSize = fontSize + "px";
      }
    }
  };

  app.setLabelVisibility = function (visible) {
    app.labelVisibility = visible;
    app.scene.labelRootElement.style.display = (visible) ? "block" : "none";
    app.scene.labelConnectorGroup.visible = visible;
    app.render();
  };

  app.setRotateAnimationMode = function (rotate) {
    if (rotate) {
      app.controls.autoRotate = true;
      app.startAnimation();
    }
    else {
      app.controls.autoRotate = false;
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

  app.help = function () {
    var lines = (Q3D.Controls === undefined) ? [] : Q3D.Controls.keyList;
    if (lines.indexOf("* Keys") == -1) lines.push("* Keys");
    lines = lines.concat([
      "I : Show Information About Page",
      "L : Toggle Label Visibility",
      "R : Start / Stop Rotate Animation",
      "W : Wireframe Mode",
      "Shift + R : Reset View",
      "Shift + S : Save Image"
    ]);
    var html = '<table>';
    lines.forEach(function (line) {
      if (line.trim() == "") return;

      if (line[0] == "*") {
        html += '<tr><td colspan="2" class="star">' + line.substr(1).trim() + "</td></tr>";
      }
      else if (line.indexOf(":") == -1) {
        html += '<tr><td colspan="2">' + line.trim() + "</td></tr>";
      }
      else {
        var p = line.split(":");
        html += "<tr><td>" + p[0].trim() + "</td><td>" + p[1].trim() + "</td></tr>";
      }
    });
    html += "</table>";
    return html;
  };

  app.popup = {

    modal: false,

    // show box
    // obj: html or element
    show: function (obj, title, modal) {

      if (modal) app.pause();
      else if (this.modal) app.resume();

      this.modal = Boolean(modal);

      var content = Q3D.$("popupcontent");
      if (obj === undefined) {
        // show page info
        content.style.display = "none";
        Q3D.$("pageinfo").style.display = "block";
      }
      else {
        Q3D.$("pageinfo").style.display = "none";
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
    },

    hide: function () {
      Q3D.$("popup").style.display = "none";
      if (this.modal) app.resume();
    }

  };

  app.showInfo = function () {
    Q3D.$("urlbox").value = app.currentViewUrl();
    Q3D.$("usage").innerHTML = app.help();
    app.popup.show();
  };

  app.showQueryResult = function (point, obj) {
    var layer = app.scene.mapLayers[obj.userData.layerId], r = [];
    if (layer) {
      // layer name
      r.push('<table class="layer">');
      r.push("<caption>Layer name</caption>");
      r.push("<tr><td>" + layer.properties.name + "</td></tr>");
      r.push("</table>");
    }

    // clicked coordinates
    var pt = app.scene.toMapCoordinates(point.x, point.y, point.z);
    r.push('<table class="coords">');
    r.push("<caption>Clicked coordinates</caption>");
    r.push("<tr><td>");

    if (typeof proj4 === "undefined") r.push([pt.x.toFixed(2), pt.y.toFixed(2), pt.z.toFixed(2)].join(", "));
    else {
      var lonLat = proj4(app.scene.userData.proj).inverse([pt.x, pt.y]);
      r.push(Q3D.Utils.convertToDMS(lonLat[1], lonLat[0]) + ", Elev. " + pt.z.toFixed(2));
    }

    r.push("</td></tr></table>");

    if (layer.properties.propertyNames !== undefined) {
      // attributes
      r.push('<table class="attrs">');
      r.push("<caption>Attributes</caption>");
      for (var i = 0, l = layer.properties.propertyNames.length; i < l; i++) {
        r.push("<tr><td>" + layer.properties.propertyNames[i] + "</td><td>" + obj.userData.properties[i] + "</td></tr>");
      }
      r.push("</table>");
    }
    app.popup.show(r.join(""));
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
    app.queryMarker.visible = false;
    app.highlightFeature(null);
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
      app.queryMarker.visible = true;
      app.queryMarker.updateMatrixWorld();

      // get layerId of clicked object
      var layerId, object = obj.object;
      while (object) {
        layerId = object.userData.layerId;
        if (layerId !== undefined) break;
        object = object.parent;
      }

      app.highlightFeature(object);
      app.showQueryResult(pt, object);

      app.render();

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
    if (app.labelVisibility) {
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
          camera_pos = camera.position,
          c2t = app.controls.target.clone().sub(camera_pos),
          c2l = new THREE.Vector3(),
          v = new THREE.Vector3();

      // make a list of [label index, distance to camera]
      var idx_dist = [];
      for (var i = 0, l = labels.length; i < l; i++) {
        idx_dist.push([i, camera_pos.distanceTo(labels[i].pt)]);
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
        if (c2l.subVectors(label.pt, camera_pos).dot(c2t) > 0) {    // label is in front
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
    var bgcolor = Q3D.Options.bgcolor;
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
};

Q3D.Material.prototype = {

  constructor: Q3D.Material,

  // callback is called when texture is loaded
  loadJSONObject: function (jsonObject, callback) {
    this.origProp = jsonObject;

    var m = jsonObject, opt = {};

    if (m.ds && !Q3D.isIE) opt.side = THREE.DoubleSide;

    if (m.flat) opt.shading = THREE.FlatShading;

    // texture
    if (m.image !== undefined) {
      var image = m.image;
      if (image.url !== undefined) {
        opt.map = Q3D.application.loadTextureFile(image.url, callback);
      }
      else if (image.object !== undefined) {    // WebKit Bridge
        opt.map = new THREE.Texture(image.object.toImageData());
        opt.map.needsUpdate = true;
        callback();
      }
      else {    // base64
        var img = new Image();
        img.onload = function () {
          opt.map.needsUpdate = true;
          callback();
        };
        img.src = image.base64;
        opt.map = new THREE.Texture(img);
      }
    }

    if (m.o !== undefined && m.o < 1) {
      opt.opacity = m.o;
      opt.transparent = true;
    }

    if (m.t) opt.transparent = true;

    if (m.w) opt.wireframe = true;

    if (m.type == Q3D.MaterialType.MeshLambert) {
      if (m.c !== undefined) opt.color = m.c;
      this.mtl = new THREE.MeshLambertMaterial(opt);
    }
    else if (m.type == Q3D.MaterialType.MeshPhong) {
      if (m.c !== undefined) opt.color = m.c;
      this.mtl = new THREE.MeshPhongMaterial(opt);
    }
    else if (m.type == Q3D.MaterialType.LineBasic) {
      opt.color = m.c;
      this.mtl = new THREE.LineBasicMaterial(opt);
    }
    else {
      opt.color = 0xffffff;
      this.mtl = new THREE.SpriteMaterial(opt);
    }
  },

  set: function (material) {
    this.mtl = material;
    this.origProp = {};
  },

  type: function () {
    if (this.mtl instanceof THREE.MeshLambertMaterial) return Q3D.MaterialType.MeshLambert;
    if (this.mtl instanceof THREE.MeshPhongMaterial) return Q3D.MaterialType.MeshPhong;
    if (this.mtl instanceof THREE.LineBasicMaterial) return Q3D.MaterialType.LineBasic;
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
    mtl.loadJSONObject(jsonObject[i], callback);    // callback is called when a texture is loaded
    this.add(mtl);
  }
  iterated = true;

  // TODO: layer opacity is the average opacity of materials
  //this.opacity = sum_opacity / this.materials.length;
};

Q3D.Materials.prototype.dispose = function () {
  for (var i = 0, l = this.materials.length; i < l; i++) {
    this.materials[i].dispose();
  }
  this.materials = [];
};

// opacity
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
      if (callback) callback(_this);
    });
    layer.materials.add(this.material);

    // create geometry and mesh
    var geom = new THREE.PlaneBufferGeometry(obj.width, obj.height, grid.width - 1, grid.height - 1),
        mesh = new THREE.Mesh(geom, this.material.mtl);

    if (obj.translate !== undefined) mesh.position.set(obj.translate[0], obj.translate[1], obj.translate[2]);

    var buildGeometry = function (grid_values) {
      var vertices = geom.attributes.position.array;
      for (var i = 0, j = 0, l = vertices.length; i < l; i++, j += 3) {
        vertices[j + 2] = grid_values[i];
      }
      geom.attributes.position.needsUpdate = true;

      // Calculate normals
      if (layer.properties.shading) {
        geom.computeFaceNormals();
        geom.computeVertexNormals();
      }

      // build sides, bottom and frame
      if (obj.sides) {
        _this.buildSides(layer, grid, obj.width, obj.height, mesh, Q3D.Options.side.bottomZ);
        layer.sideVisible = true;
      }
      if (obj.frame) {
        _this.buildFrame(layer, grid, obj.width, obj.height, mesh, Q3D.Options.frame.bottomZ);
        layer.sideVisible = true;
      }

      if (callback) callback(_this);    // call callback to request rendering
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

  buildSides: function (layer, grid, planeWidth, planeHeight, parent, z0) {
    var matProp = this.material.origProp,
        opacity = (matProp.o !== undefined) ? matProp.o : 1;
    var material = new THREE.MeshLambertMaterial({color: Q3D.Options.side.color,
                                                  opacity: opacity,
                                                  transparent: (opacity < 1)});
    layer.materials.add(material);

    var band_width = -z0 * 2, grid_values = grid.array, w = grid.width, h = grid.height, HALF_PI = Math.PI / 2;
    var i, mesh;

    // front and back
    var geom_fr = new THREE.PlaneBufferGeometry(planeWidth, band_width, w - 1, 1),
        geom_ba = new THREE.PlaneBufferGeometry(planeWidth, band_width, w - 1, 1);

    var k = w * (h - 1);
    var vertices_fr = geom_fr.attributes.position.array,
        vertices_ba = geom_ba.attributes.position.array;

    for (i = 0; i < w; i++) {
      vertices_fr[i * 3 + 1] = grid_values[k + i];
      vertices_ba[i * 3 + 1] = grid_values[w - 1 - i];
    }
    mesh = new THREE.Mesh(geom_fr, material);
    mesh.rotation.x = HALF_PI;
    mesh.position.y = -planeHeight / 2;
    mesh.name = "side";
    parent.add(mesh);

    mesh = new THREE.Mesh(geom_ba, material);
    mesh.rotation.x = HALF_PI;
    mesh.rotation.y = Math.PI;
    mesh.position.y = planeHeight / 2;
    mesh.name = "side";
    parent.add(mesh);

    // left and right
    var geom_le = new THREE.PlaneBufferGeometry(band_width, planeHeight, 1, h - 1),
        geom_ri = new THREE.PlaneBufferGeometry(band_width, planeHeight, 1, h - 1);

    var vertices_le = geom_le.attributes.position.array,
        vertices_ri = geom_ri.attributes.position.array;

    for (i = 0; i < h; i++) {
      vertices_le[(i * 2 + 1) * 3] = grid_values[w * i];
      vertices_ri[i * 2 * 3] = -grid_values[w * (i + 1) - 1];
    }
    mesh = new THREE.Mesh(geom_le, material);
    mesh.rotation.y = -HALF_PI;
    mesh.position.x = -planeWidth / 2;
    mesh.name = "side";
    parent.add(mesh);

    mesh = new THREE.Mesh(geom_ri, material);
    mesh.rotation.y = HALF_PI;
    mesh.position.x = planeWidth / 2;
    mesh.name = "side";
    parent.add(mesh);

    // bottom
    if (Q3D.Options.exportMode) {
      var geom = new THREE.PlaneBufferGeometry(planeWidth, planeHeight, w - 1, h - 1);
    }
    else {
      var geom = new THREE.PlaneBufferGeometry(planeWidth, planeHeight, 1, 1);
    }
    mesh = new THREE.Mesh(geom, material);
    mesh.rotation.x = Math.PI;
    mesh.position.z = z0;
    mesh.name = "bottom";
    parent.add(mesh);

    parent.updateMatrixWorld();
  },

  buildFrame: function (layer, grid, planeWidth, planeHeight, parent, z0) {
    var matProp = this.material.origProp,
        opacity = (matProp.o !== undefined) ? matProp.o : 1;
    var material = new THREE.LineBasicMaterial({color: Q3D.Options.frame.color,
                                                opacity: opacity,
                                                transparent: (opacity < 1)});
    layer.materials.add(material);

    // horizontal rectangle at bottom
    var hw = planeWidth / 2, hh = planeHeight / 2;
    var geom = new THREE.Geometry();
    geom.vertices.push(new THREE.Vector3(-hw, -hh, z0),
                       new THREE.Vector3(hw, -hh, z0),
                       new THREE.Vector3(hw, hh, z0),
                       new THREE.Vector3(-hw, hh, z0),
                       new THREE.Vector3(-hw, -hh, z0));

    var obj = new THREE.Line(geom, material);
    obj.name = "frame";
    parent.add(obj);

    // vertical lines at corners
    var pts = [[-hw, -hh, grid.array[grid.array.length - grid.width]],
               [hw, -hh, grid.array[grid.array.length - 1]],
               [hw, hh, grid.array[grid.width - 1]],
               [-hw, hh, grid.array[0]]];
    pts.forEach(function (pt) {
      var geom = new THREE.Geometry();
      geom.vertices.push(new THREE.Vector3(pt[0], pt[1], pt[2]),
                         new THREE.Vector3(pt[0], pt[1], z0));

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
    var _this = this,
        grid = obj.grid;
    this.data = obj;

    // load material
    this.material = new Q3D.Material();
    this.material.loadJSONObject(obj.material, function () {
      if (callback) callback(_this);
    });
    layer.materials.add(this.material);

    var mesh = new THREE.Mesh(new THREE.Geometry(), this.material.mtl);
    if (obj.translate !== undefined) mesh.position.set(obj.translate[0], obj.translate[1], obj.translate[2]);

    var buildGeometry = function (grid_values) {
      mesh.geometry = Q3D.Utils.createOverlayGeometry(obj.clip.triangles, obj.clip.split_polygons, layer.getZ.bind(layer));

      // set UVs
      Q3D.Utils.setGeometryUVs(mesh.geometry, layer.sceneData.width, layer.sceneData.height);

      if (obj.sides) {
        _this.buildSides(layer, mesh, Q3D.Options.side.bottomZ);
        layer.sideVisible = true;
      }

      if (callback) callback(_this);    // call callback to request rendering
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

  buildSides: function (layer, parent, z0) {
    var matProp = this.material.origProp,
        opacity = (matProp.o !== undefined) ? matProp.o : 1;
    var material = new THREE.MeshLambertMaterial({color: Q3D.Options.side.color,
                                                  opacity: opacity,
                                                  transparent: (opacity < 1)});
    layer.materials.add(material);

    var polygons = this.data.clip.polygons,
        zFunc = layer.getZ.bind(layer),
        bzFunc = function (x, y) { return z0; };

    // make back-side material for bottom
    var mat_back = material.clone();
    mat_back.side = THREE.BackSide;
    layer.materials.add(mat_back);

    var geom, mesh, shape, vertices;
    for (var i = 0, l = polygons.length; i < l; i++) {
      var polygon = polygons[i];

      // sides
      for (var j = 0, m = polygon.length; j < m; j++) {
        vertices = layer.segmentizeLineString(polygon[j], zFunc);
        geom = Q3D.Utils.createWallGeometry(vertices, bzFunc);
        mesh = new THREE.Mesh(geom, material);
        mesh.name = "side";
        parent.add(mesh);
      }

      // bottom
      shape = new THREE.Shape(Q3D.Utils.arrayToVec2Array(polygon[0]));
      for (var j = 1, m = polygon.length; j < m; j++) {
        shape.holes.push(new THREE.Path(Q3D.Utils.arrayToVec2Array(polygon[j])));
      }
      geom = new THREE.ShapeBufferGeometry(shape);
      mesh = new THREE.Mesh(geom, mat_back);
      mesh.position.z = z0;
      mesh.name = "bottom";
      parent.add(mesh);
    }
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
Q3D.MapLayer
*/
Q3D.MapLayer = function () {
  this.opacity = 1;
  this.visible = true;
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
  // properties
  if (jsonObject.properties !== undefined) {
    this.properties = jsonObject.properties;
    this.setVisible((jsonObject.properties.visible !== false) ? true : false);
  }

  if (jsonObject.data !== undefined) {
    this.removeAllObjects();

    // materials
    if (jsonObject.data.materials !== undefined) {
      this.materials.loadJSONObject(jsonObject.data.materials);
    }
  }

  this.sceneData = scene.userData;
};

Q3D.MapLayer.prototype.setOpacity = function (opacity) {
  this.materials.setOpacity(opacity);
  this.opacity = opacity;
  this.requestRender();
};

Q3D.MapLayer.prototype.setVisible = function (visible) {
  // if (this.visible === visible) return;
  this.visible = visible;
  this.objectGroup.visible = visible;
  this.requestRender();
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
  if (jsonObject.type == "layer") {
    Q3D.MapLayer.prototype.loadJSONObject.call(this, jsonObject, scene);
    if (jsonObject.data !== undefined) this.build(jsonObject.data);
  }
  else if (jsonObject.type == "block") {
    var index = jsonObject.block;
    this.blocks[index] = (jsonObject.clip === undefined) ? (new Q3D.DEMBlock()) : (new Q3D.ClippedDEMBlock());

    var mesh = this.blocks[index].loadJSONObject(jsonObject, this, this.requestRender.bind(this));
    this.addObject(mesh);
  }
};

Q3D.DEMLayer.prototype.build = function (blocks) {
  // build blocks
  blocks.forEach(function (block) {
    var b = (block.clip === undefined) ? (new Q3D.DEMBlock()) : (new Q3D.ClippedDEMBlock()),
        mesh = b.loadJSONObject(block, this, this.requestRender.bind(this));
    this.addObject(mesh);
    this.blocks.push(b);
  }, this);
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

Q3D.DEMLayer.prototype.setVisible = function (visible) {
  Q3D.MapLayer.prototype.setVisible.call(this, visible);
  // if (visible && this.sideVisible === false) this.setSideVisibility(false);
};

Q3D.DEMLayer.prototype.setSideVisibility = function (visible) {
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

  var line_mat = new THREE.LineBasicMaterial({color: Q3D.Options.label.connectorColor});
  var f, text, pts, pt, pt0, pt1;

  for (var i = 0, l = features.length; i < l; i++) {
    f = features[i];
    text = f.prop[pIndex];
    if (text === null || text === "") continue;

    pts = getPointsFunc(f);
    for (var j = 0, m = pts.length; j < m; j++) {
      // create div element for label
      var e = document.createElement("div");
      e.appendChild(document.createTextNode(text));
      e.className = "label";
      this.labelParentElement.appendChild(e);

      pt = pts[j];
      pt0 = new THREE.Vector3(pt[0], pt[1], pt[2]);                                      // bottom
      pt1 = new THREE.Vector3(pt[0], pt[1], (isRelative) ? pt[2] + f.lh : z0 + f.lh);    // top

      // create connector
      var geom = new THREE.Geometry();
      geom.vertices.push(pt1, pt0);
      var conn = new THREE.Line(geom, line_mat);
      conn.userData.layerId = this.id;
      //conn.userData.featureId = i;
      conn.userData.elem = e;
      this.labelConnectorGroup.add(conn);
    }
  }
};

Q3D.VectorLayer.prototype.loadJSONObject = function (jsonObject, scene) {
  if (jsonObject.type == "layer") {
    Q3D.MapLayer.prototype.loadJSONObject.call(this, jsonObject, scene);
    if (jsonObject.data !== undefined) {
      this.clearLabels();

      // build labels
      if (this.properties.label !== undefined) {
        // create a label connector group
        if (this.labelConnectorGroup === undefined) {
          this.labelConnectorGroup = new Q3D.Group();
          this.labelConnectorGroup.userData.layerId = this.id;
          scene.labelConnectorGroup.add(this.labelConnectorGroup);
        }

        // create a label parent element
        if (this.labelParentElement === undefined) {
          this.labelParentElement = document.createElement("div");
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

Q3D.VectorLayer.prototype.setVisible = function (visible) {
  if (this.labelParentElement) this.labelParentElement.style.display = (visible) ? "block" : "none";
  if (this.labelConnectorGroup) this.labelConnectorGroup.visible = visible;
  Q3D.MapLayer.prototype.setVisible.call(this, visible);
};


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
};

Q3D.PointLayer.prototype.build = function (features) {
  var objType = this.properties.objType;
  if (objType == "Icon") { this.buildIcons(features); return; }
  if (objType == "JSON model" || objType == "COLLADA model") { this.buildModels(features); return; }

  var deg2rad = Math.PI / 180, rx = 90 * deg2rad;
  var setSR, unitGeom;

  if (objType == "Sphere") {
    setSR = function (mesh, geom) {
      mesh.scale.set(geom.r, geom.r, geom.r);
    };
    unitGeom = new THREE.SphereBufferGeometry(1, 32, 32);
  }
  else if (objType == "Box") {
    setSR = function (mesh, geom) {
      mesh.scale.set(geom.w, geom.h, geom.d);
      mesh.rotation.x = rx;
    };
    unitGeom = new THREE.BoxBufferGeometry(1, 1, 1);
  }
  else if (objType == "Disk") {
    var xAxis = Q3D.uv.i, zAxis = Q3D.uv.k;
    var sz = (this.ns === undefined || this.ns == false) ? this.sceneData.zExaggeration : 1;
    setSR = function (mesh, geom) {
      mesh.scale.set(geom.r, 1, geom.r * sz);
      mesh.rotateOnWorldAxis(xAxis, (90 - geom.d) * deg2rad);
      mesh.rotateOnWorldAxis(zAxis, -geom.dd * deg2rad);
    };
    unitGeom = new THREE.CylinderBufferGeometry(1, 1, 0.0001, 32);
  }
  else {  // Cylinder or Cone
    setSR = function (mesh, geom) {
      mesh.scale.set(geom.r, geom.h, geom.r);
      mesh.rotation.x = rx;
    };
    unitGeom = (objType == "Cylinder") ? new THREE.CylinderBufferGeometry(1, 1, 1, 32) : new THREE.CylinderBufferGeometry(0, 1, 1, 32);
  }

  // iteration for features
  var materials = this.materials;
  var f, geom, z_addend, i, l, mesh, pt;
  for (var fidx = 0, flen = features.length; fidx < flen; fidx++) {
    f = features[fidx];
    geom = f.geom;
    z_addend = (geom.h) ? geom.h / 2 : 0;
    for (i = 0, l = geom.pts.length; i < l; i++) {
      mesh = new THREE.Mesh(unitGeom, materials.mtl(f.mtl));
      setSR(mesh, geom);

      pt = geom.pts[i];
      mesh.position.set(pt[0], pt[1], pt[2] + z_addend);
      //mesh.userData.featureId = fid;
      mesh.userData.properties = f.prop;

      this.addObject(mesh);
    }
  }
};

// TODO: [Point - Icon]
Q3D.PointLayer.prototype.buildIcons = function (features) {
  // each feature in this layer
  for (var fidx = 0, flen = features.length; fidx < flen; fidx++) {
    var f = features[fidx],
        geom = f.geom;
    var mtl = this.materials.mtl(f.mtl);
    var image = scene.images[mtl.i];   // TODO: [Point - Icon]

    // base size is 64 x 64
    var scale = (geom.scale === undefined) ? 1 : geom.scale;
    var sx = image.width / 64 * scale,
        sy = image.height / 64 * scale;

    for (var i = 0, l = geom.pts.length; i < l; i++) {
      var pt = geom.pts[i];
      var sprite = new THREE.Sprite(mtl);
      sprite.position.set(pt[0], pt[1], pt[2]);
      sprite.scale.set(sx, sy, scale);
      //sprite.userData.featureId = fid;
      sprite.mesh.userData.properties = f.prop;

      this.addObject(sprite);
    }
  }
};

// TODO: [Point - Model]
Q3D.PointLayer.prototype.buildModels = function (features) {
  // each feature in this layer
  for (var fid = 0, flen = features.length; fid < flen; fid++) {
    var f = features[fid];
    Q3D.application.modelBuilders[f.model_index].addFeature(this.userData.id, fid);
  }
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
      var geom = new THREE.Geometry(), pt;
      for (var i = 0, l = line.length; i < l; i++) {
        pt = line[i];
        geom.vertices.push(new THREE.Vector3(pt[0], pt[1], pt[2]));
      }
      return new THREE.Line(geom, materials.mtl(f.mtl));
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
    var debugMode = Q3D.Options.debugMode;
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
        if (debugMode) {
          mesh = new THREE.Mesh(geom, materials.mtl(f.mtl));
          mesh.position.set(ptM.x, ptM.y, ptM.z);
          mesh.rotation.set(rx, 0, rz, "ZXY");
          group.add(mesh);
        }
        else {
          geom.applyMatrix(matrix);
          geometry.merge(geom);
        }

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
          if (debugMode) {
            geom.computeFaceNormals();
            group.add(new THREE.Mesh(geom));
          }
          else {
            geometry.merge(geom);
          }
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

      if (debugMode) return group;

      geometry.mergeVertices();
      geometry.computeFaceNormals();
      return new THREE.Mesh(geometry, materials.mtl(f.mtl));
    };
  }
  else if (objType == "Profile") {
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
  for (var fidx = 0, flen = features.length; fidx < flen; fidx++) {
    var f = features[fidx],
        geom = f.geom;
    for (var i = 0, l = geom.lines.length; i < l; i++) {
      var obj = createObject(f, geom.lines[i]);
      //obj.userData.featureId = fid;
      obj.userData.properties = f.prop;
      this.addObject(obj);
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
  else if (this.properties.objType == "Extruded") {
    var createSubObject = function (f, polygon, z) {
      var i, l, j, m;

      var shape = new THREE.Shape(Q3D.Utils.arrayToVec2Array(polygon[0]));
      for (i = 1, l = polygon.length; i < l; i++) {
        shape.holes.push(new THREE.Path(Q3D.Utils.arrayToVec2Array(polygon[i])));
      }

      // extruded geometry
      var geom = new THREE.ExtrudeBufferGeometry(shape, {bevelEnabled: false, amount: f.geom.h});
      var mesh = new THREE.Mesh(geom, materials.mtl(f.mtl.face));
      mesh.position.z = z;

      if (f.mtl.border !== undefined) {
        // border
        var border, pt, pts, zFunc = function (x, y) { return 0; };

        for (i = 0, l = polygon.length; i < l; i++) {
          pts = Q3D.Utils.arrayToVec3Array(polygon[i], zFunc);

          geom = new THREE.Geometry();
          geom.vertices = pts;

          border = new THREE.Line(geom, materials.mtl(f.mtl.border));
          mesh.add(border);

          border = new THREE.Line(geom, materials.mtl(f.mtl.border));
          border.position.z = f.geom.h;
          mesh.add(border);

          // vertical lines
          for (j = 0, m = geom.vertices.length - 1; j < m; j++) {
            pt = pts[j];

            geom = new THREE.Geometry();
            geom.vertices.push(pt, new THREE.Vector3(pt.x, pt.y, pt.z + f.geom.h));
            border = new THREE.Line(geom, materials.mtl(f.mtl.border));
            mesh.add(border);
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
  else {    // this.objType == "Overlay"
    var z0 = sceneData.zShift * sceneData.zScale;

    createObject = function (f) {
      var polygons, zFunc;

      if (f.geom.polygons) {
        polygons = f.geom.polygons;
        zFunc = function (x, y) { return z0 + f.geom.h; };
      }
      else {
        polygons = f.geom.split_polygons || [];   // with z values
      }

      var geom = Q3D.Utils.createOverlayGeometry(f.geom.triangles, polygons, zFunc);
      return new THREE.Mesh(geom, materials.mtl(f.mtl));

      //TODO: [Polygon - Overlay] border
    };
  }

  // each feature in this layer
  var f, obj;
  for (var i = 0, l = features.length; i < l; i++) {
    f = features[i];
    obj = createObject(f);
    obj.userData.properties = f.prop;
    this.addObject(obj);
  }

  this._lastObjType = this.properties.objType;
  this._createObject = createObject;
};

Q3D.PolygonLayer.prototype.buildLabels = function (features) {
  Q3D.VectorLayer.prototype.buildLabels.call(this, features, function (f) { return f.geom.centroids; });
};

Q3D.PolygonLayer.prototype.setBorderVisibility = function (visible) {
  if (this.properties.objType != "Overlay") return;

  this.objectGroup.children.forEach(function (parent) {
    for (var i = 0, l = parent.children.length; i < l; i++) {
      var obj = parent.children[i];
      if (obj instanceof THREE.Line) obj.visible = visible;
    }
  });
  this.borderVisible = visible;
};

Q3D.PolygonLayer.prototype.setSideVisibility = function (visible) {
  if (this.properties.objType != "Overlay") return;

  this.objectGroup.children.forEach(function (parent) {
    for (var i = 0, l = parent.children.length; i < l; i++) {
      var obj = parent.children[i];
      if (obj instanceof THREE.Mesh) obj.visible = visible;
    }
  });
  this.sideVisible = visible;
};


// TODO: [Point - Model]
// Q3D.ModelBuilder
Q3D.ModelBuilder = {};
Q3D.ModelBuilder._loaders = {};


/*
Q3D.ModelBuilder.Base
*/
Q3D.ModelBuilder.Base = function (scene, obj) {
  this.scene = scene;
  this.features = [];
  this._objects = {};

  this.loaded = false;
};

Q3D.ModelBuilder.Base.prototype = {

  constructor: Q3D.ModelBuilder.Base,

  addFeature: function (layerId, featureId) {
    this.features.push({layerId: layerId, featureId: featureId});
    this.buildObjects();
  },

  buildObjects: function () {
    if (!this.loaded) return;

    var deg2rad = Math.PI / 180,
        m = new THREE.Matrix4();

    // TODO: [Model] f, geom
    this.features.forEach(function (fet) {
      var layer = this.scene.mapLayers[fet.layerId],
          f = layer.f[fet.featureId];

      for (var i = 0, l = f.pts.length; i < l; i++) {
        var pt = f.pts[i],
            mesh = this.cloneObject(fet.layerId);

        // rotation
        if (f.rotateX) mesh.applyMatrix(m.makeRotationX(f.rotateX * deg2rad));
        if (f.rotateY) mesh.applyMatrix(m.makeRotationY(f.rotateY * deg2rad));
        if (f.rotateZ) mesh.applyMatrix(m.makeRotationZ(f.rotateZ * deg2rad));

        // scale and position
        if (f.scale !== undefined) mesh.scale.set(f.scale, f.scale, f.scale);
        mesh.position.set(pt[0], pt[1], pt[2]);

        mesh.userData.featureId = fet.featureId;

        layer.addObject(mesh);
      }
    }, this);

    this.features = [];
  },

  cloneObject: function (layerId) {
    if (this.object === undefined) return null;

    // if there is already the object for the layer, return a clone of the object
    if (layerId in this._objects) return this._objects[layerId].clone();

    var layer = this.scene.mapLayers[layerId];

    // clone the original object
    var object = this.object.clone();

    if (Object.keys(this._objects).length) {
      // if this is not the first layer which uses this model, clone materials
      // and append cloned materials to material list of the layer
      object.traverse(function (obj) {
        if (obj instanceof THREE.Mesh === false) return;
        obj.material = obj.material.clone();
        layer.materials.add(obj.material);
      });
    }
    else {
      // if this is the first, append original materials to material list of the layer
      object.traverse(function (obj) {
        if (obj instanceof THREE.Mesh === false) return;
        layer.materials.add(obj.material);
      });
    }
    this._objects[layerId] = object;

    // as properties of the object will be changed, clone the object to keep the original for the layer
    return object.clone();
  },

  onLoad: function (object) {
    this.object = object;
    this.loaded = true;
    this.buildObjects();
  }
};


/*
Q3D.ModelBuilder.JSON --> Q3D.ModelBuilder.Base

 load JSON data and build JSON models
*/
Q3D.ModelBuilder.JSON = function (scene, model) {
  Q3D.ModelBuilder.Base.call(this, scene, model);

  var loaders = Q3D.ModelBuilder._loaders;
  if (loaders.jsonLoader === undefined) loaders.jsonLoader = new THREE.JSONLoader(true);
  this.loader = loaders.jsonLoader;

  if (model.src !== undefined) {
    this.loader.load(model.src, this.onLoad.bind(this));
  }
  else if (model.data) {
    var result = this.loader.parse(JSON.parse(model.data));
    this.onLoad(result.geometry, result.materials);
  }
};

Q3D.ModelBuilder.JSON.prototype = Object.create(Q3D.ModelBuilder.Base.prototype);
Q3D.ModelBuilder.JSON.prototype.constructor = Q3D.ModelBuilder.JSON;

Q3D.ModelBuilder.JSON.prototype.onLoad = function (geometry, materials) {
  this.geometry = geometry;
  this.material = new THREE.MeshFaceMaterial(materials);
  Q3D.ModelBuilder.Base.prototype.onLoad.call(this, new THREE.Mesh(this.geometry, this.material));
};


/*
Q3D.ModelBuilder.JSONObject --> Q3D.ModelBuilder.Base
*/
Q3D.ModelBuilder.JSONObject = function (scene, model) {
  Q3D.ModelBuilder.Base.call(this, scene, model);

  var loaders = Q3D.ModelBuilder._loaders;
  if (loaders.jsonObjectLoader === undefined) loaders.jsonObjectLoader = new THREE.ObjectLoader();
  this.loader = loaders.jsonObjectLoader;

  if (model.src !== undefined) {
    this.loader.load(model.src, this.onLoad.bind(this));
  }
  else if (model.data) {
    this.onLoad(this.loader.parse(JSON.parse(model.data)));
  }
};

Q3D.ModelBuilder.JSONObject.prototype = Object.create(Q3D.ModelBuilder.Base.prototype);
Q3D.ModelBuilder.JSONObject.prototype.constructor = Q3D.ModelBuilder.JSONObject;


/*
Q3D.ModelBuilder.COLLADA --> Q3D.ModelBuilder.Base
*/
Q3D.ModelBuilder.COLLADA = function (scene, model) {
  Q3D.ModelBuilder.Base.call(this, scene, model);

  var loaders = Q3D.ModelBuilder._loaders;
  if (loaders.colladaLoader === undefined) loaders.colladaLoader = new THREE.ColladaLoader();
  this.loader = loaders.colladaLoader;

  if (model.src !== undefined) {
    this.loader.load(model.src, this.onLoad.bind(this));
  }
  else if (model.data) {
    var xmlParser = new DOMParser(),
        responseXML = xmlParser.parseFromString(model.data, "application/xml"),
        url = "./";
    this.onLoad(this.loader.parse(responseXML, undefined, url));
  }
};

Q3D.ModelBuilder.COLLADA.prototype = Object.create(Q3D.ModelBuilder.Base.prototype);
Q3D.ModelBuilder.COLLADA.prototype.constructor = Q3D.ModelBuilder.COLLADA;

Q3D.ModelBuilder.COLLADA.prototype.onLoad = function (collada) {
  this.collada = collada;
  Q3D.ModelBuilder.Base.prototype.onLoad.call(this, collada.scene);
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

Q3D.Utils.createWallGeometry = function (vertices, bzFunc) {
  var pt,
      geom = new THREE.PlaneBufferGeometry(0, 0, vertices.length - 1, 1),
      v = geom.attributes.position.array;
  for (var i = 0, k = 0, l = vertices.length, l3 = l * 3; i < l; i++, k += 3) {
    pt = vertices[i];
    v[k] = v[k + l3] = pt.x;
    v[k + 1] = v[k + l3 + 1] = pt.y;
    v[k + 2] = bzFunc(pt.x, pt.y);
    v[k + l3 + 2] = pt.z;
  }
  geom.computeFaceNormals();
  geom.computeVertexNormals();
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

Q3D.Utils.createOverlayGeometry = function (triangles, polygons, zFunc) {
  var geom = new THREE.Geometry();

  // vertices and faces
  if (triangles !== undefined) {
    geom.vertices = Q3D.Utils.arrayToVec3Array(triangles.v, zFunc);
    geom.faces = Q3D.Utils.arrayToFace3Array(triangles.f);
  }

  // split-polygons
  for (var i = 0, l = polygons.length; i < l; i++) {
    var polygon = polygons[i];
    var poly_geom = new THREE.Geometry(),
        holes = [];

    // make Vector3 arrays
    poly_geom.vertices = Q3D.Utils.arrayToVec3Array(polygon[0], zFunc);
    for (var j = 1, m = polygon.length; j < m; j++) {
      holes.push(Q3D.Utils.arrayToVec3Array(polygon[j], zFunc));
    }

    // triangulate polygon
    var faces = THREE.ShapeUtils.triangulateShape(poly_geom.vertices, holes);

    // append points of holes to vertices
    for (var j = 0, m = holes.length; j < m; j++) {
      Array.prototype.push.apply(poly_geom.vertices, holes[j]);
    }

    // element of faces is [index1, index2, index3]
    poly_geom.faces = Q3D.Utils.arrayToFace3Array(faces);

    geom.merge(poly_geom);
  }
  geom.mergeVertices();
  geom.computeFaceNormals();
  geom.computeVertexNormals();
  return geom;
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
