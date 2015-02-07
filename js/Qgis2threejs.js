// Qgis2threejs.js
// (C) 2014 Minoru Akagi | MIT License
// https://github.com/minorua/Qgis2threejs

var Q3D = {VERSION: "1.0"};
Q3D.Options = {
  bgcolor: null,
  light: {
    directional: {
      azimuth: 220,   // note: default light azimuth of gdaldem hillshade is 315.
      altitude: 45    // altitude angle
    }
  },
  sole_height: 1.5,
  side: {color: 0xc7ac92},
  frame: {color: 0},
  label: {visible: true, connectorColor: 0xc0c0d0, autoSize: false, minFontSize: 10},
  qmarker: {r: 0.25, c: 0xffff00, o: 0.8},
  exportMode: false
};

Q3D.LayerType = {DEM: "dem", Point: "point", Line: "line", Polygon: "polygon"};
Q3D.MaterialType = {MeshLambert: 0, MeshPhong: 1, LineBasic: 2, Sprite: 3, MeshFace: 9};
Q3D.uv = {i: new THREE.Vector3(1, 0, 0), j: new THREE.Vector3(0, 1, 0), k: new THREE.Vector3(0, 0, 1)};
Q3D.projector = new THREE.Projector();

Q3D.ua = window.navigator.userAgent.toLowerCase();
Q3D.isIE = (Q3D.ua.indexOf("msie") != -1 || Q3D.ua.indexOf("trident") != -1);

Q3D.$ = function (elementId) {
  return document.getElementById(elementId);
};

/*
Q3D.Project - Project data holder

params: title, crs, baseExtent, width, zExaggeration, zShift, wgs84Center
*/
Q3D.Project = function (params) {
  for (var k in params) {
    this[k] = params[k];
  }

  this.height = this.width * (this.baseExtent[3] - this.baseExtent[1]) / (this.baseExtent[2] - this.baseExtent[0]);
  this.scale = this.width / (this.baseExtent[2] - this.baseExtent[0]);
  this.zScale = this.scale * this.zExaggeration;

  this.layers = [];
  this.jsons = [];
  this.images = [];
};

Q3D.Project.prototype = {

  constructor: Q3D.Project,

  addLayer: function (layer) {
    layer.index = this.layers.length;
    layer.project = this;
    this.layers.push(layer);
    return layer;
  },

  layerCount: function () {
    return this.layers.length;
  },

  getLayerByName: function (name) {
    for (var i = 0, l = this.layers.length; i < l; i++) {
      var layer = this.layers[i];
      if (layer.name == name) return layer;
    }
    return null;
  },

  toMapCoordinates: function (x, y, z) {
    return {x : (x + this.width / 2) / this.scale + this.baseExtent[0],
            y : (y + this.height / 2) / this.scale + this.baseExtent[1],
            z : z / this.zScale - this.zShift};
  }

  // buildCustomLights: function (parent) {},

  // buildCustomCamera: function () {}
};


/*
the application

limitations:
- one renderer
- one scene
*/
Q3D.application = {

  init: function (container) {
    this.container = container;
    this.running = false;

    // URL parameters
    this.urlParams = this.parseUrlParameters();
    if ("popup" in this.urlParams) {
      // open popup window
      var c = window.location.href.split("?");
      window.open(c[0] + "?" + c[1].replace(/&?popup/, ""), "popup", "width=" + this.urlParams.width + ",height=" + this.urlParams.height);
      this.popup.show("Another window has been opened.");
      return;
    }

    if (this.urlParams.width && this.urlParams.height) {
      // set container size
      container.style.width = this.urlParams.width + "px";
      container.style.height = this.urlParams.height + "px";
    }

    if (container.clientWidth && container.clientHeight) {
      this.width = container.clientWidth;
      this.height = container.clientHeight;
      this._fullWindow = false;
    } else {
      this.width = window.innerWidth;
      this.height = window.innerHeight;
      this._fullWindow = true;
    }

    // WebGLRenderer
    var bgcolor = Q3D.Options.bgcolor;
    this.renderer = new THREE.WebGLRenderer({alpha: (bgcolor === null)});
    this.renderer.setSize(this.width, this.height);
    this.renderer.setClearColor(bgcolor || 0, (bgcolor === null) ? 0 : 1);
    this.container.appendChild(this.renderer.domElement);

    // scene
    this.scene = new THREE.Scene();

    this.queryableObjects = [];

    // label
    this.labelConnectorGroup = new THREE.Object3D();
    this.labelVisibility = Q3D.Options.label.visible;
    this.labels = [];     // labels of visible layers

    // root element for labels
    var e = document.createElement("div");
    e.style.display = (this.labelVisibility) ? "block" : "none";
    this.container.appendChild(e);
    this.labelRootElement = e;

    this.jsonObjectBuilders = [];
    this._wireframeMode = false;
  },

  parseUrlParameters: function () {
    var p, vars = {};
    var params = window.location.search.substring(1).split('&').concat(window.location.hash.substring(1).split('&'));
    params.forEach(function (param) {
      p = param.split('=');
      vars[p[0]] = p[1];
    });
    return vars;
  },

  loadProject: function (project) {
    this.project = project;

    // light
    if (project.buildCustomLights) project.buildCustomLights(this.scene);
    else this.buildDefaultLights(this.scene);

    // camera
    if (project.buildCustomCamera) project.buildCustomCamera();
    else this.buildDefaultCamera();

    // controls
    if (Q3D.Controls) this.controls = Q3D.Controls.create(this.camera, this.renderer.domElement);

    // load JSON models
    if (project.jsons.length > 0) {
      this._jsonLoader = new THREE.JSONLoader(true);
      project.jsons.forEach(function (json, index) {
        this.jsonObjectBuilders[index] = new Q3D.JSONObjectBuilder(this._jsonLoader, this.project, json);
      }, this);
    }

    // build models
    project.layers.forEach(function (layer) {
      layer.initMaterials();
      layer.build(this.scene);
      if (layer.queryableObjects.length) this.queryableObjects = this.queryableObjects.concat(layer.queryableObjects);

      // build labels
      if (layer.l) {
        layer.buildLabels(this.labelConnectorGroup, this.labelRootElement);
        this.labels = this.labels.concat(layer.labels);
      }
    }, this);

    if (this.labels.length) this.scene.add(this.labelConnectorGroup);

    // restore view from URL parameters
    this._restoreViewFromUrl();

    // wireframe mode setting
    if ("wireframe" in this.urlParams) this.setWireframeMode(true);

    // create a marker for queried point
    var opt = Q3D.Options.qmarker;
    this.queryMarker = new THREE.Mesh(new THREE.SphereGeometry(opt.r),
                                      new THREE.MeshLambertMaterial({color: opt.c, ambient: opt.c, opacity: opt.o, transparent: (opt.o < 1)}));
    this.queryMarker.visible = false;
    this.scene.add(this.queryMarker);

    this.highlightMaterial = new THREE.MeshLambertMaterial({emissive: 0x666600});

    this.selectedLayerId = null;
    this.selectedFeatureId = null;
    this._originalMaterial = null;
  },

  addEventListeners: function () {
    window.addEventListener("keydown", this.eventListener.keydown.bind(this));
    window.addEventListener("resize", this.eventListener.resize.bind(this));

    var e = Q3D.$("closebtn");
    if (e) e.addEventListener("click", this.closePopup.bind(this));
  },

  eventListener: {

    keydown: function (e) {
      if (e.ctrlKey || e.altKey) return;
      var keyPressed = e.which;
      if (!e.shiftKey) {
        if (keyPressed == 27) this.closePopup(); // ESC
        else if (keyPressed == 73) this.showInfo();  // I
        else if (keyPressed == 76) this.setLabelVisibility(!this.labelVisibility);  // L
        else if (keyPressed == 87) this.setWireframeMode(!this._wireframeMode);    // W
      }
      else {
        if (keyPressed == 82) this.controls.reset();   // Shift + R
        else if (keyPressed == 83) this.saveCanvasImage();    // Shift + S
      }
    },

    resize: function () {
      if (!this._fullWindow) return;

      this.width = window.innerWidth;
      this.height = window.innerHeight;
      this.camera.aspect = this.width / this.height;
      this.camera.updateProjectionMatrix();
      this.renderer.setSize(this.width, this.height);
    }

  },

  buildDefaultLights: function (parent) {
    var deg2rad = Math.PI / 180;

    // ambient light
    parent.add(new THREE.AmbientLight(0x999999));

    // directional lights
    var opt = Q3D.Options.light.directional;
    var lambda = (90 - opt.azimuth) * deg2rad;
    var phi = opt.altitude * deg2rad;

    var x = Math.cos(phi) * Math.cos(lambda),
        y = Math.cos(phi) * Math.sin(lambda),
        z = Math.sin(phi);

    var light1 = new THREE.DirectionalLight(0xffffff, 0.5);
    light1.position.set(x, y, z);
    parent.add(light1);

    // thin light from the opposite direction
    var light2 = new THREE.DirectionalLight(0xffffff, 0.1);
    light2.position.set(-x, -y, -z);
    parent.add(light2);
  },

  buildDefaultCamera: function () {
    this.camera = new THREE.PerspectiveCamera(45, this.width / this.height, 0.1, 1000);
    this.camera.position.set(0, -100, 100);
  },

  currentViewUrl: function () {
    var controls = this.controls;
    var c = controls.object.position, t = controls.target, u = controls.object.up;
    var hash = "#cx=" + c.x + "&cy=" + c.y + "&cz=" + c.z;
    if (t.x || t.y || t.z) hash += "&tx=" + t.x + "&ty=" + t.y + "&tz=" + t.z;
    if (u.x || u.y || u.z != 1) hash += "&ux=" + u.x + "&uy=" + u.y + "&uz=" + u.z;
    return window.location.href.split("#")[0] + hash;
  },

  // Restore camera position and target position
  _restoreViewFromUrl: function () {
    var vars = this.urlParams;
    if (vars.tx !== undefined) this.controls.target.set(vars.tx, vars.ty, vars.tz);
    if (vars.cx !== undefined) this.controls.object.position.set(vars.cx, vars.cy, vars.cz);
    if (vars.ux !== undefined) this.controls.object.up.set(vars.ux, vars.uy, vars.uz);
  },

  // start rendering loop
  start: function () {
    this.running = true;
    this.animate();
  },

  stop: function () {
    this.running = false;
  },

  // animation loop
  animate: function () {
    if (this.running) requestAnimationFrame(this.animate.bind(this));
    if (this.controls) this.controls.update();
    this.render();
  },

  render: function () {
    this.renderer.render(this.scene, this.camera);
    this.updateLabelPosition();
  },

  // update label position
  updateLabelPosition: function () {
    if (!this.labelVisibility || this.labels.length == 0) return;

    var widthHalf = this.width / 2, heightHalf = this.height / 2;
    var autosize = Q3D.Options.label.autoSize;
    var camera = this.camera;
    var c2t = this.controls.target.clone().sub(camera.position);
    var c2l = new THREE.Vector3();
    var v = new THREE.Vector3();

    // make a list of [label index, distance to camera]
    var idx_dist = [];
    for (var i = 0, l = this.labels.length; i < l; i++) {
      idx_dist.push([i, camera.position.distanceTo(this.labels[i].pt)]);
    }

    // sort label indexes in descending order of distances
    idx_dist.sort(function (a, b) {
      if (a[1] < b[1]) return 1;
      if (a[1] > b[1]) return -1;
      return 0;
    });

    var label, e, x, y, dist, fontSize;
    var minFontSize = Q3D.Options.label.minFontSize;
    for (var i = 0, l = this.labels.length; i < l; i++) {
      label = this.labels[idx_dist[i][0]];
      e = label.e;
      if (c2l.subVectors(label.pt, camera.position).dot(c2t) > 0) {
        // label is in front
        // calculate label position
        Q3D.projector.projectVector(v.copy(label.pt), camera);
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
  },

  labelVisibilityChanged: function () {
    this.labels = [];
    this.project.layers.forEach(function (layer) {
      if (!layer.l) return;
      this.labels = this.labels.concat(layer.labels);
    }, this);
  },

  setLabelVisibility: function (visible) {
    this.labelVisibility = visible;
    if (this.labels.length == 0) return;

    this.labelRootElement.style.display = (visible) ? "block" : "none";
    this.labelConnectorGroup.visible = visible;
    this.labelConnectorGroup.children.forEach(function (group) {
      var layer = this.project.layers[group.userData.layerId];
      if (!layer.visible && visible) return;
      Q3D.Utils.setObjectVisibility(group, visible);
    }, this);

    this.render();
  },

  setWireframeMode: function (wireframe) {
    if (wireframe == this._wireframeMode) return;

    this.project.layers.forEach(function (layer) {
      layer.setWireframeMode(wireframe);
    });

    this._wireframeMode = wireframe;
  },

  intersectObjects: function (offsetX, offsetY) {
    var x = (offsetX / this.width) * 2 - 1;
    var y = -(offsetY / this.height) * 2 + 1;
    var vector = new THREE.Vector3(x, y, 1);
    Q3D.projector.unprojectVector(vector, this.camera);
    var ray = new THREE.Raycaster(this.camera.position, vector.sub(this.camera.position).normalize());
    return ray.intersectObjects(this.queryableObjects);
  },

  _offset: function (elm) {
    var top = 0, left = 0;
    do {
      top += elm.offsetTop || 0; left += elm.offsetLeft || 0; elm = elm.offsetParent;
    } while (elm);
    return {top: top, left: left};
  },

  help: function () {
    var lines = (Q3D.Controls === undefined) ? [] : Q3D.Controls.keyList;
    if (lines.indexOf("* Keys") == -1) lines.push("* Keys");
    lines = lines.concat([
      "I : Show Information About Page",
      "L : Toggle Label Visibility",
      "W : Wireframe Mode",
      "Shift + R : Reset View",
      "Shift + S : Save Image As File"
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
  },

  popup: {

    show: function (html) {
      if (html === undefined) {
        // show page info
        Q3D.$("popupcontent").style.display = "none";
        Q3D.$("pageinfo").style.display = "block";
      }
      else {
        Q3D.$("pageinfo").style.display = "none";
        Q3D.$("popupcontent").style.display = "block";
        Q3D.$("popupcontent").innerHTML = html;
      }
      Q3D.$("popup").style.display = "block";
    },

    hide: function () {
      Q3D.$("popup").style.display = "none";
    }

  },

  showInfo: function () {
    Q3D.$("urlbox").value = this.currentViewUrl();
    Q3D.$("usage").innerHTML = this.help();
    this.popup.show();
  },

  showQueryResult: function (obj) {
    var userData = obj.object.userData, layer, r = [];
    if (userData.layerId !== undefined) {
      // layer name
      layer = this.project.layers[userData.layerId];
      r.push('<table class="layer">');
      r.push("<caption>Layer name</caption>");
      r.push("<tr><td>" + layer.name + "</td></tr>");
      r.push("</table>");
    }

    // clicked coordinates
    var pt = this.project.toMapCoordinates(obj.point.x, obj.point.y, obj.point.z);
    r.push('<table class="coords">');
    r.push("<caption>Clicked coordinates</caption>");
    r.push("<tr><td>");

    if (typeof proj4 === "undefined") r.push([pt.x.toFixed(2), pt.y.toFixed(2), pt.z.toFixed(2)].join(", "));
    else {
      var lonLat = proj4(this.project.proj).inverse([pt.x, pt.y]);
      r.push(Q3D.Utils.convertToDMS(lonLat[1], lonLat[0]) + ", Elev. " + pt.z.toFixed(2));
    }

    r.push("</td></tr></table>");

    if (userData.layerId !== undefined && userData.featureId !== undefined && layer.a !== undefined) {
      // attributes
      r.push('<table class="attrs">');
      r.push("<caption>Attributes</caption>");
      var f = layer.f[userData.featureId];
      for (var i = 0, l = layer.a.length; i < l; i++) {
        r.push("<tr><td>" + layer.a[i] + "</td><td>" + f.a[i] + "</td></tr>");
      }
      r.push("</table>");
    }
    this.popup.show(r.join(""));
  },

  closePopup: function () {
    this.popup.hide();
    this.queryMarker.visible = false;
    this.highlightFeature(null, null);
    if (this._canvasImageUrl) {
      URL.revokeObjectURL(this._canvasImageUrl);
      this._canvasImageUrl = null;
    }
  },

  highlightFeature: function (layerId, featureId) {
    if (this.selectedLayerId !== null && this.selectedFeatureId !== null) {
      var f = this.project.layers[this.selectedLayerId].f[this.selectedFeatureId];
      var orig_mat = this._originalMaterial;
      var setMaterial = function (obj) {
        obj.material = orig_mat;
      };
      for (var i = 0, l = f.objs.length; i < l; i++) {
        f.objs[i].traverse(setMaterial);
      }
      this.selectedLayerId = null;
      this.selectedFeatureId = null;
      this._originalMaterial = null;
    }

    if (layerId === null || featureId === null) return;

    var layer = this.project.layers[layerId];
    if (layer === undefined) return;
    if (layer.objType == "Icon" || layer.objType == "JSON model") return;

    var f = layer.f[featureId];
    if (f === undefined || f.objs.length == 0) return;

    this._originalMaterial = layer.materials[f.m].m;
    var high_mat = this.highlightMaterial;
    high_mat.color = layer.materials[f.m].m.color;
    //high_mat.ambient = layer.materials[f.m].m.ambient;
    var setMaterial = function (obj) {
      obj.material = high_mat;
    };
    for (var i = 0, l = f.objs.length; i < l; i++) {
      f.objs[i].traverse(setMaterial);
    }
    this.selectedLayerId = layerId;
    this.selectedFeatureId = featureId;
  },

  // Called from *Controls.js when canvas is clicked
  canvasClicked: function (e) {
    var canvasOffset = this._offset(this.renderer.domElement);
    var objs = this.intersectObjects(e.clientX - canvasOffset.left, e.clientY - canvasOffset.top);

    for (var i = 0, l = objs.length; i < l; i++) {
      var obj = objs[i];
      if (obj.object.visible) {
        // query marker
        this.queryMarker.position.set(obj.point.x, obj.point.y, obj.point.z);
        this.queryMarker.visible = true;

        // highlight clicked object
        var userData = obj.object.userData;
        this.highlightFeature((userData.layerId === undefined) ? null : userData.layerId,
                              (userData.featureId === undefined) ? null : userData.featureId);

        this.showQueryResult(obj);
        return;
      }
    }
    this.closePopup();
  },

  // limitations:
  // - background of image is white if background is sky-like
  // - labels are not rendered
  saveCanvasImage: function () {
    function saveBlob (blob) {
      var filename = "image.png";

      // ie
      if (window.navigator.msSaveBlob !== undefined) {
        window.navigator.msSaveBlob(blob, filename);
        return;
      }

      // create object url
      if (this._canvasImageUrl) URL.revokeObjectURL(this._canvasImageUrl);
      this._canvasImageUrl = URL.createObjectURL(blob);

      // display a link to save the image
      var e = document.createElement("a");
      e.className = "download-link";
      e.href = this._canvasImageUrl;
      e.download = filename;
      e.innerHTML = "Click here to save the image";
      this.popup.show(e.outerHTML);
    }

    // render for canvas.toDataURL()
    this.renderer.preserveDrawingBuffer = true;
    this.render();

    // to blob
    var canvas = this.renderer.domElement;
    if (canvas.toBlob !== undefined) {
      canvas.toBlob(saveBlob.bind(this));
    }
    else {    // !HTMLCanvasElement.prototype.toBlob
      // https://developer.mozilla.org/en-US/docs/Web/API/HTMLCanvasElement.toBlob
      var binStr = atob(canvas.toDataURL("image/png").split(',')[1]),
          len = binStr.length,
          arr = new Uint8Array(len);

      for (var i = 0; i < len; i++) {
        arr[i] = binStr.charCodeAt(i);
      }

      saveBlob.call(this, new Blob([arr], {type: "image/png"}));
    }
  }

};


/*
Q3D.DEMBlock
*/
Q3D.DEMBlock = function (params) {
  for (var k in params) {
    this[k] = params[k];
  }
  this.aObjs = [];
};

Q3D.DEMBlock.prototype = {

  constructor: Q3D.DEMBlock,

  build: function (layer) {
    var geom = new THREE.PlaneGeometry(this.plane.width, this.plane.height,
                                       this.width - 1, this.height - 1);

    // Filling of the DEM plane
    for (var i = 0, l = geom.vertices.length; i < l; i++) {
      geom.vertices[i].z = this.data[i];
    }

    // Calculate normals
    if (this.shading) {
      geom.computeFaceNormals();
      geom.computeVertexNormals();
    }

    var mesh = new THREE.Mesh(geom, layer.materials[this.m].m);
    if (this.plane.offsetX != 0) mesh.position.x = this.plane.offsetX;
    if (this.plane.offsetY != 0) mesh.position.y = this.plane.offsetY;
    mesh.userData.layerId = layer.index;
    this.obj = mesh;
    layer.addObject(mesh);
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
Q3D.MapLayer = function (params) {

  this.visible = true;
  this.opacity = 1;

  this.m = [];
  for (var k in params) {
    this[k] = params[k];
  }

  // this.materials = undefined;
  this.objectGroup = new THREE.Object3D();
  this.queryableObjects = [];

};

Q3D.MapLayer.prototype = {

  constructor: Q3D.MapLayer,

  addObject: function (object, queryable) {
    if (queryable === undefined) queryable = this.q;

    this.objectGroup.add(object);
    if (queryable) this._addQueryableObject(object);
  },

  _addQueryableObject: function (object) {
    this.queryableObjects.push(object);
    for (var i = 0, l = object.children.length; i < l; i++) {
      this._addQueryableObject(object.children[i]);
    }
  },

  initMaterials: function () {
    this.materials = [];
    if (this.m.length == 0) return;

    var mat, sum_opacity = 0;
    for (var i = 0, l = this.m.length; i < l; i++) {
      var m = this.m[i];

      var opt = {};
      if (m.ds && !Q3D.isIE) opt.side = THREE.DoubleSide;    // Shader compilation error occurs with double sided material on IE11
      if (m.flat) opt.shading = THREE.FlatShading;
      if (m.i !== undefined) {
        var image = this.project.images[m.i];
        if (image.texture === undefined) {
          if (image.src !== undefined) image.texture = THREE.ImageUtils.loadTexture(image.src);
          else image.texture = Q3D.Utils.loadTextureData(image.data);
        }
        opt.map = image.texture;
      }
      if (m.o !== undefined && m.o < 1) {
        opt.opacity = m.o;
        opt.transparent = true;
      }
      if (m.t) opt.transparent = true;
      if (m.w) opt.wireframe = true;

      if (m.type == Q3D.MaterialType.MeshLambert) {
        if (m.c !== undefined) opt.color = opt.ambient = m.c;
        mat = new THREE.MeshLambertMaterial(opt);
      }
      else if (m.type == Q3D.MaterialType.MeshPhong) {
        if (m.c !== undefined) opt.color = opt.ambient = m.c;
        mat = new THREE.MeshPhongMaterial(opt);
      }
      else if (m.type == Q3D.MaterialType.LineBasic) {
        opt.color = m.c;
        mat = new THREE.LineBasicMaterial(opt);
      }
      else {
        opt.color = 0xffffff;
        mat = new THREE.SpriteMaterial(opt);
      }

      m.m = mat;
      this.materials.push(m);
      sum_opacity += mat.opacity;
    }

    // layer opacity is the average opacity of materials
    this.opacity = sum_opacity / this.materials.length;
  },

  setOpacity: function (opacity) {
    this.opacity = opacity;
    this.materials.forEach(function (m) {
      if (m.type == Q3D.MaterialType.MeshFace) {
        var materials = m.m.materials;
        for (var i = 0, l = materials.length; i < l; i++) {
          materials[i].transparent = Boolean(m.t) || (opacity < 1);
          materials[i].opacity = opacity;
        }
      }
      else {
        m.m.transparent = Boolean(m.t) || (opacity < 1);
        m.m.opacity = opacity;
      }
    });
  },

  setVisible: function (visible) {
    this.visible = visible;
    Q3D.Utils.setObjectVisibility(this.objectGroup, visible);
  },

  setWireframeMode: function (wireframe) {
    this.materials.forEach(function (m) {
      if (m.w) return;
      if (m.type == Q3D.MaterialType.MeshFace) {
        var materials = m.m.materials;
        for (var i = 0, l = materials.length; i < l; i++) {
          materials[i].wireframe = wireframe;
        }
      }
      else if (m.type != Q3D.MaterialType.LineBasic) m.m.wireframe = wireframe;
    });
  }

};

/*
Q3D.MapLayer.prototype.build = function (parent) {};
Q3D.MapLayer.prototype.meshes = function () {};
*/


/*
Q3D.DEMLayer --> Q3D.MapLayer
*/
Q3D.DEMLayer = function (params) {
  Q3D.MapLayer.call(this, params);
  this.type = Q3D.LayerType.DEM;
  this.blocks = [];
};

Q3D.DEMLayer.prototype = Object.create(Q3D.MapLayer.prototype);

Q3D.DEMLayer.prototype.addBlock = function (params) {
  var block = new Q3D.DEMBlock(params);
  this.blocks.push(block);
  return block;
};

Q3D.DEMLayer.prototype.build = function (parent) {
  var opt = Q3D.Options;
  this.blocks.forEach(function (block) {
    block.build(this);

    // Build sides, bottom and frame
    if (block.s) {
      this.buildSides(block, opt.side.color, opt.sole_height);
      this.sideVisible = true;
    }
    if (block.frame) {
      this.buildFrame(block, opt.frame.color, opt.sole_height);
      this.sideVisible = true;
    }
  }, this);

  if (parent) parent.add(this.objectGroup);
};

// Creates sides and bottom of the DEM to give an impression of "extruding" and increase the 3D aspect.
Q3D.DEMLayer.prototype.buildSides = function (block, color, sole_height) {
  var dem = block;

  // Material
  var opacity = this.materials[block.m].o;
  if (opacity === undefined) opacity = 1;
  var mat = new THREE.MeshLambertMaterial({color: color,
                                           ambient: color,
                                           opacity: opacity,
                                           transparent: (opacity < 1)});
  this.materials.push({type: Q3D.MaterialType.MeshLambert, m: mat});

  // Sides
  var w = dem.width, h = dem.height, HALF_PI = Math.PI / 2;
  var i, geom, mesh;

  // front
  geom = new THREE.PlaneGeometry(dem.plane.width, 2 * sole_height, w - 1, 1);
  for (i = 0; i < w; i++) {
    geom.vertices[i].y = dem.data[w * (h - 1) + i];
  }
  mesh = new THREE.Mesh(geom, mat);
  mesh.position.y = -dem.plane.height / 2;
  mesh.rotateOnAxis(Q3D.uv.i, HALF_PI);
  this.addObject(mesh, false);
  dem.aObjs.push(mesh);

  // back
  geom = new THREE.PlaneGeometry(dem.plane.width, 2 * sole_height, w - 1, 1);
  for (i = 0; i < w; i++) {
    geom.vertices[i].y = dem.data[w - 1 - i];
  }
  mesh = new THREE.Mesh(geom, mat);
  mesh.position.y = dem.plane.height / 2;
  mesh.rotateOnAxis(Q3D.uv.k, Math.PI);
  mesh.rotateOnAxis(Q3D.uv.i, HALF_PI);
  this.addObject(mesh, false);
  dem.aObjs.push(mesh);

  // left
  geom = new THREE.PlaneGeometry(2 * sole_height, dem.plane.height, 1, h - 1);
  for (i = 0; i < h; i++) {
    geom.vertices[i * 2 + 1].x = dem.data[w * i];
  }
  mesh = new THREE.Mesh(geom, mat);
  mesh.position.x = -dem.plane.width / 2;
  mesh.rotateOnAxis(Q3D.uv.j, -HALF_PI);
  this.addObject(mesh, false);
  dem.aObjs.push(mesh);

  // right
  geom = new THREE.PlaneGeometry(2 * sole_height, dem.plane.height, 1, h - 1);
  for (i = 0; i < h; i++) {
    geom.vertices[i * 2].x = -dem.data[w * (i + 1) - 1];
  }
  mesh = new THREE.Mesh(geom, mat);
  mesh.position.x = dem.plane.width / 2;
  mesh.rotateOnAxis(Q3D.uv.j, HALF_PI);
  this.addObject(mesh, false);
  dem.aObjs.push(mesh);

  // Bottom
  if (Q3D.Options.exportMode) {
    geom = new THREE.PlaneGeometry(dem.plane.width, dem.plane.height, w - 1, h - 1);
  }
  else {
    geom = new THREE.PlaneGeometry(dem.plane.width, dem.plane.height, 1, 1);
  }
  mesh = new THREE.Mesh(geom, mat);
  mesh.position.z = -sole_height;
  mesh.rotateOnAxis(Q3D.uv.i, Math.PI);
  this.addObject(mesh, false);
  dem.aObjs.push(mesh);
};

Q3D.DEMLayer.prototype.buildFrame = function (block, color, sole_height) {
  var dem = block;
  var opacity = this.materials[block.m].o;
  if (opacity === undefined) opacity = 1;
  var mat = new THREE.LineBasicMaterial({color: color,
                                         opacity: opacity,
                                         transparent: (opacity < 1)});
  this.materials.push({type: Q3D.MaterialType.LineBasic, m: mat});

  // horizontal rectangle at bottom
  var hw = dem.plane.width / 2, hh = dem.plane.height / 2, z = -sole_height;
  var geom = new THREE.Geometry();
  geom.vertices.push(new THREE.Vector3(-hw, -hh, z),
                     new THREE.Vector3(hw, -hh, z),
                     new THREE.Vector3(hw, hh, z),
                     new THREE.Vector3(-hw, hh, z),
                     new THREE.Vector3(-hw, -hh, z));

  var obj = new THREE.Line(geom, mat);
  this.addObject(obj, false);
  dem.aObjs.push(obj);

  // vertical lines at corners
  var pts = [[-hw, -hh, dem.data[dem.data.length - dem.width]],
             [hw, -hh, dem.data[dem.data.length - 1]],
             [hw, hh, dem.data[dem.width - 1]],
             [-hw, hh, dem.data[0]]];
  pts.forEach(function (pt) {
    var geom = new THREE.Geometry();
    geom.vertices.push(new THREE.Vector3(pt[0], pt[1], pt[2]),
                       new THREE.Vector3(pt[0], pt[1], z));

    var obj = new THREE.Line(geom, mat);
    this.addObject(obj, false);
    dem.aObjs.push(obj);
  }, this);
};

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
  var xmin = -this.project.width / 2,
      ymax = this.project.height / 2;

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
  var width = this.project.width, height = this.project.height;
  var xmin = -width / 2, ymax = height / 2;
  var block = this.blocks[0];
  var x_segments = block.width - 1,
      y_segments = block.height - 1;
  var ix = width / x_segments,
      iy = height / y_segments;

  var pts = [];
  for (var i = 1, l = lineString.length; i < l; i++) {
    var pt1 = lineString[i - 1], pt2 = lineString[i];
    var x1 = pt1[0], x2 = pt2[0], y1 = pt1[1], y2 = pt2[1];
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

    var x, y, lp = null;
    for (var j = 0, m = p.length; j < m; j++) {
      if (lp === p[j]) continue;
      if (p[j] == 1) break;

      x = x1 + (x2 - x1) * p[j];
      y = y1 + (y2 - y1) * p[j];
      pts.push(new THREE.Vector3(x, y, zFunc(x, y)));
      // Q3D.Utils.putStick(x, y, zFunc);

      lp = p[j];
    }
  }
  // last point (= the first point)
  var pt = lineString[lineString.length - 1];
  pts.push(new THREE.Vector3(pt[0], pt[1], zFunc(pt[0], pt[1])));

  /*
  for (var i = 0, l = lineString.length - 1; i < l; i++) {
    Q3D.Utils.putStick(lineString[i][0], lineString[i][1], zFunc, 0.8);
  }
  */

  return pts;
};

Q3D.DEMLayer.prototype.setVisible = function (visible) {
  Q3D.MapLayer.prototype.setVisible.call(this, visible);
  if (visible && this.sideVisible === false) this.setSideVisibility(false);
};

Q3D.DEMLayer.prototype.setSideVisibility = function (visible) {
  this.sideVisible = visible;
  this.blocks[0].aObjs.forEach(function (obj) {
    obj.visible = visible;
  });
};


/*
Q3D.VectorLayer --> Q3D.MapLayer
*/
Q3D.VectorLayer = function (params) {
  this.f = [];
  Q3D.MapLayer.call(this, params);

  this.labels = [];
};

Q3D.VectorLayer.prototype = Object.create(Q3D.MapLayer.prototype);

Q3D.VectorLayer.prototype.build = function (parent) {};

Q3D.VectorLayer.prototype.buildLabels = function (parent, parentElement, getPointsFunc, zFunc) {
  // Layer must belong to a project
  var label = this.l;
  if (label === undefined || this.project === undefined || getPointsFunc === undefined) return;

  // function to get height for both ends of label connector
  // label.ht
  //  1: fixed height
  //  2: height from point (bottom height if extruded polygon, elevation at centroid of polygon if overlay)
  //  3: height from top of extruded polygon / from overlay
  //  >= 100: data-defined + addend
  var zShift = this.project.zShift, zScale = this.project.zScale;
  var labelHeightFunc = function (f, pt) {
    var z0 = (zFunc === undefined) ? pt[2] : zFunc(pt[0], pt[1]);

    if (label.ht == 1) return [z0, label.v];
    if (label.ht >= 100) return [z0, (f.a[label.ht - 100] + zShift) * zScale + label.v];

    if (label.ht == 3) z0 += f.h;
    return [z0, z0 + label.v];
  };

  var line_mat = new THREE.LineBasicMaterial({color: Q3D.Options.label.connectorColor});
  this.labelConnectorGroup = new THREE.Object3D();
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
  if (this.labelConnectorGroup.parent.visible) {
    Q3D.Utils.setObjectVisibility(this.labelConnectorGroup, visible);
  }
  Q3D.application.labelVisibilityChanged();
};


/*
Q3D.PointLayer --> Q3D.VectorLayer
*/
Q3D.PointLayer = function (params) {
  Q3D.VectorLayer.call(this, params);
  this.type = Q3D.LayerType.Point;
};

Q3D.PointLayer.prototype = Object.create(Q3D.VectorLayer.prototype);

Q3D.PointLayer.prototype.build = function (parent) {
  if (this.objType == "Icon") { this.buildIcons(parent); return; }
  if (this.objType == "JSON model") { this.buildJSONModels(parent); return; }

  var materials = this.materials;
  var deg2rad = Math.PI / 180;
  var createGeometry, scaleZ = 1;
  if (this.objType == "Sphere") createGeometry = function (f) { return new THREE.SphereGeometry(f.r); };
  else if (this.objType == "Cube") createGeometry = function (f) { return new THREE.CubeGeometry(f.w, f.h, f.d); };
  else if (this.objType == "Disk") {
    createGeometry = function (f) {
      var geom = new THREE.CylinderGeometry(f.r, f.r, 0, 32), m = new THREE.Matrix4();
      if (90 - f.d) geom.applyMatrix(m.makeRotationX((90 - f.d) * deg2rad));
      if (f.dd) geom.applyMatrix(m.makeRotationZ(-f.dd * deg2rad));
      return geom;
    };
    if (this.ns === undefined || this.ns == false) scaleZ = this.project.zExaggeration;
  }
  else createGeometry = function (f) { return new THREE.CylinderGeometry(f.rt, f.rb, f.h); };   // Cylinder or Cone

  // each feature in this layer
  this.f.forEach(function (f, fid) {
    f.objs = [];
    var z_addend = (f.h) ? f.h / 2 : 0;
    for (var i = 0, l = f.pts.length; i < l; i++) {
      var mesh = new THREE.Mesh(createGeometry(f), materials[f.m].m);

      var pt = f.pts[i];
      mesh.position.set(pt[0], pt[1], pt[2] + z_addend);
      if (f.rotateX) mesh.rotation.x = f.rotateX * deg2rad;
      if (scaleZ != 1) mesh.scale.z = scaleZ;
      mesh.userData.layerId = this.index;
      mesh.userData.featureId = fid;

      this.addObject(mesh);
      f.objs.push(mesh);
    }
  }, this);

  if (parent) parent.add(this.objectGroup);
};

Q3D.PointLayer.prototype.buildIcons = function (parent) {
  // each feature in this layer
  this.f.forEach(function (f, fid) {
    var mat = this.materials[f.m];
    var image = this.project.images[mat.i];

    // base size is 64 x 64
    var scale = (f.scale === undefined) ? 1 : f.scale;
    var sx = image.width / 64 * scale,
        sy = image.height / 64 * scale;

    f.objs = [];
    for (var i = 0, l = f.pts.length; i < l; i++) {
      var pt = f.pts[i];
      var sprite = new THREE.Sprite(mat.m);
      sprite.position.set(pt[0], pt[1], pt[2]);
      sprite.scale.set(sx, sy, scale);
      sprite.userData.layerId = this.index;
      sprite.userData.featureId = fid;

      this.addObject(sprite);
      f.objs.push(sprite);
    }
  }, this);

  if (parent) parent.add(this.objectGroup);
};

Q3D.PointLayer.prototype.buildJSONModels = function (parent) {
  // each feature in this layer
  this.f.forEach(function (f, fid) {
    Q3D.application.jsonObjectBuilders[f.json_index].addFeature(this.index, fid);
  }, this);

  if (parent) parent.add(this.objectGroup);
};

Q3D.PointLayer.prototype.buildLabels = function (parent, parentElement) {
  Q3D.VectorLayer.prototype.buildLabels.call(this, parent, parentElement, function (f) { return f.pts; });
};


/*
Q3D.LineLayer --> Q3D.VectorLayer
*/
Q3D.LineLayer = function (params) {
  Q3D.VectorLayer.call(this, params);
  this.type = Q3D.LayerType.Line;
};

Q3D.LineLayer.prototype = Object.create(Q3D.VectorLayer.prototype);

Q3D.LineLayer.prototype.build = function (parent) {
  var materials = this.materials;
  var pt;
  if (this.objType == "Line") {
    var createObject = function (f, line, userData) {
      var geom = new THREE.Geometry();
      for (var i = 0, l = line.length; i < l; i++) {
        pt = line[i];
        geom.vertices.push(new THREE.Vector3(pt[0], pt[1], pt[2]));
      }
      var line = new THREE.Line(geom, materials[f.m].m);
      line.userData = userData;
      return line;
    };
  }
  else if (this.objType == "Pipe" || this.objType == "Cone") {
    var hasJoints = (this.objType == "Pipe");
    var createObject = function (f, line, userData) {
      var group = new THREE.Object3D();
      group.userData = userData;

      var pt0 = new THREE.Vector3(), pt1 = new THREE.Vector3(), sub = new THREE.Vector3();
      var geom, obj;
      for (var i = 0, l = line.length; i < l; i++) {
        pt = line[i];
        pt1.set(pt[0], pt[1], pt[2]);

        if (hasJoints) {
          geom = new THREE.SphereGeometry(f.rb);
          obj = new THREE.Mesh(geom, materials[f.m].m);
          obj.position.copy(pt1);
          obj.userData = userData;
          group.add(obj);
        }

        if (i) {
          sub.subVectors(pt1, pt0);
          geom = new THREE.CylinderGeometry(f.rt, f.rb, pt0.distanceTo(pt1));
          obj = new THREE.Mesh(geom, materials[f.m].m);
          obj.position.set((pt0.x + pt1.x) / 2, (pt0.y + pt1.y) / 2, (pt0.z + pt1.z) / 2);
          obj.rotation.set(Math.atan2(sub.z, Math.sqrt(sub.x * sub.x + sub.y * sub.y)), 0, Math.atan2(sub.y, sub.x) - Math.PI / 2, "ZXY");
          obj.userData = userData;
          group.add(obj);
        }
        pt0.copy(pt1);
      }
      return group;
    };
  }
  else if (this.objType == "Profile") {
    var z0 = this.project.zShift * this.project.zScale;
    var createObject = function (f, line, userData) {
      var geom = new THREE.PlaneGeometry(0, 0, line.length - 1, 1);
      for (var i = 0, l = line.length; i < l; i++) {
        pt = line[i];
        geom.vertices[i].x = geom.vertices[i + l].x = pt[0];
        geom.vertices[i].y = geom.vertices[i + l].y = pt[1];
        geom.vertices[i].z = pt[2];
        geom.vertices[i + l].z = z0;
      }
      geom.computeFaceNormals();
      var mesh = new THREE.Mesh(geom, materials[f.m].m);
      mesh.userData = userData;
      return mesh;
    };
  }

  // each feature in this layer
  this.f.forEach(function (f, fid) {
    f.objs = [];
    var userData = {layerId: this.index, featureId: fid};
    for (var i = 0, l = f.lines.length; i < l; i++) {
      var obj = createObject(f, f.lines[i], userData);
      this.addObject(obj);
      f.objs.push(obj);
    }
  }, this);

  if (parent) parent.add(this.objectGroup);
};

Q3D.LineLayer.prototype.buildLabels = function (parent, parentElement) {
  // Line layer doesn't support label
  // Q3D.VectorLayer.prototype.buildLabels.call(this, parent, parentElement);
};


/*
Q3D.PolygonLayer --> Q3D.VectorLayer
*/
Q3D.PolygonLayer = function (params) {
  Q3D.VectorLayer.call(this, params);
  this.type = Q3D.LayerType.Polygon;
};

Q3D.PolygonLayer.prototype = Object.create(Q3D.VectorLayer.prototype);

Q3D.PolygonLayer.prototype.build = function (parent) {
  var materials = this.materials;

  var arrayToVec2Array = function (points) {
    var pt, pts = [];
    for (var i = 0, l = points.length; i < l; i++) {
      pt = points[i];
      pts.push(new THREE.Vector2(pt[0], pt[1]));
    }
    return pts;
  };

  var arrayToVec3Array = function (points, zFunc) {
    if (zFunc === undefined) zFunc = function () { return 0; };
    var pt, pts = [];
    for (var i = 0, l = points.length; i < l; i++) {
      pt = points[i];
      pts.push(new THREE.Vector3(pt[0], pt[1], zFunc(pt[0], pt[1])));
    }
    return pts;
  };

  var arrayToFace3Array = function (faces) {
    var f, fs = [];
    for (var i = 0, l = faces.length; i < l; i++) {
      f = faces[i];
      fs.push(new THREE.Face3(f[0], f[1], f[2]));
    }
    return fs;
  };

  if (this.objType == "Extruded") {
    var createObject = function (f, polygon, z) {
      var shape = new THREE.Shape(arrayToVec2Array(polygon[0]));
      for (var i = 1, l = polygon.length; i < l; i++) {
        shape.holes.push(new THREE.Path(arrayToVec2Array(polygon[i])));
      }
      var geom = new THREE.ExtrudeGeometry(shape, {bevelEnabled: false, amount: f.h});
      var mesh = new THREE.Mesh(geom, materials[f.m].m);
      mesh.position.z = z;
      return mesh;
    };

    // each feature in this layer
    this.f.forEach(function (f, fid) {
      f.objs = [];
      var userData = {layerId: this.index, featureId: fid};
      for (var i = 0, l = f.polygons.length; i < l; i++) {
        var obj = createObject(f, f.polygons[i], f.zs[i]);
        obj.userData = userData;
        this.addObject(obj);
        f.objs.push(obj);
      }
    }, this);
  }
  else {    // this.objType == "Overlay"
    var relativeToDEM = (this.am == "relative");    // altitude mode
    if (relativeToDEM) {
      var dem = this.project.layers[0];
    }
    var face012 = new THREE.Face3(0, 1, 2);
    var createObject = function (f) {
      var zFunc;
      if (relativeToDEM) zFunc = function (x, y) { return dem.getZ(x, y) + f.h; };
      else zFunc = function (x, y) { return f.h; };

      var geom = new THREE.Geometry();

      // vertices and faces
      if (f.triangles !== undefined) {
        geom.vertices = arrayToVec3Array(f.triangles.v, zFunc);
        geom.faces = arrayToFace3Array(f.triangles.f);
      }

      // polygons (number of vertices > 3)
      var polygons = (relativeToDEM) ? (f.split_polygons || []) : f.polygons;
      for (var i = 0, l = polygons.length; i < l; i++) {
        var polygon = polygons[i];
        var triangles = new THREE.Geometry(),
            holes = [];

        // make Vector3 arrays
        triangles.vertices = arrayToVec3Array(polygon[0], zFunc);
        for (var j = 1, m = polygon.length; j < m; j++) {
          holes.push(arrayToVec3Array(polygon[j], zFunc));
        }

        // triangulate polygon
        var faces = THREE.Shape.Utils.triangulateShape(triangles.vertices, holes);

        // append points of holes to vertices
        for (var j = 0, m = holes.length; j < m; j++) {
          Array.prototype.push.apply(triangles.vertices, holes[j]);
        }

        // element of faces is [index1, index2, index3]
        triangles.faces = arrayToFace3Array(faces);

        THREE.GeometryUtils.merge(geom, triangles, 0);
      }
      geom.mergeVertices();
      geom.computeFaceNormals();
      geom.computeVertexNormals();
      var mesh = new THREE.Mesh(geom, materials[f.m].m);

      if (f.b === undefined) return mesh;

      // border
      for (var i = 0, l = f.polygons.length; i < l; i++) {
        var polygon = f.polygons[i];
        for (var j = 0, m = polygon.length; j < m; j++) {
          var geom = new THREE.Geometry();
          if (relativeToDEM) {
            geom.vertices = dem.segmentizeLineString(polygon[j], zFunc);
          }
          else {
            geom.vertices = arrayToVec3Array(polygon[j], zFunc);
          }
          mesh.add(new THREE.Line(geom, materials[f.b].m));
        }
      }
      return mesh;
    };

    // each feature in this layer
    this.f.forEach(function (f, fid) {
      f.objs = [];
      var obj = createObject(f);
      obj.userData.layerId = this.index;
      obj.userData.featureId = fid;
      this.addObject(obj);
      f.objs.push(obj);
    }, this);
  }

  if (parent) parent.add(this.objectGroup);
};

Q3D.PolygonLayer.prototype.buildLabels = function (parent, parentElement) {
  var zFunc, getPointsFunc = function (f) { return f.centroids; };
  var relativeToDEM = (this.am == "relative");    // altitude mode
  if (relativeToDEM) {
    var dem = this.project.layers[0];
    zFunc = dem.getZ.bind(dem);
  }

  Q3D.VectorLayer.prototype.buildLabels.call(this, parent, parentElement, getPointsFunc, zFunc);
};


// load JSON data and build JSON models
Q3D.JSONObjectBuilder = function (loader, project, json_obj) {
  this.loader = loader;
  this.project = project;
  this.features = [];
  this.meshFaceMaterials = {};

  if (json_obj.src !== undefined) {
    loader.load(json_obj.src, this.onLoad.bind(this));
  }
  else if (json_obj.data) {
    var result = loader.parse(JSON.parse(json_obj.data));
    this.geometry = result.geometry;
    this.materials = result.materials;
  }
};

Q3D.JSONObjectBuilder.prototype = {

  constructor: Q3D.JSONObjectBuilder,

  addFeature: function (layerId, featureId) {
    this.features.push({layerId: layerId, featureId: featureId});
    this.buildObjects();
  },

  cloneObject: function (layerId) {
    if (this.geometry === undefined) return null;

    // material is created for each layer
    if (!(layerId in this.meshFaceMaterials)) {
      var mat;
      if (this._origMeshFaceMaterial === undefined) {
        mat = new THREE.MeshFaceMaterial(this.materials);
        this._origMeshFaceMaterial = mat;
      }
      else {
        mat = this._origMeshFaceMaterial.clone();
      }

      this.meshFaceMaterials[layerId] = mat;
      this.project.layers[layerId].materials.push({type: Q3D.MaterialType.MeshFace, m: mat});
    }
    return new THREE.Mesh(this.geometry, this.meshFaceMaterials[layerId]);
  },

  buildObjects: function () {
    if (this.geometry === undefined) return;

    var deg2rad = Math.PI / 180;
    this.features.forEach(function (fet) {
      var layer = this.project.layers[fet.layerId],
          f = layer.f[fet.featureId];
      f.objs = [];

      for (var i = 0, l = f.pts.length; i < l; i++) {
        var pt = f.pts[i],
            mesh = this.cloneObject(fet.layerId);
        mesh.position.set(pt[0], pt[1], pt[2]);
        if (f.rotateX || f.rotateY || f.rotateZ)
          mesh.rotation.set((f.rotateX || 0) * deg2rad, (f.rotateY || 0) * deg2rad, (f.rotateZ || 0) * deg2rad);
        if (f.scale) mesh.scale.set(f.scale, f.scale, f.scale);
        mesh.userData.layerId = fet.layerId;
        mesh.userData.featureId = fet.featureId;

        layer.addObject(mesh);
        f.objs.push(mesh);
      }
    }, this);
    this.features = [];
  },

  onLoad: function (geometry, materials) {
    this.geometry = geometry;
    this.materials = materials;
    this.buildObjects();
  }

};


// Q3D.Utils - Utilities
Q3D.Utils = {};

Q3D.Utils.setObjectVisibility = function (object, visible) {
  object.traverse(function (obj) {
    obj.visible = visible;
  });
};

// Create a texture with image data and update texture when the image has been loaded
Q3D.Utils.loadTextureData = function (imageData) {
  var texture, image = new Image();
  image.onload = function () {
    texture.needsUpdate = true;
    if (!Q3D.Options.exportMode && !Q3D.application.running) Q3D.application.render();
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
    zFunc = function (x, y) { return Q3D.application.project.layers[0].getZ(x, y); }
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
