// Variables
var world = {};
var lyr = [], mat = [], tex = [], jsons=[], labels=[], queryableObjs = [];
var labelVisible = true;
var option = {
  sole_height: 1.5,
  side: {color: 0xc7ac92},
  frame: {color: 0},
  label: {pointer_color: 0x6666cc, autosize: true, height: 10},
  qmarker: {r: 0.25, c:0xffff00, o:0.8}};

var ua = window.navigator.userAgent.toLowerCase();
var isIE = (ua.indexOf("msie") != -1 || ua.indexOf("trident") != -1);

var projector = new THREE.Projector();

// World class
World = function ( mapExtent, width, zExaggeration, zShift ) {
  this.mapExtent = mapExtent;
  this.width = width;
  this.height = width * (mapExtent[3] - mapExtent[1]) / (mapExtent[2] - mapExtent[0]);
  this.scale = width / (mapExtent[2] - mapExtent[0]);
  this.zExaggeration = zExaggeration;
  this.zScale = this.scale * zExaggeration;
  this.zShift = zShift;
};

World.prototype = {

  constructor: World,

  toMapCoordinates: function (x, y, z) {
    return {x : (x + this.width / 2) / this.scale + this.mapExtent[0],
            y : (y + this.height / 2) / this.scale + this.mapExtent[1],
            z : z / this.zScale - this.zShift};
  }

};

// MapLayer class
MapLayer = function ( params ) {
  for (var k in params) {
    this[k] = params[k];
  }
};

MapLayer.prototype = {

  constructor: MapLayer,

  meshes: function () {
    var m = [];
    if (this.type == "dem") {
      for (var i = 0, l = this.dem.length; i < l; i++) {
        m.push(this.dem[i].obj);

        //var aObjs = this.dem[i].aObjs || [];
        //for (var j = 0, k = aObjs.length; j < k; j++) m.push(aObjs[j]);
      }
    } else {
      for (var i = 0, l = this.f.length; i < l; i++) {
        this.f[i].objs.forEach(function (mesh) {
          m.push(mesh);
        });
      }
    }
    return m;
  },

  setVisible: function (visible) {
    if (this.type == "dem") {
      for (var i = 0, l = this.dem.length; i < l; i++) {
        this.dem[i].obj.visible = visible;

        var aObjs = this.dem[i].aObjs;
        if (aObjs !== undefined) {
          for (var j = 0, m = aObjs.length; j < m; j++) {
            aObjs[j].visible = visible;
          }
        }
      }
    } else {
      for (var i = 0, l = this.f.length; i < l; i++) {
        var f = this.f[i];
        f.obj.visible = visible;  // TODO: objs
        if (f.aObj !== undefined) f.aObj.visible = visible;
        if (f.aElem !== undefined) f.aElem.style.display = (visible) ? "block": "none";
      }
    }
  }

};

// Add default key event listener
function addDefaultKeyEventListener() {
  window.addEventListener("keydown", function(e){

    var keyPressed = e.which;
    if (keyPressed == 27) closeClicked(); // ESC
    else if (keyPressed == 73) showInfo();  // I
    else if (keyPressed == 76) toggleLabelVisibility();  // L
    else if (!e.ctrlKey && e.shiftKey) {
      if (keyPressed == 82) controls.reset();   // Shift + R
      else if (keyPressed == 83) { // Shift + S
        var screenShoot = renderer.domElement.toDataURL("image/png");
        var imageUrl = screenShoot.replace("image/png", 'data:application/octet-stream');
        window.open(imageUrl);
      }
    }
  });
}

// Call this once to create materials
function createMaterials() {
  var material;
  for (var i = 0, l = mat.length; i < l; i++) {
    var m = mat[i];
    if (m.type == 0) {
      material = new THREE.MeshLambertMaterial({color:m.c, ambient:m.c});
    }
    else if (m.type == 1) {
      material = new THREE.LineBasicMaterial({color:m.c});
    }
    else {    // type == 2
      material = new THREE.MeshLambertMaterial({color:m.c, ambient:m.c, wireframe:true});
    }
    if (m.o !== undefined && m.o < 1) {
      material.opacity = m.o;
      material.transparent = true;
    }
    mat[i].m = material;
  }
}

// Create a texture with image data and update texture when the image has been loaded
function createTexture(imageData) {
  var texture, image = new Image();
  image.onload = function () { texture.needsUpdate = true; };
  image.src = imageData;
  texture = new THREE.Texture(image);
  return texture;
}

// Terrain functions
function buildDEM(scene, layer, dem) {

  var geometry = new THREE.PlaneGeometry(dem.plane.width, dem.plane.height,
                                     dem.width - 1, dem.height - 1);

  // Filling of the DEM plane
  for (var j = 0, m = geometry.vertices.length; j < m; j++) {
    geometry.vertices[j].z = dem.data[j];
  }

  // Terrain material
  var material;
  if (dem.m !== undefined) material = mat[dem.m].m;
  else {
    var texture;
    if (dem.t.src === undefined) {
      texture = createTexture(dem.t.data);
    } else {
      texture = THREE.ImageUtils.loadTexture(dem.t.src);
      texture.needsUpdate = true;
    }
    if (dem.t.o === undefined) dem.t.o = 1;
    material = new THREE.MeshPhongMaterial({map: texture, opacity: dem.t.o, transparent: (dem.t.o < 1)});
  }
  if (!isIE) material.side = THREE.DoubleSide;

  var plane = new THREE.Mesh(geometry, material);
  if (dem.plane.offsetX != 0) plane.position.x = dem.plane.offsetX;
  if (dem.plane.offsetY != 0) plane.position.y = dem.plane.offsetY;
  plane.userData = [layer.index, 0];
  scene.add(plane);
  if (layer.q) queryableObjs.push(plane);
  dem.obj = plane;
}

/**
 * buildSides()
 *   - scene : scene in which we add sides
 *   - dem : a dem object
 *   - color : color of sides
 *   - sole_height : depth of bottom under zero
 *
 *  Creates sides and bottom of the DEM to give an impression of "extruding" 
 *  and increase the 3D aspect.
 *  It adds also lights to see correctly the meshes created.
 */
function buildSides(scene, dem, color, sole_height) {
  // Filling of altitudes dictionary
  var altitudes = {
    'back': [],
    'left': [],
    'front': [],
    'right': []
  };

  var w = dem.width, h = dem.height;
  altitudes['back'] = dem.data.slice(0, w);
  altitudes['front'] = dem.data.slice(w * (h - 1));
  for (var y = 0; y < h; y++) {
    altitudes['left'].push(dem.data[y * w]);
    altitudes['right'].push(dem.data[(y + 1) * w - 1]);
  }

  // Material
  if (dem.s.o === undefined) dem.s.o = 1;

  var front_material =  new THREE.MeshLambertMaterial({color: color,
                                                       ambient: color,
                                                       opacity: dem.s.o,
                                                       transparent: (dem.s.o < 1)});

  var back_material;
  if (isIE) {   // Shader compilation error occurs with double sided material on IE11
    back_material = front_material.clone();
    back_material.side = THREE.BackSide;
  }
  else {
    front_material.side = THREE.DoubleSide;
    back_material = front_material;
  }

  // Sides
  var side_width;
  for (var side in altitudes) {
    if (side == 'back' || side == 'front')
      side_width = dem.plane.width;
    else
      side_width = dem.plane.height;

    var geom = new THREE.PlaneGeometry(side_width, 2 * sole_height,
                                       altitudes[side].length -1, 1);

    // Filling of the geometry vertices
    for (var i = 0, l = altitudes[side].length; i < l; i++) {
      geom.vertices[i].y = altitudes[side][i];
    }

    // Rotation(s) and translating(s) according to the side
    var mesh;
    switch (side) {
      case 'back' :
        mesh = new THREE.Mesh(geom, back_material);
        mesh.position.y = dem.plane.height/2;
        mesh.rotateOnAxis(new THREE.Vector3(1,0,0), Math.PI/2);
        break;
      case 'left' :
        mesh = new THREE.Mesh(geom, front_material);
        mesh.position.x = -dem.plane.width/2;
        mesh.rotateOnAxis(new THREE.Vector3(0,0,1), -Math.PI/2);
        mesh.rotateOnAxis(new THREE.Vector3(1,0,0), Math.PI/2);
        break;
      case 'front' :
        mesh = new THREE.Mesh(geom, front_material);
        mesh.position.y = -dem.plane.height/2;
        mesh.rotateOnAxis(new THREE.Vector3(1,0,0), Math.PI/2);
        break;
      case 'right' :
        mesh = new THREE.Mesh(geom, back_material);
        mesh.position.x = dem.plane.width/2;
        mesh.rotateOnAxis(new THREE.Vector3(0,0,1), -Math.PI/2);
        mesh.rotateOnAxis(new THREE.Vector3(1,0,0), Math.PI/2);
        break;
    }

    scene.add(mesh);
    dem.aObjs.push(mesh);
  }

  // Bottom
  var geom_bottom = new THREE.PlaneGeometry(dem.plane.width, dem.plane.height, 1, 1);
  var plane_bottom = new THREE.Mesh(geom_bottom, back_material);
  plane_bottom.position.z = -sole_height;
  scene.add(plane_bottom);
  dem.aObjs.push(plane_bottom);

  // Additional lights
  var light2 = new THREE.DirectionalLight(0xffffff, 0.3);
  light2.position.set(dem.plane.width, -dem.plane.height / 2, -10);
  scene.add(light2);

  var light3 = new THREE.DirectionalLight(0xffffff, 0.3);
  light3.position.set(-dem.plane.width, dem.plane.height / 2, -10);
  scene.add(light3);
}

function buildFrame(scene, dem, color, sole_height) {
  var line_mat = new THREE.LineBasicMaterial({color:color});

  // horizontal rectangle at bottom
  var hw = dem.plane.width / 2, hh = dem.plane.height / 2, z = -sole_height;
  var geometry = new THREE.Geometry();
  geometry.vertices.push(new THREE.Vector3(-hw, -hh, z));
  geometry.vertices.push(new THREE.Vector3(hw, -hh, z));
  geometry.vertices.push(new THREE.Vector3(hw, hh, z));
  geometry.vertices.push(new THREE.Vector3(-hw, hh, z));
  geometry.vertices.push(new THREE.Vector3(-hw, -hh, z));

  var obj = new THREE.Line(geometry, line_mat);
  scene.add(obj);
  dem.aObjs.push(obj);

  // vertical lines at corners
  var pts = [[-hw, -hh, dem.data[dem.data.length - dem.width]],
             [hw, -hh, dem.data[dem.data.length - 1]],
             [hw, hh, dem.data[dem.width-1]],
             [-hw, hh, dem.data[0]]];
  for (var i = 0; i < 4; i++) {
    var pt = pts[i];
    geometry = new THREE.Geometry();
    geometry.vertices.push(new THREE.Vector3(pt[0], pt[1], pt[2]));
    geometry.vertices.push(new THREE.Vector3(pt[0], pt[1], z));

    obj = new THREE.Line(geometry, line_mat);
    scene.add(obj);
    dem.aObjs.push(obj);
  }
}

// Vector functions
function buildPointLayer(scene, layer) {
  var f, geometry, obj;
  var deg2rad = Math.PI / 180;
  for (var i = 0, l = layer.f.length; i < l; i++) {
    // each feature in the layer
    f = layer.f[i];
    f.objs = [];
    f.pts.forEach(function (pt) {
      if (layer.objType == "Cube") geometry = new THREE.CubeGeometry(f.w, f.h, f.d);
      else if (layer.objType == "Cylinder" || layer.objType == "Cone") geometry = new THREE.CylinderGeometry(f.rt, f.rb, f.h);
      else geometry = new THREE.SphereGeometry(f.r);

      obj = new THREE.Mesh(geometry, mat[f.m].m);
      obj.position.set(pt[0], pt[1], pt[2]);
      if (f.rotateX) obj.rotation.x = f.rotateX * deg2rad;
      obj.userData = [layer.index, i];
      scene.add(obj);
      if (layer.q) queryableObjs.push(obj);
      f.objs.push(obj);
    });
  }
}

function buildJSONPointLayer(scene, layer) {
  var manager = new THREE.LoadingManager();
  var loader = new THREE.JSONLoader(manager);
  var f, obj, json_objs=[];
  var deg2rad = Math.PI / 180;

  for (var i = 0, l = layer.f.length; i < l; i++) {
    // each feature in the layer
    f = layer.f[i];
    f.objs = [];
    if (json_objs[f.json_index] === undefined) {
      var result = loader.parse(JSON.parse(jsons[f.json_index]));
      json_objs[f.json_index] = new THREE.Mesh(result.geometry, result.materials[0]);
    }
    f.pts.forEach(function (pt) {
      obj = json_objs[f.json_index].clone();
      obj.position.set(pt[0], pt[1], pt[2]);
      if (f.rotateX || f.rotateY || f.rotateZ)
        obj.rotation.set((f.rotateX || 0) * deg2rad, (f.rotateY || 0) * deg2rad, (f.rotateZ || 0) * deg2rad);
      if (f.scale) obj.scale.set(f.scale, f.scale, f.scale);
      obj.userData = [layer.index, i];
      scene.add(obj);
      if (layer.q) queryableObjs.push(obj);
      f.objs.push(obj);
    });
  }
}

function buildLineLayer(scene, layer) {
  var f, geometry, obj;
  for (var i = 0, l = layer.f.length; i < l; i++) {
    // each feature in the layer
    f = layer.f[i];
    f.objs = [];
    f.lines.forEach(function (line) {
      geometry = new THREE.Geometry();
      line.forEach(function (pt) {
        geometry.vertices.push(new THREE.Vector3(pt[0], pt[1], pt[2]));
      });
      obj = new THREE.Line(geometry, mat[f.m].m);
      obj.userData = [layer.index, i];
      scene.add(obj);
      if (layer.q) queryableObjs.push(obj);
      f.objs.push(obj);
    });
  }
}

function buildPolygonLayer(scene, layer) {
  var f, polygon, boundary, pts, shape, geometry, obj;
  for (var i = 0, l = layer.f.length; i < l; i++) {
    // each feature in the layer
    f = layer.f[i];
    f.objs = [];
    for (var j = 0, m = f.polygons.length; j < m; j++) {
      polygon = f.polygons[j];
      for (var k = 0, n = polygon.length; k < n; k++) {
        boundary = polygon[k];
        pts = [];
        boundary.forEach(function(pt) {
          pts.push(new THREE.Vector2(pt[0], pt[1]));
        });
        if (k == 0) {
          shape = new THREE.Shape(pts);
        } else {
          shape.holes.push(new THREE.Path(pts));
        }
      }
      geometry = new THREE.ExtrudeGeometry(shape, {bevelEnabled:false, amount:f.h});
      obj = new THREE.Mesh(geometry, mat[f.m].m);
      obj.position.z = f.zs[j];
      obj.userData = [layer.index, i];
      scene.add(obj);
      if (layer.q) queryableObjs.push(obj);
      f.objs.push(obj);
    }
  }
}

function buildLabels(scene) {
  var f, pts, e, pt0, pt1, geometry;
  var height = option.label.height;
  var container = document.getElementById("webgl");
  var line_mat = new THREE.LineBasicMaterial({color:option.label.pointer_color});
  for (var i = 0, l = lyr.length; i < l; i++) {
    if (lyr[i].l === undefined) continue;

    var attr_idx = lyr[i].l;
    for (var j = 0, m = lyr[i].f.length; j < m; j++) {
      f = lyr[i].f[j];
      if (lyr[i].type == "point") pts = f.pts;
      else if (lyr[i].type == "polygon") pts = f.centroids;
      else continue;

      f.aElems = [];
      f.aObjs = [];
      pts.forEach(function (pt) {
        // create div element for label
        e = document.createElement("div");
        e.appendChild(document.createTextNode(f.a[attr_idx]));
        e.className = "label";
        container.appendChild(e);

        pt0 = new THREE.Vector3(pt[0], pt[1], pt[2]);
        pt1 = new THREE.Vector3(pt[0], pt[1], pt[2] + height);

        // create pointer
        geometry = new THREE.Geometry();
        geometry.vertices.push(pt1);
        geometry.vertices.push(pt0);
        obj = new THREE.Line(geometry, line_mat);
        obj.userData = [i, j];
        scene.add(obj);

        f.aElems.push(e);
        f.aObjs.push(obj);

        labels.push({e:e, obj:obj, pt:pt1, l:i, f:j});
      });
    }
  }
}

function buildModels(scene) {
  createMaterials();

  for (var i = 0, l = lyr.length; i < l; i++) {
    var layer = lyr[i];
    layer.index = i;
    if (layer.type == "dem") {
      for (var j = 0, k = layer.dem.length; j < k; j++) {
        buildDEM(scene, layer, layer.dem[j]);
        layer.dem[j].aObjs = [];

        // Build sides, bottom and frame
        if (layer.dem[j].s !== undefined) buildSides(scene, layer.dem[j], option.side.color, option.sole_height);
        if (layer.dem[j].frame) buildFrame(scene, layer.dem[j], option.frame.color, option.sole_height);
      }
    }
    else if (layer.type == "point") {
      if (layer.objType == "JSON model") buildJSONPointLayer(scene, layer);
      else buildPointLayer(scene, layer);
    }
    else if (layer.type == "line") {
      buildLineLayer(scene, layer);
    }
    else if (layer.type == "polygon") {
      buildPolygonLayer(scene, layer);
    }
  }

  buildLabels(scene);
}

// update label positions
function updateLabels() {
  if (labels.length == 0 || !labelVisible) return;

  var widthHalf = width / 2, heightHalf = height / 2;
  var autosize = option.label.autosize;

  var c2t = controls.target.clone().sub(camera.position);
  var c2l = new THREE.Vector3();
  var v = new THREE.Vector3();

  // make a list of [label index, distance to camera]
  var idx_dist = [];
  for (var i = 0, l = labels.length; i < l; i++) {
    idx_dist.push([i, camera.position.distanceTo(labels[i].pt)]);
  }

  // sort label indexes in descending order of distances
  idx_dist.sort(function(a, b){
    if (a[1] < b[1]) return 1;
    if (a[1] > b[1]) return -1;
    return 0;
  });

  var label, e, x, y, dist, fontSize;
  for (var i = 0, l = labels.length; i < l; i++) {
    label = labels[idx_dist[i][0]];
    e = label.e;
    if (c2l.subVectors(label.pt, camera.position).dot(c2t) > 0) {
      // label is in front
      // calculate label position
      projector.projectVector(v.copy(label.pt), camera);
      x = (v.x * widthHalf) + widthHalf;
      y = -(v.y * heightHalf) + heightHalf;

      // set label position
      e.style.display = "block";
      e.style.left = (x - (e.offsetWidth / 2)) + "px";
      e.style.top = (y - (e.offsetHeight / 2)) + "px";
      e.style.zIndex = i + 1;

      if (autosize) {
        // set font size
        dist = idx_dist[i][1];
        if (dist < 10) dist = 10;
        fontSize = Math.round(1000 / dist);
        if (fontSize < 10) fontSize = 10;
        e.style.fontSize = fontSize + "px";
      }
    }
    else {
      // label is in back
      e.style.display = "none";
    }
  }
}

function toggleLabelVisibility() {
  labelVisible = !labelVisible;
  if (labels.length == 0) return;
  labels.forEach(function (label) {
    if (!labelVisible) label.e.style.display = "none";
    label.obj.visible = labelVisible;
  });
}

// Called from *Controls.js when canvas is clicked
function canvas_clicked(e) {
  if (object_clicked === undefined) return;
  var canvasOffset = offset(renderer.domElement);
  var mx = e.clientX - canvasOffset.left;
  var my = e.clientY - canvasOffset.top;
  var x = (mx / width) * 2 - 1;
  var y = -(my / height) * 2 + 1;
  var vector = new THREE.Vector3(x, y, 1);
  projector.unprojectVector(vector, camera);
  var ray = new THREE.Raycaster(camera.position, vector.sub(camera.position).normalize())
  var objs = ray.intersectObjects(queryableObjs);
  if(objs.length > 0) object_clicked(objs);
}

function offset(elm) {
  var top = left = 0;
  do {
    top += elm.offsetTop || 0; left += elm.offsetLeft || 0; elm = elm.offsetParent;
  } while(elm);
  return {top: top, left: left};
}

function parseParams() {
  var p, vars = {};
  window.location.search.substring(1).split('&').forEach(function (param) {
    p = param.split('=');
    vars[p[0]] = p[1];
  });
  return vars;
}
