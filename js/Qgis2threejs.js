"use strict";

// Qgis2threejs.js
// (C) 2014 Minoru Akagi | MIT License
// https://github.com/minorua/Qgis2threejs

var Q3D = {VERSION: "1.4.2"};
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
Q3D.Group -> THREE.Scene -> THREE.Object3D
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


/*
Q3D.Scene -> THREE.Scene -> THREE.Object3D

.mapLayers: an object that holds map layers contained in this scene. the key is layerId.
            use .loadLayerJSONObject() to add a map layer to this scene.
.userData: an object that holds metadata (crs, proj, baseExtent, rotation, width, zExaggeration, zShift, wgs84Center)
           properties of the scene object in JSON data?

.add(object):
.getObjectByName(layerId): returns the layer object specified by the layer id.

--
custom function
.loadLayerJSONObject(json_obj): 
.toMapCoordinates(x, y, z): converts world coordinates to map coordinates
._rotatePoint(point, degrees, origin): 
*/
Q3D.Scene = function () {
  THREE.Scene.call(this);
  this.autoUpdate = false;

  // scene is z-up
  this.rotateX(-Math.PI / 2);
  this.updateMatrixWorld();

  this.mapLayers = {};

  this.lightGroup = new Q3D.Group();
  this.add(this.lightGroup);
};

Q3D.Scene.prototype = Object.create(THREE.Scene.prototype);
Q3D.Scene.prototype.constructor = Q3D.Scene;

Q3D.Scene.prototype.add = function (object) {
  THREE.Scene.prototype.add.call(this, object);
  object.updateMatrixWorld();
};

Q3D.Scene.prototype.loadJSONObject = function (jsonObject) {
  // console.assert(jsonObject.type == "scene");

  // set properties
  if (jsonObject.properties !== undefined) this.userData = jsonObject.properties;

  // load lights
  if (jsonObject.lights !== undefined) {
    // remove all existing lights
    for (var i = this.lightGroup.children.length - 1 ; i >= 0; i--) {
      this.lightGroup.remove(this.lightGroup.children[i]);
    }

    // TODO: load light settings and build lights
  }

  // create default lights if this scene has no lights
  if (this.lightGroup.children.length == 0) this.buildDefaultLights();

  // load layers
  if (jsonObject.layers !== undefined) {
    jsonObject.layers.forEach(function (layer) {
      this.loadLayerJSONObject(layer);
    }, this);
  }
};

Q3D.Scene.prototype.loadLayerJSONObject = function (jsonObject) {
  // console.assert(jsonObject.type == "layer");

  var _this = this;
  var requestRender = function () {
    _this.dispatchEvent({type: "renderRequest"});
  };

  var layer = this.mapLayers[jsonObject.id];
  if (layer === undefined) {
    // console.assert(jsonObject.properties !== undefined);
    var type = jsonObject.properties.type
    if (type == "dem") layer = new Q3D.DEMLayer(this);
    else if (type == "point") layer = new Q3D.PointLayer(this);
    else if (type == "line") layer = new Q3D.LineLayer(this);
    else if (type == "polygon") layer = new Q3D.PolygonLayer(this);
    else {
      // console.error("unknown layer type:" + type);
      return;
    }
    layer.addEventListener("renderRequest", requestRender);

    this.mapLayers[jsonObject.id] = layer;
    this.add(layer.objectGroup);
  }

  layer.loadJSONObject(jsonObject);

  requestRender();
 
  /* TODO: build labels
  // build labels
  if (layer.l) {
    layer.buildLabels(app.labelConnectorGroup, app.labelRootElement);
    app.labels = app.labels.concat(layer.labels);
  }

  if (app.labels.length) app.scene.add(app.labelConnectorGroup);
  */

  /* TODO: load models
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

    // scene
    app.scene = new Q3D.Scene();
    app.scene.addEventListener("renderRequest", function (event) {
      app.render();
    });

    // camera
    app.buildDefaultCamera();

    // restore view (camera position and its target) from URL parameters
    var vars = app.urlParams;
    if (vars.cx !== undefined) app.camera.position.set(parseFloat(vars.cx), parseFloat(vars.cy), parseFloat(vars.cz));
    if (vars.ux !== undefined) app.camera.up.set(parseFloat(vars.ux), parseFloat(vars.uy), parseFloat(vars.uz));
    if (vars.tx !== undefined) app.camera.lookAt(parseFloat(vars.tx), parseFloat(vars.ty), parseFloat(vars.tz));

    // orbit controls
    app.controls = new THREE.OrbitControls(app.camera, app.renderer.domElement);
    var controls = app.controls;
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
      scope.target.copy(controls.object.position).add(offset);
      scope.object.lookAt(controls.target);
    };

    controls.update();

      /*
    if (vars.tx !== undefined) {
      app.controls.target.set(parseFloat(vars.tx), parseFloat(vars.ty), parseFloat(vars.tz));
      app.controls.target0.copy(app.controls.target);   // for reset
    }
    */

    // label
    app.labelVisibility = Q3D.Options.label.visible;
    app.labelConnectorGroup = new Q3D.Group();
    app.labels = [];     // labels of visible layers

    // root element for labels
    var e = document.createElement("div");
    e.style.display = (app.labelVisibility) ? "block" : "none";
    app.container.appendChild(e);
    app.labelRootElement = e;

    // create a marker for queried point
    var opt = Q3D.Options.qmarker;
    app.queryMarker = new THREE.Mesh(new THREE.SphereGeometry(opt.r),
                                      new THREE.MeshLambertMaterial({color: opt.c, opacity: opt.o, transparent: (opt.o < 1)}));
    app.queryMarker.visible = false;
    app.scene.add(app.queryMarker);

    app.highlightMaterial = new THREE.MeshLambertMaterial({emissive: 0x999900, transparent: true, opacity: 0.5});
    if (!Q3D.isIE) app.highlightMaterial.side = THREE.DoubleSide;    // Shader compilation error occurs with double sided material on IE11

    app._queryableObjects = [];
    app.queryObjNeedsUpdate = true;
    app.selectedLayerId = null;
    app.selectedFeatureId = null;
    app.highlightObject = null;

    app.modelBuilders = [];
    app._wireframeMode = false;

    // TODO:
    // wireframe mode setting
    // if ("wireframe" in app.urlParams) app.setWireframeMode(true);
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
    if (jsonObject.type == "scene") {
      app.scene.loadJSONObject(jsonObject);
    }
    else if (jsonObject.type == "layer") {
      app.scene.loadLayerJSONObject(jsonObject);    // TODO: -> .loadJSONObject
    }
  };

  app.loadJSONFromURL = function (url) {

    var xhr = new XMLHttpRequest();
    xhr.open("GET", url, true);
    xhr.responseType = "json";
    xhr.onload = function () {
      app.loadJSONObject(this.response);
    };
    xhr.send(null);

    /* latest three.js has THREE.FileLoader()
    var loader = new THREE.FileLoader();
    loader.setResponseType("json");
    loader.load(url, app.loadJSON,    // url, onLoad
      // onProcess
      function (xhr) {
        console.log((xhr.loaded / xhr.total * 100) + "% loaded");
      },
      // onError
      function (xhr) {
        console.error("An error happened");
      });
    */
  };

  app.addEventListeners = function () {
    window.addEventListener("keydown", app.eventListener.keydown);
    window.addEventListener("resize", app.eventListener.resize);

    app.controls.addEventListener("change", function (event) {
      app.render();
    });

    var e = Q3D.$("closebtn");
    if (e) e.addEventListener("click", app.closePopup);
  };

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
            controls.moveForward(3 * panDelta)    // horizontally forward
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
          case 87:  // W
            app.setWireframeMode(!app._wireframeMode);
            return;
          default:
            return;
        }
      }
      app.controls.update();
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

  app.buildDefaultCamera = function () {
    app.camera = new THREE.PerspectiveCamera(45, app.width / app.height, 0.1, 1000);
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

  // animation loop
  app.animate = function () {
    if (app.running) requestAnimationFrame(app.animate);
    app.render(true);
  };

  app.render = function (updateControls) {
    if (updateControls && app.controls.update()) return;    // changeEvent handler calls app.render()
    app.renderer.render(app.scene, app.camera);
    app.updateLabelPosition();
  };

  // update label position
  app.updateLabelPosition = function () {
    if (!app.labelVisibility || app.labels.length == 0) return;

    var widthHalf = app.width / 2,
        heightHalf = app.height / 2,
        autosize = Q3D.Options.label.autoSize,
        camera = app.camera,
        camera_pos = camera.position,
        c2t = app.controls.target.clone().sub(camera_pos),
        c2l = new THREE.Vector3(),
        v = new THREE.Vector3();

    // make a list of [label index, distance to camera]
    var idx_dist = [];
    for (var i = 0, l = app.labels.length; i < l; i++) {
      idx_dist.push([i, camera_pos.distanceTo(app.labels[i].pt)]);
    }

    // sort label indexes in descending order of distances
    idx_dist.sort(function (a, b) {
      if (a[1] < b[1]) return 1;
      if (a[1] > b[1]) return -1;
      return 0;
    });

    var label, e, x, y, dist, fontSize;
    var minFontSize = Q3D.Options.label.minFontSize;
    for (var i = 0, l = idx_dist.length; i < l; i++) {
      label = app.labels[idx_dist[i][0]];
      e = label.e;
      if (c2l.subVectors(label.pt, camera_pos).dot(c2t) > 0) {
        // label is in front
        // calculate label position
        v.copy(label.pt).project(camera);
        x = (v.x * widthHalf) + widthHalf;
        y = -(v.y * heightHalf) + heightHalf;

        // set label position
        e.style.display = "block";
        e.style.left = (x - (e.offsetWidth / 2)) + "px";
        e.style.top = (y - (e.offsetHeight / 2)) + "px";
        e.style.zIndex = i + 1;

        // set font size
        if (autosize) {
          dist = idx_dist[i][1];
          if (dist < 10) dist = 10;
          fontSize = Math.max(Math.round(1000 / dist), minFontSize);
          e.style.fontSize = fontSize + "px";
        }
      }
      else {
        // label is in back
        e.style.display = "none";
      }
    }
  };

  app.labelVisibilityChanged = function () {
    app.labels = [];
    var layer;
    for (var id in app.scene.mapLayers) {
      if (layer.l && layer.visible) app.labels = app.labels.concat(layer.labels);
    }
  };

  app.setLabelVisibility = function (visible) {
    app.labelVisibility = visible;
    app.labelRootElement.style.display = (visible) ? "block" : "none";
    app.labelConnectorGroup.visible = visible;

    if (app.labels.length) app.render();
  };

  app.setWireframeMode = function (wireframe) {
    if (wireframe == app._wireframeMode) return;

    for (var id in app.scene.mapLayers) {
      app.scene.mapLayers[id].setWireframeMode(wireframe);
    }

    app._wireframeMode = wireframe;
  };

  app.queryableObjects = function () {
    if (app.queryObjNeedsUpdate) {
      app._queryableObjects = [];
      var layer;
      for (var id in app.scene.mapLayers) {
        layer = app.scene.mapLayers[id];
        if (layer.visible && layer.queryableObjects.length) app._queryableObjects = app._queryableObjects.concat(layer.queryableObjects);
      }
    }
    return app._queryableObjects;
  };

  app.intersectObjects = function (offsetX, offsetY) {
    var x = (offsetX / app.width) * 2 - 1;
    var y = -(offsetY / app.height) * 2 + 1;
    var vector = new THREE.Vector3(x, y, 1);
    vector.unproject(app.camera);
    var ray = new THREE.Raycaster(app.camera.position, vector.sub(app.camera.position).normalize());
    return ray.intersectObjects(app.queryableObjects());
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

  app.showQueryResult = function (point, layerId, featureId) {
    var layer, r = [];
    if (layerId !== undefined) {
      // layer name
      layer = app.scene.mapLayers[layerId];
      r.push('<table class="layer">');
      r.push("<caption>Layer name</caption>");
      r.push("<tr><td>" + layer.name + "</td></tr>");
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

    if (layerId !== undefined && featureId !== undefined && layer.a !== undefined) {
      // attributes
      r.push('<table class="attrs">');
      r.push("<caption>Attributes</caption>");
      var f = layer.f[featureId];
      for (var i = 0, l = layer.a.length; i < l; i++) {
        r.push("<tr><td>" + layer.a[i] + "</td><td>" + f.a[i] + "</td></tr>");
      }
      r.push("</table>");
    }
    app.popup.show(r.join(""));
  };

  app.showPrintDialog = function () {

    function e (tagName, parent, innerHTML) {
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
    e("span", d2, "px,")

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
    }

    app.popup.show(f, "Save Image", true);   // modal
  };

  app.closePopup = function () {
    app.popup.hide();
    app.queryMarker.visible = false;
    app.highlightFeature(null, null);
    if (app._canvasImageUrl) {
      URL.revokeObjectURL(app._canvasImageUrl);
      app._canvasImageUrl = null;
    }
  };

  app.highlightFeature = function (layerId, featureId) {
    if (app.highlightObject) {
      // remove highlight object from the scene
      app.scene.remove(app.highlightObject);
      app.selectedLayerId = null;
      app.selectedFeatureId = null;
      app.highlightObject = null;
    }

    if (layerId === null || featureId === null) return;

    var layer = app.scene.mapLayers[layerId];
    if (layer === undefined) return;
    if (["Icon", "JSON model", "COLLADA model"].indexOf(layer.objType) != -1) return;

    var f = layer.f[featureId];
    if (f === undefined || f.objs.length == 0) return;

    var high_mat = app.highlightMaterial;
    var setMaterial = function (obj) {
      obj.material = high_mat;
    };

    // create a highlight object (if layer type is Point, slightly bigger than the object)
    var highlightObject = new Q3D.Group();
    var clone, s = (layer.type == Q3D.LayerType.Point) ? 1.01 : 1;

    for (var i = 0, l = f.objs.length; i < l; i++) {
      clone = f.objs[i].clone();
      clone.traverse(setMaterial);
      if (s != 1) clone.scale.set(clone.scale.x * s, clone.scale.y * s, clone.scale.z * s);
      highlightObject.add(clone);
    }

    // add the highlight object to the scene
    app.scene.add(highlightObject);

    app.selectedLayerId = layerId;
    app.selectedFeatureId = featureId;
    app.highlightObject = highlightObject;
  };

  // Called from *Controls.js when canvas is clicked
  app.canvasClicked = function (e) {
    var canvasOffset = app._offset(app.renderer.domElement);
    var objs = app.intersectObjects(e.clientX - canvasOffset.left, e.clientY - canvasOffset.top);

    for (var i = 0, l = objs.length; i < l; i++) {
      var obj = objs[i];
      if (!obj.object.visible) continue;

      // query marker
      app.queryMarker.position.set(obj.point.x, obj.point.y, obj.point.z);
      app.queryMarker.visible = true;
      app.queryMarker.updateMatrixWorld();

      // get layerId and featureId of clicked object
      var object = obj.object, layerId, featureId;
      while (object) {
        layerId = object.userData.layerId,
        featureId = object.userData.featureId;
        if (layerId !== undefined) break;
        object = object.parent;
      }

      // highlight clicked object
      app.highlightFeature((layerId === undefined) ? null : layerId,
                            (featureId === undefined) ? null : featureId);

      app.showQueryResult(obj.point, layerId, featureId);

      if (Q3D.Options.debugMode && object instanceof THREE.Mesh) {
        var face = obj.face,
            geom = object.geometry;
        if (face) {
          if (geom instanceof THREE.Geometry) {
            var v = object.geometry.vertices;
            console.log(v[face.a], v[face.b], v[face.c]);
          }
          else {
            console.log("Qgis2threejs: [DEBUG] THREE.BufferGeometry");
          }
        }
      }

      return;
    }
    app.closePopup();
  };

  app.saveCanvasImage = function (width, height, fill_background) {
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

    var saveCanvasImage = function (canvas) {
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
      for (var i = 0, l = app.labels.length; i < l; i++) {
        idx_dist.push([i, camera_pos.distanceTo(app.labels[i].pt)]);
      }

      // sort label indexes in descending order of distances
      idx_dist.sort(function (a, b) {
        if (a[1] < b[1]) return 1;
        if (a[1] > b[1]) return -1;
        return 0;
      });

      var label, text, x, y;
      for (var i = 0, l = idx_dist.length; i < l; i++) {
        label = app.labels[idx_dist[i][0]];
        text = label.e.textContent;
        if (c2l.subVectors(label.pt, camera_pos).dot(c2t) > 0) {    // label is in front
          // calculate label position
          v.copy(label.pt).project(camera);
          x = (v.x * widthHalf) + widthHalf;
          y = -(v.y * heightHalf) + heightHalf;
          if (x < 0 || width <= x || y < 0 || height <= y) continue;

          // outline effect
          ctx.fillStyle = "#FFF";
          for (var j = 0; j < 9; j++) {
            if (j != 4) ctx.fillText(text, x + Math.floor(j / 3) - 1, y + j % 3 - 1);
          }

          ctx.fillStyle = color;
          ctx.fillText(text, x, y);
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

    var render_labels = (app.labelVisibility && app.labels.length > 0);
    if ((fill_background && bgcolor === null) || render_labels) {
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
        if (render_labels) renderLabels(ctx);

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
        opt.map = THREE.ImageUtils.loadTexture(image.url, undefined, callback);
      }
      else if (image.object !== undefined) {    // WebKit Bridge
        opt.map = new THREE.Texture(image.object.toImageData());
        opt.map.needsUpdate = true;
        callback();
      }
      else {    // base64   TODO: remove
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
      this.mat = new THREE.MeshLambertMaterial(opt);
    }
    else if (m.type == Q3D.MaterialType.MeshPhong) {
      if (m.c !== undefined) opt.color = m.c;
      this.mat = new THREE.MeshPhongMaterial(opt);
    }
    else if (m.type == Q3D.MaterialType.LineBasic) {
      opt.color = m.c;
      this.mat = new THREE.LineBasicMaterial(opt);
    }
    else {
      opt.color = 0xffffff;
      this.mat = new THREE.SpriteMaterial(opt);
    }
  },

  set: function (material) {
    this.mat = material;
    this.origProp = {};
  },

  type: function () {
    if (this.mat instanceof THREE.MeshLambertMaterial) return Q3D.MaterialType.MeshLambert;
    if (this.mat instanceof THREE.MeshPhongMaterial) return Q3D.MaterialType.MeshPhong;
    if (this.mat instanceof THREE.LineBasicMaterial) return Q3D.MaterialType.LineBasic;
    if (this.mat instanceof THREE.SpriteMaterial) return Q3D.MaterialType.Sprite;
    if (this.mat === undefined) return undefined;
    if (this.mat === null) return null;
    return Q3D.MaterialType.Unknown;
  },

  dispose: function () {
    if (!this.mat) return;

    if (this.mat.map) this.mat.map.dispose();   // dispose of texture
    this.mat.dispose();
    this.mat = null;
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
    var mat = new Q3D.Material();
    mat.set(material);
    this.materials.push(mat);
  }
};

Q3D.Materials.prototype.get = function (index) {
  return this.materials[index];
};

Q3D.Materials.prototype.mat = function (index) {
  return this.materials[index].mat;
};


Q3D.Materials.prototype.loadJSONObject = function (jsonObject) {
  var _this = this, iterated = false;
  var callback = function () {
    if (iterated) _this.dispatchEvent({type: "renderRequest"});
  };

  for (var i = 0, l = jsonObject.length; i < l; i++) {
    var mat = new Q3D.Material();
    mat.loadJSONObject(jsonObject[i], callback);    // callback is called when a texture is loaded
    this.add(mat);
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
    material.mat.transparent = Boolean(material.origProp.t) || (opacity < 1);
    material.mat.opacity = opacity;
  }
};

// wireframe: boolean
Q3D.Materials.prototype.setWireframeMode = function (wireframe) {
  var material;
  for (var i = 0, l = this.materials.length; i < l; i++) {
    material = this.materials[i];
    if (material.origProp.w || material.mat instanceof THREE.LineBasicMaterial) continue;
    material.mat.wireframe = wireframe;
  }
};


/*
Q3D.DEMBlock
*/
Q3D.DEMBlock = function (params) {
  for (var k in params) {
    this[k] = params[k];
  }
};

Q3D.DEMBlock.prototype = {

  constructor: Q3D.DEMBlock,

  build: function (layer, material, callback) {     // TODO: -> shading, materials, callback
    var PlaneGeometry = (Q3D.Options.exportMode) ? THREE.PlaneGeometry : THREE.PlaneBufferGeometry,
        geom = new PlaneGeometry(this.width, this.height, this.grid.width - 1, this.grid.height - 1),
        mesh = new THREE.Mesh(geom, material),    // TODO: , layer.materials[this.m].m);
        block = this;

    if (this.grid.array !== undefined) {    // WebKit Bridge
      var grid_values = this.grid.array;

      if (Q3D.Options.exportMode) {
        for (var i = 0, l = geom.vertices.length; i < l; i++) {
          geom.vertices[i].z = grid_values[i];
        }
      }
      else {
        var vertices = geom.attributes.position.array;
        for (var i = 0, j = 0, l = vertices.length; i < l; i++, j += 3) {
          vertices[j + 2] = grid_values[i];
        }
      }

      // Calculate normals
      if (layer.properties.shading) {
        geom.computeFaceNormals();
        geom.computeVertexNormals();
      }

      if (callback) callback(block);
    }
    else if (this.grid.url !== undefined) {
      var xhr = new XMLHttpRequest();
      xhr.open("GET", this.grid.url);
      xhr.responseType = "arraybuffer";

      xhr.onload = function (event) {
        var arrayBuffer = xhr.response;
        if (arrayBuffer) {
          var grid_values = new Float32Array(arrayBuffer);
          var vertices = geom.attributes.position.array;
          for (var i = 0, j = 0, l = vertices.length; i < l; i++, j += 3) {
            vertices[j + 2] = grid_values[i];
          }

          // Calculate normals
          if (layer.properties.shading) {
            geom.computeFaceNormals();
            geom.computeVertexNormals();
          }

          geom.attributes.position.needsUpdate = true;

          block.grid.array = grid_values;
          if (callback) callback(block);
        }
      };
      xhr.send(null);
    }

    // TODO: if (this.plane.offsetX != 0) mesh.position.x = this.plane.offsetX;
    // TODO: if (this.plane.offsetY != 0) mesh.position.y = this.plane.offsetY;
    this.obj = mesh;
    return mesh;
  },

  buildSides: function (layer, material, z0) {
    var PlaneGeometry = (Q3D.Options.exportMode) ? THREE.PlaneGeometry : THREE.PlaneBufferGeometry;
    var band_width = -z0 * 2, grid_values = this.grid.array, w = this.grid.width, h = this.grid.height, HALF_PI = Math.PI / 2;
    var i, mesh;

    // front and back
    var geom_fr = new PlaneGeometry(this.width, band_width, w - 1, 1),
        geom_ba = new PlaneGeometry(this.width, band_width, w - 1, 1);

    var k = w * (h - 1);
    if (Q3D.Options.exportMode) {
      for (i = 0; i < w; i++) {
        geom_fr.vertices[i].y = grid_values[k + i];
        geom_ba.vertices[i].y = grid_values[w - 1 - i];
      }
    }
    else {
      var vertices_fr = geom_fr.attributes.position.array,
          vertices_ba = geom_ba.attributes.position.array;

      for (i = 0; i < w; i++) {
        vertices_fr[i * 3 + 1] = grid_values[k + i];
        vertices_ba[i * 3 + 1] = grid_values[w - 1 - i];
      }
    }
    mesh = new THREE.Mesh(geom_fr, material);
    mesh.position.y = -this.height / 2;
    mesh.rotateOnAxis(Q3D.uv.i, HALF_PI);
    mesh.name = "side";
    layer.addObject(mesh, false);

    mesh = new THREE.Mesh(geom_ba, material);
    mesh.position.y = this.height / 2;
    mesh.rotateOnAxis(Q3D.uv.k, Math.PI);
    mesh.rotateOnAxis(Q3D.uv.i, HALF_PI);
    mesh.name = "side";
    layer.addObject(mesh, false);

    // left and right
    var geom_le = new PlaneGeometry(band_width, this.height, 1, h - 1),
        geom_ri = new PlaneGeometry(band_width, this.height, 1, h - 1);

    if (Q3D.Options.exportMode) {
      for (i = 0; i < h; i++) {
        geom_le.vertices[i * 2 + 1].x = grid_values[w * i];
        geom_ri.vertices[i * 2].x = -grid_values[w * (i + 1) - 1];
      }
    }
    else {
      var vertices_le = geom_le.attributes.position.array,
          vertices_ri = geom_ri.attributes.position.array;

      for (i = 0; i < h; i++) {
        vertices_le[(i * 2 + 1) * 3] = grid_values[w * i];
        vertices_ri[i * 2 * 3] = -grid_values[w * (i + 1) - 1];
      }
    }
    mesh = new THREE.Mesh(geom_le, material);
    mesh.position.x = -this.width / 2;
    mesh.rotateOnAxis(Q3D.uv.j, -HALF_PI);
    mesh.name = "side";
    layer.addObject(mesh, false);

    mesh = new THREE.Mesh(geom_ri, material);
    mesh.position.x = this.width / 2;
    mesh.rotateOnAxis(Q3D.uv.j, HALF_PI);
    mesh.name = "side";
    layer.addObject(mesh, false);

    // bottom
    if (Q3D.Options.exportMode) {
      var geom = new THREE.PlaneGeometry(this.width, this.height, w - 1, h - 1);
    }
    else {
      var geom = new THREE.PlaneBufferGeometry(this.width, this.height, 1, 1);
    }
    mesh = new THREE.Mesh(geom, material);
    mesh.position.z = z0;
    mesh.rotateOnAxis(Q3D.uv.i, Math.PI);
    mesh.name = "bottom";
    layer.addObject(mesh, false);
    // TODO: return object group
  },

  getValue: function (x, y) {
    if (0 <= x && x < this.width && 0 <= y && y < this.height) return this.data[x + this.width * y];
    return null;
  },

  contains: function (x, y) {
    var xmin = this.plane.offsetX - this.plane.width / 2,
        xmax = this.plane.offsetX + this.plane.width / 2,
        ymin = this.plane.offsetY - this.plane.height / 2,
        ymax = this.plane.offsetY + this.plane.height / 2;
    if (xmin <= x && x <= xmax && ymin <= y && y <= ymax) return true;
    return false;
  }

};


/*
Q3D.ClippedDEMBlock
*/
Q3D.ClippedDEMBlock = function (params) {
  for (var k in params) {
    this[k] = params[k];
  }
};

Q3D.ClippedDEMBlock.prototype = {

  constructor: Q3D.ClippedDEMBlock,

  build: function (layer, material) {
    var geom = Q3D.Utils.createOverlayGeometry(this.clip.triangles, this.clip.split_polygons, layer.getZ.bind(layer));

    // set UVs
    Q3D.Utils.setGeometryUVs(geom, layer.scene.userData.width, layer.scene.userData.height);

    var mesh = new THREE.Mesh(geom, material);
    if (this.plane.offsetX != 0) mesh.position.x = this.plane.offsetX;
    if (this.plane.offsetY != 0) mesh.position.y = this.plane.offsetY;
    this.obj = mesh;
    layer.addObject(mesh);
  },

  buildSides: function (layer, material, z0) {
    var polygons = this.clip.polygons,
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
        layer.addObject(mesh, false);
      }

      // bottom
      shape = new THREE.Shape(Q3D.Utils.arrayToVec2Array(polygon[0]));
      for (var j = 1, m = polygon.length; j < m; j++) {
        shape.holes.push(new THREE.Path(Q3D.Utils.arrayToVec2Array(polygon[j])));
      }
      geom = new THREE.ShapeGeometry(shape);
      mesh = new THREE.Mesh(geom, mat_back);
      mesh.position.z = z0;
      mesh.name = "bottom";
      layer.addObject(mesh, false);
    }
  },

  getValue: function (x, y) {
    if (0 <= x && x < this.width && 0 <= y && y < this.height) return this.data[x + this.width * y];
    return null;
  },

  contains: function (x, y) {
    var xmin = this.plane.offsetX - this.plane.width / 2,
        xmax = this.plane.offsetX + this.plane.width / 2,
        ymin = this.plane.offsetY - this.plane.height / 2,
        ymax = this.plane.offsetY + this.plane.height / 2;
    if (xmin <= x && x <= xmax && ymin <= y && y <= ymax) return true;
    return false;
  }

};

/*
Q3D.MapLayer
*/
Q3D.MapLayer = function (scene) {
  this.scene = scene;
  this.visible = true;
  this.opacity = 1;

  this.materials = new Q3D.Materials();

  var _this = this;
  this.materials.addEventListener("renderRequest", function (event) {
    console.log("renderRequest from materials");
    _this.dispatchEvent({type: "renderRequest"});
  });

  this.objectGroup = new Q3D.Group();
  this.queryableObjects = [];
};

Q3D.MapLayer.prototype = Object.create(THREE.EventDispatcher.prototype);
Q3D.MapLayer.prototype.constructor = Q3D.MapLayer;

Q3D.MapLayer.prototype.addObject = function (object, queryable) {
  if (queryable === undefined) queryable = this.q;

  this.objectGroup.add(object);
  if (queryable) this._addQueryableObject(object);
};

Q3D.MapLayer.prototype._addQueryableObject = function (object) {
  this.queryableObjects.push(object);
  for (var i = 0, l = object.children.length; i < l; i++) {
    this._addQueryableObject(object.children[i]);
  }
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
  this.queryableObjects = [];
};

Q3D.MapLayer.prototype.loadJSONObject = function (jsonObject) {
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
};

Q3D.MapLayer.prototype.setOpacity = function (opacity) {
  this.materials.setOpacity(opacity);
  this.opacity = opacity;
};

Q3D.MapLayer.prototype.setVisible = function (visible) {
  // if (this.visible === visible) return;
  this.visible = visible;
  this.objectGroup.visible = visible;
  Q3D.application.queryObjNeedsUpdate = true;
};

Q3D.MapLayer.prototype.setWireframeMode = function (wireframe) {
  this.materials.setWireframeMode(wireframe);
};


/*
Q3D.MapLayer.prototype.build = function () {};
Q3D.MapLayer.prototype.meshes = function () {};
*/


/*
Q3D.DEMLayer --> Q3D.MapLayer
*/
Q3D.DEMLayer = function (scene) {
  Q3D.MapLayer.call(this, scene);
  this.type = Q3D.LayerType.DEM;
  this.blocks = [];
};

Q3D.DEMLayer.prototype = Object.create(Q3D.MapLayer.prototype);
Q3D.DEMLayer.prototype.constructor = Q3D.DEMLayer;

Q3D.DEMLayer.prototype.loadJSONObject = function (jsonObject) {
  Q3D.MapLayer.prototype.loadJSONObject.call(this, jsonObject);

  if (jsonObject.data !== undefined) this.build(jsonObject.data);
};

Q3D.DEMLayer.prototype.addBlock = function (params, clipped) {
  var BlockClass = (clipped) ? Q3D.ClippedDEMBlock : Q3D.DEMBlock,
      block = new BlockClass(params);
  this.blocks.push(block);
  return block;
};

Q3D.DEMLayer.prototype.build = function (data) {
  var layer = this,
      opt = Q3D.Options;

  var callback = function (block) {
    // build sides, bottom and frame
    if (block.sides) {
      // material
      var matProp = layer.materials.get(block.mat).origProp;
      var opacity = (matProp.o !== undefined) ? matProp.o : 1;
      var mat = new THREE.MeshLambertMaterial({color: opt.side.color,
                                               opacity: opacity,
                                               transparent: (opacity < 1)});
      layer.materials.add(mat);

      block.buildSides(layer, mat, opt.side.bottomZ);                 // TODO: layer.objectGroup.add()
      layer.sideVisible = true;
    }
    if (block.frame) {
      layer.buildFrame(block, opt.frame.color, opt.frame.bottomZ);    // layer.objectGroup.add()
      layer.sideVisible = true;
    }

    if (block.grid.url !== undefined) layer.dispatchEvent({type: "renderRequest"});
  };

  // build blocks
  data.blocks.forEach(function (b) {
    var block = new Q3D.DEMBlock(b);
    this.blocks.push(block);

    var obj = block.build(this, this.materials.mat(b.mat), callback);
    obj.userData.layerId = this.index;
    this.objectGroup.add(obj);
  }, this);
};

Q3D.DEMLayer.prototype.buildFrame = function (block, color, z0) {
  var opacity = this.materials.mat(block.mat).opacity;
  if (opacity === undefined) opacity = 1;
  var mat = new THREE.LineBasicMaterial({color: color,
                                         opacity: opacity,
                                         transparent: (opacity < 1)});
  this.materials.add(mat);

  // horizontal rectangle at bottom
  var hw = block.width / 2, hh = block.height / 2;
  var geom = new THREE.Geometry();
  geom.vertices.push(new THREE.Vector3(-hw, -hh, z0),
                     new THREE.Vector3(hw, -hh, z0),
                     new THREE.Vector3(hw, hh, z0),
                     new THREE.Vector3(-hw, hh, z0),
                     new THREE.Vector3(-hw, -hh, z0));

  var obj = new THREE.Line(geom, mat);
  obj.name = "frame";
  this.addObject(obj, false);

  // vertical lines at corners
  var pts = [[-hw, -hh, block.grid.array[block.grid.array.length - block.grid.width]],
             [hw, -hh, block.grid.array[block.grid.array.length - 1]],
             [hw, hh, block.grid.array[block.grid.width - 1]],
             [-hw, hh, block.grid.array[0]]];
  pts.forEach(function (pt) {
    var geom = new THREE.Geometry();
    geom.vertices.push(new THREE.Vector3(pt[0], pt[1], pt[2]),
                       new THREE.Vector3(pt[0], pt[1], z0));

    var obj = new THREE.Line(geom, mat);
    obj.name = "frame";
    this.addObject(obj, false);
  }, this);
};

// TODO: remove
Q3D.DEMLayer.prototype.meshes = function () {
  var m = [];
  this.blocks.forEach(function (block) {
    m.push(block.obj);
    (block.aObjs || []).forEach(function (obj) {
      m.push(obj);
    });
  });
  return m;
};

// calculate elevation at the coordinates (x, y) on triangle face
Q3D.DEMLayer.prototype.getZ = function (x, y) {
  var xmin = -this.scene.userData.width / 2,
      ymax = this.scene.userData.height / 2;

  for (var i = 0, l = this.blocks.length; i < l; i++) {
    var block = this.blocks[i];
    if (!block.contains(x, y)) continue;

    var ix = block.plane.width / (block.width - 1),
        iy = block.plane.height / (block.height - 1);

    var xmin = block.plane.offsetX - block.plane.width / 2,
        ymax = block.plane.offsetY + block.plane.height / 2;

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
  var width = this.scene.userData.width, height = this.scene.userData.height;
  var xmin = -width / 2, ymax = height / 2;
  var block = this.blocks[0];
  var x_segments = block.width - 1,
      y_segments = block.height - 1;
  var ix = width / x_segments,
      iy = height / y_segments;

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

    p.sort(function (a, b) { return a - b; });

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
Q3D.VectorLayer = function (scene) {
  Q3D.MapLayer.call(this, scene);
  this.f = [];
  this.labels = [];
};

Q3D.VectorLayer.prototype = Object.create(Q3D.MapLayer.prototype);
Q3D.VectorLayer.prototype.constructor = Q3D.VectorLayer;

Q3D.VectorLayer.prototype.build = function (startIndex) {};

Q3D.VectorLayer.prototype.buildLabels = function (parent, parentElement, getPointsFunc, zFunc) {
  var label = this.l;
  if (label === undefined || getPointsFunc === undefined) return;

  // function to get height for both ends of label connector
  // label.ht
  //  1: fixed height
  //  2: height from point (bottom height if extruded polygon, elevation at centroid of polygon if overlay)
  //  3: height from top of extruded polygon / from overlay
  //  >= 100: data-defined + addend
  var zShift = this.scene.userData.zShift, zScale = this.scene.userData.zScale;
  var labelHeightFunc = function (f, pt) {
    var z0 = (zFunc === undefined) ? pt[2] : zFunc(pt[0], pt[1]);

    if (label.ht == 1) return [z0, label.v];
    if (label.ht >= 100) return [z0, (f.a[label.ht - 100] + zShift) * zScale + label.v];

    if (label.ht == 3) z0 += f.h;
    return [z0, z0 + label.v];
  };

  var line_mat = new THREE.LineBasicMaterial({color: Q3D.Options.label.connectorColor});
  this.labelConnectorGroup = new Q3D.Group();
  this.labelConnectorGroup.userData.layerId = this.index;
  if (parent) parent.add(this.labelConnectorGroup);

  // create parent element for labels
  var e = document.createElement("div");
  parentElement.appendChild(e);
  this.labelParentElement = e;

  for (var i = 0, l = this.f.length; i < l; i++) {
    var f = this.f[i];
    f.aElems = [];
    f.aObjs = [];
    var text = f.a[label.i];
    if (text === null || text === "") continue;

    var pts = getPointsFunc(f);
    for (var j = 0, m = pts.length; j < m; j++) {
      var pt = pts[j];
      // create div element for label
      var e = document.createElement("div");
      e.appendChild(document.createTextNode(text));
      e.className = "label";
      this.labelParentElement.appendChild(e);

      var z = labelHeightFunc(f, pt);
      var pt0 = new THREE.Vector3(pt[0], pt[1], z[0]);    // bottom
      var pt1 = new THREE.Vector3(pt[0], pt[1], z[1]);    // top

      // create connector
      var geom = new THREE.Geometry();
      geom.vertices.push(pt1, pt0);
      var conn = new THREE.Line(geom, line_mat);
      conn.userData.layerId = this.index;
      conn.userData.featureId = i;
      this.labelConnectorGroup.add(conn);

      f.aElems.push(e);
      f.aObjs.push(conn);
      this.labels.push({e: e, obj: conn, pt: pt1});
    }
  }
};

Q3D.VectorLayer.prototype.loadJSONObject = function (jsonObject) {
  Q3D.MapLayer.prototype.loadJSONObject.call(this, jsonObject);
};

Q3D.VectorLayer.prototype.meshes = function () {
  var meshes = [];
  for (var i = 0, l = this.f.length; i < l; i++) {
    var f = this.f[i];
    for (var j = 0, m = f.objs.length; j < m; j++) {
      meshes.push(f.objs[j]);
    }
  }
  return meshes;
};

Q3D.VectorLayer.prototype.setVisible = function (visible) {
  Q3D.MapLayer.prototype.setVisible.call(this, visible);
  if (this.labels.length == 0) return;

  this.labelParentElement.style.display = (visible) ? "block" : "none";
  this.labelConnectorGroup.visible = visible;
  Q3D.application.labelVisibilityChanged();
};


/*
Q3D.PointLayer --> Q3D.VectorLayer
*/
Q3D.PointLayer = function (scene) {
  Q3D.VectorLayer.call(this, scene);
  this.type = Q3D.LayerType.Point;
};

Q3D.PointLayer.prototype = Object.create(Q3D.VectorLayer.prototype);
Q3D.PointLayer.prototype.constructor = Q3D.PointLayer;

Q3D.PointLayer.prototype.loadJSONObject = function (jsonObject) {
  Q3D.VectorLayer.prototype.loadJSONObject.call(this, jsonObject);

  if (jsonObject.data !== undefined) {
    this.build(jsonObject.data.features);
  }
};

Q3D.PointLayer.prototype.build = function (features, startIndex) {
  var objType = this.properties.objType;
  if (objType == "Icon") { this.buildIcons(features, startIndex); return; }
  if (objType == "JSON model" || objType == "COLLADA model") { this.buildModels(features, startIndex); return; }

  var deg2rad = Math.PI / 180;
  var createGeometry, scaleZ = 1;
  if (objType == "Sphere") createGeometry = function (geom) { return new THREE.SphereGeometry(geom.r); };
  else if (objType == "Box") createGeometry = function (geom) { return new THREE.BoxGeometry(geom.w, geom.h, geom.d); };
  else if (objType == "Disk") {
    createGeometry = function (geom) {
      var geom = new THREE.CylinderGeometry(geom.r, geom.r, 0, 32), m = new THREE.Matrix4();
      if (90 - geom.d) geom.applyMatrix(m.makeRotationX((90 - geom.d) * deg2rad));
      if (geom.dd) geom.applyMatrix(m.makeRotationZ(-geom.dd * deg2rad));
      return geom;
    };
    if (this.ns === undefined || this.ns == false) scaleZ = this.scene.userData.zExaggeration;
  }
  else createGeometry = function (geom) { return new THREE.CylinderGeometry(geom.rt, geom.rb, geom.h); };   // Cylinder or Cone

  // each feature in this layer
  var materials = this.materials;
  for (var fid = startIndex || 0, flen = features.length; fid < flen; fid++) {
    var f = features[fid],
        geom = f.geom;
    f.objs = [];    // TODO
    var z_addend = (geom.h) ? geom.h / 2 : 0;
    for (var i = 0, l = geom.pts.length; i < l; i++) {
      var mesh = new THREE.Mesh(createGeometry(geom), materials.mat(f.mat));

      var pt = geom.pts[i];
      mesh.position.set(pt[0], pt[1], pt[2] + z_addend);
      if (geom.rotateX) mesh.rotation.x = geom.rotateX * deg2rad;
      if (scaleZ != 1) mesh.scale.z = scaleZ;
      mesh.userData.layerId = this.index;
      mesh.userData.featureId = fid;
      if (f.prop !== undefined) mesh.userData.properties = geom.prop;

      this.addObject(mesh);
      f.objs.push(mesh);
    }
  }
};

Q3D.PointLayer.prototype.buildIcons = function (features, startIndex) {
  // each feature in this layer
  for (var fid = startIndex || 0, flen = features.length; fid < flen; fid++) {
    var f = features[fid],
        geom = f.geom;
    var mat = this.materials.mat(f.mat);
    var image = this.scene.images[mat.i];   // TODO:

    // base size is 64 x 64
    var scale = (geom.scale === undefined) ? 1 : geom.scale;
    var sx = image.width / 64 * scale,
        sy = image.height / 64 * scale;

    f.objs = [];
    for (var i = 0, l = geom.pts.length; i < l; i++) {
      var pt = geom.pts[i];
      var sprite = new THREE.Sprite(mat);
      sprite.position.set(pt[0], pt[1], pt[2]);
      sprite.scale.set(sx, sy, scale);
      sprite.userData.layerId = this.index;
      sprite.userData.featureId = fid;
      // TODO: prop

      this.addObject(sprite);
      f.objs.push(sprite);
    }
  }
};

// TODO:
Q3D.PointLayer.prototype.buildModels = function (features, startIndex) {
  // each feature in this layer
  for (var fid = startIndex || 0, flen = features.length; fid < flen; fid++) {
    var f = features[fid];
    Q3D.application.modelBuilders[f.model_index].addFeature(this.index, fid);
  }
};

// TODO:
Q3D.PointLayer.prototype.buildLabels = function (parent, parentElement) {
  Q3D.VectorLayer.prototype.buildLabels.call(this, parent, parentElement, function (f) { return f.pts; });
};


/*
Q3D.LineLayer --> Q3D.VectorLayer
*/
Q3D.LineLayer = function (scene) {
  Q3D.VectorLayer.call(this, scene);
  this.type = Q3D.LayerType.Line;
};

Q3D.LineLayer.prototype = Object.create(Q3D.VectorLayer.prototype);
Q3D.LineLayer.prototype.constructor = Q3D.LineLayer;

Q3D.LineLayer.prototype.loadJSONObject = function (jsonObject) {
  Q3D.VectorLayer.prototype.loadJSONObject.call(this, jsonObject);

  if (jsonObject.data !== undefined) {
    this.build(jsonObject.data.features);
  }
};

Q3D.LineLayer.prototype.build = function (features, startIndex) {
  var objType = this.properties.objType,
      materials = this.materials,
      scene = this.scene;
  if (this.createObject !== undefined) {
    var createObject = this.createObject;
  }
  else if (objType == "Line") {
    var createObject = function (f, line) {
      var geom = new THREE.Geometry(), pt;
      for (var i = 0, l = line.length; i < l; i++) {
        pt = line[i];
        geom.vertices.push(new THREE.Vector3(pt[0], pt[1], pt[2]));
      }
      return new THREE.Line(geom, materials.mat(f.mat));
    };
  }
  else if (objType == "Pipe" || objType == "Cone") {
    var hasJoints = (objType == "Pipe");
    var createObject = function (f, line) {
      var group = new Q3D.Group();

      var pt0 = new THREE.Vector3(), pt1 = new THREE.Vector3(), sub = new THREE.Vector3();
      var geom, obj, pt;
      for (var i = 0, l = line.length; i < l; i++) {
        pt = line[i];
        pt1.set(pt[0], pt[1], pt[2]);

        if (hasJoints) {
          geom = new THREE.SphereGeometry(f.geom.rb, 8, 8);
          obj = new THREE.Mesh(geom, materials.mat(f.mat));
          obj.position.copy(pt1);
          group.add(obj);
        }

        if (i) {
          sub.subVectors(pt1, pt0);
          geom = new THREE.CylinderGeometry(f.geom.rt, f.geom.rb, pt0.distanceTo(pt1), 8);
          obj = new THREE.Mesh(geom, materials.mat(f.mat));
          obj.position.set((pt0.x + pt1.x) / 2, (pt0.y + pt1.y) / 2, (pt0.z + pt1.z) / 2);
          obj.rotation.set(Math.atan2(sub.z, Math.sqrt(sub.x * sub.x + sub.y * sub.y)), 0, Math.atan2(sub.y, sub.x) - Math.PI / 2, "ZXY");
          group.add(obj);
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

    var createObject = function (f, line) {
      var geometry = new THREE.Geometry(),
          group = new Q3D.Group();      // used in debug mode

      var geom, obj, dist, quat, rx, rz, wh4, vb4, vf4;
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
          obj = new THREE.Mesh(geom, materials.mat(f.mat));
          obj.position.set(ptM.x, ptM.y, ptM.z);
          obj.rotation.set(rx, 0, rz, "ZXY");
          group.add(obj);
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
      return new THREE.Mesh(geometry, materials.mat(f.mat));
    };
  }
  else if (objType == "Profile") {
    var relativeToDEM = (this.am == "relative"),    // altitude mode
        bRelativeToDEM = (this.bam == "relative"),  // altitude mode of bottom height
        dem = scene.mapLayers[0],   // TODO: referenced DEM layer
        z0 = scene.userData.zShift * scene.userData.zScale;

    var createObject = function (f, line) {
      var bzFunc, vertices;
      if (bRelativeToDEM) bzFunc = function (x, y) { return dem.getZ(x, y) + f.geom.bh; };
      else bzFunc = function (x, y) { return z0 + f.geom.bh; };

      if (relativeToDEM) {
        var zFunc = function (x, y) { return dem.getZ(x, y) + f.geom.h; };
        vertices = dem.segmentizeLineString(line, zFunc);   // line is list of 2D point [x, y]
      }
      else if (bRelativeToDEM) {
        vertices = dem.segmentizeLineString(line);          // line is list of 3D point [x, y, z]
      }
      else {    // both altitude modes are absolute
        var pt;
        vertices = [];
        for (var i = 0, l = line.length; i < l; i++) {
          pt = line[i];
          vertices.push(new THREE.Vector3(pt[0], pt[1], pt[2]));
        }
      }
      var geom = Q3D.Utils.createWallGeometry(vertices, bzFunc);    // TODO: flat shading
      return new THREE.Mesh(geom, materials.mat(f.mat));
    };
  }

  // each feature in this layer
  for (var fid = startIndex || 0, flen = features.length; fid < flen; fid++) {
    var f = features[fid],
        geom = f.geom;
    f.objs = [];
    for (var i = 0, l = geom.lines.length; i < l; i++) {
      var obj = createObject(f, geom.lines[i]);
      obj.userData.layerId = this.index;
      obj.userData.featureId = fid;
      // TODO: prop
      this.addObject(obj);
      f.objs.push(obj);   // TODO: remove?
    }
  }

  this.createObject = createObject;
};

Q3D.LineLayer.prototype.buildLabels = function (parent, parentElement) {
  // Line layer doesn't support label
  // Q3D.VectorLayer.prototype.buildLabels.call(this, parent, parentElement);
};


/*
Q3D.PolygonLayer --> Q3D.VectorLayer
*/
Q3D.PolygonLayer = function (scene) {
  Q3D.VectorLayer.call(this, scene);
  this.type = Q3D.LayerType.Polygon;

  // for overlay
  this.borderVisible = true;
  this.sideVisible = true;
};

Q3D.PolygonLayer.prototype = Object.create(Q3D.VectorLayer.prototype);
Q3D.PolygonLayer.prototype.constructor = Q3D.PolygonLayer;

Q3D.PolygonLayer.prototype.loadJSONObject = function (jsonObject) {
  Q3D.VectorLayer.prototype.loadJSONObject.call(this, jsonObject);

  if (jsonObject.data !== undefined) {
    this.build(jsonObject.data.features);
  }
};

Q3D.PolygonLayer.prototype.build = function (features, startIndex) {
  var materials = this.materials,
      scene = this.scene;

  if (this.createObject !== undefined) {
    var createObject = this.createObject;
  }
  else if (this.properties.objType == "Extruded") {
    var createSubObject = function (f, polygon, z) {
      var shape = new THREE.Shape(Q3D.Utils.arrayToVec2Array(polygon[0]));
      for (var i = 1, l = polygon.length; i < l; i++) {
        shape.holes.push(new THREE.Path(Q3D.Utils.arrayToVec2Array(polygon[i])));
      }
      var geom = new THREE.ExtrudeGeometry(shape, {bevelEnabled: false, amount: f.geom.h});
      var mesh = new THREE.Mesh(geom, materials.mat(f.mat));
      mesh.position.z = z;
      return mesh;
    };

    var createObject = function (f) {
      if (f.geom.polygons.length == 1) return createSubObject(f, f.geom.polygons[0], f.geom.zs[0]);

      var group = new Q3D.Group();
      for (var i = 0, l = f.geom.polygons.length; i < l; i++) {
        group.add(createSubObject(f, f.geom.polygons[i], f.geom.zs[i]));
      }
      return group;
    };
  }
  else {    // this.objType == "Overlay"
    var relativeToDEM = (this.am == "relative"),    // altitude mode
        sbRelativeToDEM = (this.sbm == "relative"), // altitude mode of bottom height of side
        dem = scene.mapLayers[0],    // TODO: referenced DEM layer
        z0 = scene.userData.zShift * scene.userData.zScale;

    var createObject = function (f) {
      var polygons = (relativeToDEM) ? (f.geom.split_polygons || []) : f.geom.polygons;

      var zFunc;
      if (relativeToDEM) zFunc = function (x, y) { return dem.getZ(x, y) + f.geom.h; };
      else zFunc = function (x, y) { return z0 + f.geom.h; };

      var geom = Q3D.Utils.createOverlayGeometry(f.geom.triangles, polygons, zFunc);

      // set UVs
      if (materials[f.mat].i !== undefined) Q3D.Utils.setGeometryUVs(geom, scene.userData.width, scene.userData.height);
      // TODO: materials.get(f.mat).origProp.i

      var mesh = new THREE.Mesh(geom, materials.mat(f.mat));

      // TODO: f.mb and f.ms
      if (f.mb === undefined && f.ms === undefined) return mesh;

      // borders and sides
      var bzFunc, geom, vertices;
      if (sbRelativeToDEM) bzFunc = function (x, y) { return dem.getZ(x, y) + f.geom.sb; };
      else bzFunc = function (x, y) { return z0 + f.geom.sb; };

      for (var i = 0, l = f.geom.polygons.length; i < l; i++) {
        var polygon = f.geom.polygons[i];
        for (var j = 0, m = polygon.length; j < m; j++) {
          if (relativeToDEM || sbRelativeToDEM) {
            vertices = dem.segmentizeLineString(polygon[j], zFunc);
          }
          else {
            vertices = Q3D.Utils.arrayToVec3Array(polygon[j], zFunc);
          }

          // TODO
          if (f.mb) {
            geom = new THREE.Geometry();
            geom.vertices = vertices;
            mesh.add(new THREE.Line(geom, materials.mat(f.mb)));
          }

          if (f.ms) {
            geom = Q3D.Utils.createWallGeometry(vertices, bzFunc);
            mesh.add(new THREE.Mesh(geom, materials.mat(f.ms)));
          }
        }
      }
      // TODO: mesh.updateWorldMatrix();
      return mesh;
    };
  }

  // each feature in this layer
  for (var fid = startIndex || 0, flen = features.length; fid < flen; fid++) {
    var f = features[fid];
    f.objs = [];
    var obj = createObject(f);
    obj.userData.layerId = this.index;
    obj.userData.featureId = fid;
    // TODO: prop
    this.addObject(obj);
    f.objs.push(obj);
  }

  this.createObject = createObject;
};

// TODO:
Q3D.PolygonLayer.prototype.buildLabels = function (parent, parentElement) {
  var zFunc, getPointsFunc = function (f) { return f.centroids; };
  var relativeToDEM = (this.am == "relative");    // altitude mode
  if (relativeToDEM) {
    var dem = this.scene.mapLayers[0];    // TODO: referenced dem
    zFunc = dem.getZ.bind(dem);
  }

  Q3D.VectorLayer.prototype.buildLabels.call(this, parent, parentElement, getPointsFunc, zFunc);
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

    // TODO: f, geom
    this.features.forEach(function (fet) {
      var layer = this.scene.mapLayers[fet.layerId],
          f = layer.f[fet.featureId];

      f.objs = [];
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

        mesh.userData.layerId = fet.layerId;
        mesh.userData.featureId = fet.featureId;

        layer.addObject(mesh);

        f.objs.push(mesh);
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

// [NOT USED]
Q3D.Utils.setObjectVisibility = function (object, visible) {
  object.traverse(function (obj) {
    obj.visible = visible;
  });
};

// TODO: REMOVE
Q3D.Utils.loadTexture = function (url, eventDispatcher) {
  return THREE.ImageUtils.loadTexture(url, undefined, function (tex) {
    if (eventDispatcher) eventDispatcher.dispatchEvent({type: "renderRequest"});
  });
};

// TODO: remove
Q3D.Utils.loadTextureBase64 = function (imageData, eventDispatcher) {
  var texture, image = new Image();
  image.onload = function () {
    texture.needsUpdate = true;
    if (eventDispatcher && !Q3D.Options.exportMode) eventDispatcher.dispatchEvent({type: "renderRequest"});
  };
  image.src = imageData;
  texture = new THREE.Texture(image);
  return texture;
};

// Put a stick to given position (for debug)
Q3D.Utils.putStick = function (x, y, zFunc, h) {
  if (Q3D.Utils._stick_mat === undefined) Q3D.Utils._stick_mat = new THREE.LineBasicMaterial({color: 0xff0000});
  if (h === undefined) h = 0.2;
  if (zFunc === undefined) {
    zFunc = function (x, y) { return Q3D.application.scene.mapLayers[0].getZ(x, y); }
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
  function toDMS (degrees) {
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
  var geom, pt, v;
  if (Q3D.Options.exportMode) {
    geom = new THREE.PlaneGeometry(0, 0, vertices.length - 1, 1);
    v = geom.vertices;
    for (var i = 0, l = vertices.length; i < l; i++) {
      pt = vertices[i];
      v[i].x = v[i + l].x = pt.x;
      v[i].y = v[i + l].y = pt.y;
      v[i].z = bzFunc(pt.x, pt.y);
      v[i + l].z = pt.z;
    }
  }
  else {
    geom = new THREE.PlaneBufferGeometry(0, 0, vertices.length - 1, 1);
    v = geom.attributes.position.array;
    for (var i = 0, k = 0, l = vertices.length, l3 = l * 3; i < l; i++, k+=3) {
      pt = vertices[i];
      v[k] = v[k + l3] = pt.x;
      v[k + 1] = v[k + l3 + 1] = pt.y;
      v[k + 2] = bzFunc(pt.x, pt.y);
      v[k + l3 + 2] = pt.z;
    }
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
  if (zFunc === undefined) zFunc = function () { return 0; };
  var pt, pts = [];
  for (var i = 0, l = points.length; i < l; i++) {
    pt = points[i];
    pts.push(new THREE.Vector3(pt[0], pt[1], zFunc(pt[0], pt[1])));
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
    var faces = THREE.Shape.Utils.triangulateShape(poly_geom.vertices, holes);

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
