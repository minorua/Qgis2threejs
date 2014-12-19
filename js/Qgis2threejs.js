// Qgis2threejs.js
// MIT License
// (C) 2014 Minoru Akagi

var Q3D = {};
Q3D.Options = {
  bgcolor: null,
  sole_height: 1.5,
  side: {color: 0xc7ac92},
  frame: {color: 0},
  label: {visible: true, connectorColor: 0xc0c0d0, autoSize: false, minFontSize: 10},
  qmarker: {r: 0.25, c: 0xffff00, o: 0.8},
  exportMode: false
};

Q3D.LayerType = {DEM: "dem", Point: "point", Line: "line", Polygon: "polygon"};
Q3D.uv = {i: new THREE.Vector3(1, 0, 0), j: new THREE.Vector3(0, 1, 0), k: new THREE.Vector3(0, 0, 1)};
Q3D.projector = new THREE.Projector();

Q3D.ua = window.navigator.userAgent.toLowerCase();
Q3D.isIE = (Q3D.ua.indexOf("msie") != -1 || Q3D.ua.indexOf("trident") != -1);

Q3D.$ = function (elementId) {
  return document.getElementById(elementId);
};

/*
Project class - Project data holder
*/
Q3D.Project = function (title, crs, baseExtent, width, zExaggeration, zShift) {
  this.title = title;
  this.crs = crs;
  this.baseExtent = baseExtent;
  this.width = width;
  this.height = width * (baseExtent[3] - baseExtent[1]) / (baseExtent[2] - baseExtent[0]);
  this.scale = width / (baseExtent[2] - baseExtent[0]);
  this.zExaggeration = zExaggeration;
  this.zScale = this.scale * zExaggeration;
  this.zShift = zShift;

  this.layers = [];
  this.jsons = [];
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
      // TODO: show message "another window has been opened".
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

    // popup window
    this.popup = new Q3D.Popup();

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

    // TODO:
    this.actions = [];
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

    // create a marker for queried point
    var opt = Q3D.Options.qmarker;
    this.queryMarker = new THREE.Mesh(new THREE.SphereGeometry(opt.r),
                                      new THREE.MeshLambertMaterial({color: opt.c, ambient: opt.c, opacity: opt.o, transparent: (opt.o < 1)}));
    this.queryMarker.visible = false;
    this.scene.add(this.queryMarker);
  },

  addEventListeners: function () {
    window.addEventListener("keydown", this.eventListener.keydown.bind(this));
    window.addEventListener("resize", this.eventListener.resize.bind(this));

    var e = Q3D.$("closebtn");
    if (e) e.addEventListener("click", this.closePopup.bind(this));
  },

  eventListener: {

    keydown: function (e) {
      var keyPressed = e.which;
      if (keyPressed == 27) this.closePopup(); // ESC
      else if (keyPressed == 73) this.showInfo();  // I
      else if (keyPressed == 76) this.setLabelVisibility(!this.labelVisibility);  // L
      else if (!e.ctrlKey && e.shiftKey) {
        if (keyPressed == 82) this.controls.reset();   // Shift + R
        else if (keyPressed == 83) { // Shift + S
          var screenshot = this.renderer.domElement.toDataURL("image/png");
          var imageUrl = screenshot.replace("image/png", 'data:application/octet-stream');
          window.open(imageUrl);
        }
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
    // ambient light
    parent.add(new THREE.AmbientLight(0x999999));

    // directional lights
    var light1 = new THREE.DirectionalLight(0xffffff, 0.4);
    light1.position.set(-0.1, -0.3, 1);
    parent.add(light1);

    if (!this.project) return;
    
    var light2 = new THREE.DirectionalLight(0xffffff, 0.3);
    light2.position.set(this.project.width, -this.project.height / 2, -10);
    parent.add(light2);

    var light3 = new THREE.DirectionalLight(0xffffff, 0.3);
    light3.position.set(-this.project.width, this.project.height / 2, -10);
    parent.add(light3);
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
    if (true) this.render();   // TODO: if something is changed.
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
      var layer = this.project.layers[group.userData];
      if (!layer.visible && visible) return;
      Q3D.Utils.setObjectVisibility(group, visible);
    }, this);

    this.render();
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
    var help = (Q3D.Controls === undefined) ? "* Keys" : Q3D.Controls.usage.split("\n").join("<br>");
    help += "<br> I : Show page information<br> L : Toggle label visibility<br> Shift + R : Reset<br> Shift + S : Save as image";
    return help;
  },

  showInfo: function () {
    this.popup.showInfo({"urlbox": this.currentViewUrl(), "usage": this.help()});
  },

  showQueryResult: function (obj) {
    // query marker
    this.queryMarker.position.set(obj.point.x, obj.point.y, obj.point.z);
    this.queryMarker.visible = true;

    var userData = obj.object.userData, layer, r = [];
    if (userData !== undefined) {
      // layer name
      layer = this.project.layers[userData[0]];
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
    r.push([pt.x.toFixed(2), pt.y.toFixed(2), pt.z.toFixed(2)].join(", "));
    r.push("</td></tr></table>");

    if (layer !== undefined && layer.type != Q3D.LayerType.DEM && layer.a !== undefined) {
      // attributes
      r.push('<table class="attrs">');
      r.push("<caption>Attributes</caption>");
      var f = layer.f[userData[1]];
      for (var i = 0, l = layer.a.length; i < l; i++) {
        r.push("<tr><td>" + layer.a[i] + "</td><td>" + f.a[i] + "</td></tr>");
      }
      r.push("</table>");
    }
    this.popup.showQueryResult(r.join(""));
  },

  closePopup: function () {
    this.popup.hide();
    this.queryMarker.visible = false;
  },

  // Called from *Controls.js when canvas is clicked
  canvasClicked: function (e) {
    var canvasOffset = this._offset(this.renderer.domElement);
    var objs = this.intersectObjects(e.clientX - canvasOffset.left, e.clientY - canvasOffset.top);
    for (var i = 0, l = objs.length; i < l; i++) {
      if (objs[i].object.visible) {
        this.showQueryResult(objs[i]);
        return;
      }
    }
    this.closePopup();
  }

  // TODO: addActionToObject(object, action)
};


/*
Popup class
*/
Q3D.Popup = function (popupId) {

  this.popupId = (popupId === undefined) ? "popup" : popupId;

};

Q3D.Popup.prototype = {

  constructor: Q3D.Popup,

  show: function () {
    Q3D.$(this.popupId).style.display = "block";
  },

  hide: function () {
    Q3D.$(this.popupId).style.display = "none";
  },

  showInfo: function (params) {
    if (Q3D.$("urlbox")) Q3D.$("urlbox").value = params.urlbox;
    if (Q3D.$("usage")) Q3D.$("usage").innerHTML = params.usage;

    if (Q3D.$("queryresult")) Q3D.$("queryresult").style.display = "none";
    if (Q3D.$("pageinfo")) Q3D.$("pageinfo").style.display = "block";
    this.show();
  },

  showQueryResult: function (html) {
    if (Q3D.$("pageinfo")) Q3D.$("pageinfo").style.display = "none";
    var e = Q3D.$("queryresult");
    if (e) {
      e.style.display = "block";
      e.innerHTML = html;
    }
    this.show();
  }

  // TODO: result table

};


/*
DEMBlock class
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

    // Terrain material
    var mat;
    if (this.m !== undefined) mat = layer.materials[this.m].m;
    else {
      var texture;
      if (this.t.src === undefined) {
        texture = Q3D.Utils.loadTextureData(this.t.data);
      } else {
        texture = THREE.ImageUtils.loadTexture(this.t.src);
        texture.needsUpdate = true;
      }
      if (this.t.o === undefined) this.t.o = 1;
      mat = new THREE.MeshPhongMaterial({map: texture, opacity: this.t.o, transparent: (this.t.o < 1)});
      layer.materials.push({m: mat});
    }
    if (!Q3D.isIE) mat.side = THREE.DoubleSide;    // Shader compilation error occurs with double sided material on IE11

    var mesh = new THREE.Mesh(geom, mat);
    if (this.plane.offsetX != 0) mesh.position.x = this.plane.offsetX;
    if (this.plane.offsetY != 0) mesh.position.y = this.plane.offsetY;
    mesh.userData = [layer.index, 0];
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
MapLayer class
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
    this.materials = Q3D.Utils.createMaterials(this.m);

    // layer opacity is the average opacity of materials.
    var sum = 0, l = this.materials.length;
    if (l == 0) return;
    for (var i = 0; i < l; i++) {
      sum += this.materials[i].m.opacity;
    }
    this.opacity = sum / l;
  },

  setOpacity: function (opacity) {
    this.opacity = opacity;
    this.materials.forEach(function (mat) {
      mat.m.transparent = (opacity < 1);
      mat.m.opacity = opacity;
    });
  },

  setVisible: function (visible) {
    this.visible = visible;
    Q3D.Utils.setObjectVisibility(this.objectGroup, visible);
  }

};

/*
Q3D.MapLayer.prototype.build = function (parent) {};
Q3D.MapLayer.prototype.meshes = function () {};
*/


/*
Q3D.DEMLayer class --> Q3D.MapLayer
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
    if (block.s !== undefined) this.buildSides(block, opt.side.color, opt.sole_height);
    if (block.frame) this.buildFrame(block, opt.frame.color, opt.sole_height);
  }, this);

  if (parent) parent.add(this.objectGroup);
};

// Creates sides and bottom of the DEM to give an impression of "extruding" and increase the 3D aspect.
Q3D.DEMLayer.prototype.buildSides = function (block, color, sole_height) {
  var dem = block;

  // Material
  var opacity = (block.m !== undefined) ? this.materials[block.m].o : block.t.o;
  if (opacity === undefined) opacity = 1;
  var mat = new THREE.MeshLambertMaterial({color: color,
                                           ambient: color,
                                           opacity: opacity,
                                           transparent: (opacity < 1)});
  this.materials.push({m: mat});

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
  var opacity = (block.m !== undefined) ? this.materials[block.m].o : block.t.o;
  if (opacity === undefined) opacity = 1;
  var mat = new THREE.LineBasicMaterial({color: color,
                                         opacity: opacity,
                                         transparent: (opacity < 1)});
  this.materials.push({m: mat});

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

Q3D.DEMLayer.prototype.initMaterials = function () {
  Q3D.MapLayer.prototype.initMaterials.call(this);

  // overwrite opacity if layer has texture.
  var t = this.blocks[0].t;
  if (t !== undefined && t.o !== undefined) {
    this.opacity = t.o;
  }
};

Q3D.DEMLayer.prototype.setSideVisibility = function (visible) {
  var block = this.blocks[0];
  block.aObjs.forEach(function (obj) {
    obj.visible = visible;
  });
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


/*
Q3D.VectorLayer class --> Q3D.MapLayer
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
  this.labelConnectorGroup.userData = this.index;
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
      conn.userData = [this.index, i];
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
Q3D.PointLayer class --> Q3D.VectorLayer
*/
Q3D.PointLayer = function (params) {
  Q3D.VectorLayer.call(this, params);
  this.type = Q3D.LayerType.Point;
};

Q3D.PointLayer.prototype = Object.create(Q3D.VectorLayer.prototype);

Q3D.PointLayer.prototype.build = function (parent) {
  if (this.objType == "JSON model") {
    this.buildJSONModels(parent);
    return;
  }

  var materials = this.materials;
  var type2int = {
    "Sphere": 0,
    "Cube": 1,
    "Cylinder": 2,
    "Cone": 2
  };
  var typeInt = type2int[this.objType];

  var createGeometry = function (f) {
    if (typeInt == 1) return new THREE.CubeGeometry(f.w, f.h, f.d);
    if (typeInt == 2) return new THREE.CylinderGeometry(f.rt, f.rb, f.h);
    return new THREE.SphereGeometry(f.r);
  };

  var deg2rad = Math.PI / 180;

  // each feature in this layer
  this.f.forEach(function (f, fid) {
    f.objs = [];
    for (var i = 0, l = f.pts.length; i < l; i++) {
      var mesh = new THREE.Mesh(createGeometry(f), materials[f.m].m);

      var pt = f.pts[i];
      mesh.position.set(pt[0], pt[1], pt[2]);
      if (f.rotateX) mesh.rotation.x = f.rotateX * deg2rad;
      mesh.userData = [this.index, fid];

      this.addObject(mesh);
      f.objs.push(mesh);
    }
  }, this);

  if (parent) parent.add(this.objectGroup);
};

Q3D.PointLayer.prototype.buildJSONModels = function (parent) {
  var manager = new THREE.LoadingManager();
  var loader = new THREE.JSONLoader(manager);
  var jsons = this.project.jsons;
  var json_meshes = [];
  var jsonMesh = function (json_index) {
    if (json_meshes[json_index] === undefined) {
      var result = loader.parse(JSON.parse(jsons[json_index].data));
      json_meshes[json_index] = new THREE.Mesh(result.geometry, result.materials[0]);
    }
    return json_meshes[json_index];
  };

  var deg2rad = Math.PI / 180;

  // each feature in this layer
  this.f.forEach(function (f, fid) {
    f.objs = [];

    var orig_mesh = jsonMesh(f.json_index);
    for (var i = 0, l = f.pts.length; i < l; i++) {
      var pt = f.pts[i];
      var mesh = orig_mesh.clone();
      mesh.position.set(pt[0], pt[1], pt[2]);
      if (f.rotateX || f.rotateY || f.rotateZ)
        mesh.rotation.set((f.rotateX || 0) * deg2rad, (f.rotateY || 0) * deg2rad, (f.rotateZ || 0) * deg2rad);
      if (f.scale) mesh.scale.set(f.scale, f.scale, f.scale);
      mesh.userData = [this.index, fid];

      this.addObject(mesh);
      f.objs.push(mesh);
    }
  }, this);

  if (parent) parent.add(this.objectGroup);
};

Q3D.PointLayer.prototype.buildLabels = function (parent, parentElement) {
  Q3D.VectorLayer.prototype.buildLabels.call(this, parent, parentElement, function (f) { return f.pts; });
};


/*
Q3D.LineLayer class --> Q3D.VectorLayer
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
    var createObject = function (f, line, userData) {
      var geom = new THREE.PlaneGeometry(0, 0, line.length - 1, 1);
      for (var i = 0, l = line.length; i < l; i++) {
        pt = line[i];
        geom.vertices[i].x = geom.vertices[i + l].x = pt[0];
        geom.vertices[i].y = geom.vertices[i + l].y = pt[1];
        geom.vertices[i].z = pt[2];
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
    var userData = [this.index, fid];
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
Q3D.PolygonLayer class --> Q3D.VectorLayer
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
      var userData = [this.index, fid];
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
    var border_mat = new THREE.LineBasicMaterial({color: 0}); // TODO: option to select color
    this.materials.push({m: border_mat});
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
        geom.computeFaceNormals();
      }

      // split polygons (number of vertices > 3)
      var l = (f.split_polygons === undefined) ? 0 : f.split_polygons.length;
      for (var i = 0; i < l; i++) {
        var polygon = f.split_polygons[i];
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

        triangles.computeFaceNormals();
        THREE.GeometryUtils.merge(geom, triangles, 0);
      }
      geom.computeBoundingBox();
      var mesh = new THREE.Mesh(geom, materials[f.m].m);

      //if (f.b === undefined) return mesh;   // TODO
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
          mesh.add(new THREE.Line(geom, border_mat));
        }
      }
      return mesh;
    };

    // each feature in this layer
    this.f.forEach(function (f, fid) {
      f.objs = [];
      var obj = createObject(f);
      obj.userData = [this.index, fid];
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


// Q3D.Utils - Utilities
Q3D.Utils = {};

Q3D.Utils.createMaterials = function (m_list) {
  var mat, materials = [];

  for (var i = 0, l = m_list.length; i < l; i++) {
    var m = m_list[i];
    if (m.type == 0 || m.type == 3) {
      mat = new THREE.MeshLambertMaterial({color: m.c, ambient: m.c});
      if (m.type == 3) mat.shading = THREE.FlatShading;
    }
    else if (m.type == 1) {
      mat = new THREE.LineBasicMaterial({color: m.c});
    }
    else {    // type == 2
      mat = new THREE.MeshLambertMaterial({color: m.c, ambient: m.c, wireframe: true});
    }
    if (m.o !== undefined && m.o < 1) {
      mat.opacity = m.o;
      mat.transparent = true;
    }
    if (m.ds) mat.side = THREE.DoubleSide;    // TODO: ie
    m.m = mat;
    materials.push(m);
  }
  return materials;
};

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
