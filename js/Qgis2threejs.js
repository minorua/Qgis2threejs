// Variables
var world = {};
var lyr = [], mat = [], tex = [], jsons=[], labels=[], queryableObjs = [];
var option = {side_color: 0xc7ac92, side_sole_height: 1.5, label_pointer_color: 0x6666cc, label_autosize: true};

var ua = window.navigator.userAgent.toLowerCase();
var isIE = (ua.indexOf("msie") != -1 || ua.indexOf("trident") != -1);

var projector = new THREE.Projector();

// Add default key event listener
function addDefaultKeyEventListener() {
  window.addEventListener("keydown", function(e){

    var keyPressed = e.which;
    if (keyPressed == 72) { // H
      var help = (typeof controlHelp === "undefined") ? "* Keys" : controlHelp;
      help += "\n H : Show help\n Shift + R : Reset\n Shift + S : Save as image";
      alert(help);
    } else if (!e.ctrlKey && e.shiftKey) {
      if (keyPressed == 82) controls.reset();   // Shift + R
      else if (keyPressed == 83) { // Shift + S
        var screenShoot = renderer.domElement.toDataURL("image/png");
        var imageUrl = screenShoot.replace("image/png", 'data:application/octet-stream');
        window.open(imageUrl);
      }
    }
  });
}

// Function to transform coordinates
function getMapCoordinates(x, y, z) {
  return {x : (x + world.width / 2) / world.scale + world.mapExtent[0],
          y : (y + world.height / 2) / world.scale + world.mapExtent[1],
          z : z / world.zScale - world.zShift}
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
  if (dem.side_opacity === undefined) dem.side_opacity = 1;

  var front_material =  new THREE.MeshLambertMaterial({color: color,
                                                       ambient: color,
                                                       opacity: dem.side_opacity,
                                                       transparent: (dem.side_opacity < 1)});

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
  }

  // Bottom
  var geom_bottom = new THREE.PlaneGeometry(dem.plane.width, dem.plane.height, 1, 1);
  var plane_bottom = new THREE.Mesh(geom_bottom, back_material);
  plane_bottom.position.z = -sole_height;
  scene.add(plane_bottom);

  // Additional lights
  var light2 = new THREE.DirectionalLight(0xffffff, 0.3);
  light2.position.set(dem.plane.width, -dem.plane.height / 2, -10);
  scene.add(light2);

  var light3 = new THREE.DirectionalLight(0xffffff, 0.3);
  light3.position.set(-dem.plane.width, dem.plane.height / 2, -10);
  scene.add(light3);
}


// Vector functions
function buildPointLayer(scene, layer) {
  var point, pt, obj, meshes = [];
  var manager, loader, json_objs=[];
  var deg2rad = Math.PI / 180;
  for (var i = 0, l = layer.f.length; i < l; i++) {
    point = layer.f[i];
    pt = point.pt;
    if (layer.objType == "JSON model") {
      if (manager == undefined) {
        manager = new THREE.LoadingManager();
        loader = new THREE.JSONLoader(manager);
      }
      if (json_objs[point.json_index] == undefined) {
        var result = loader.parse(JSON.parse(jsons[point.json_index]));
        var json_obj = new THREE.Mesh(result.geometry, result.materials[0]);
        json_objs[point.json_index] = json_obj;
      }
      obj = json_objs[point.json_index].clone()
      obj.position.set(pt[0], pt[1], pt[2]);
      if (point.rotateX || point.rotateY || point.rotateZ)
        obj.rotation.set((point.rotateX || 0) * deg2rad, (point.rotateY || 0) * deg2rad, (point.rotateZ || 0) * deg2rad);
      if (point.scale) obj.scale.set(point.scale, point.scale, point.scale);
    } else {
      if (layer.objType == "Cube") geometry = new THREE.CubeGeometry(point.w, point.h, point.d);
      else if (layer.objType == "Cylinder") geometry = new THREE.CylinderGeometry(point.rt, point.rb, point.h);
      else geometry = new THREE.SphereGeometry(point.r);
 
      obj = new THREE.Mesh(geometry, mat[point.m].m);
      obj.position.set(pt[0], pt[1], pt[2]);
      if (point.rotateX) obj.rotation.x = point.rotateX * deg2rad;
    }
    obj.userData = [layer.index, i];
    scene.add(obj);
    if (layer.q) queryableObjs.push(obj);
    point.obj = obj;
  }
}

function buildLineLayer(scene, layer) {
  var line, geometry, pt, obj;
  for (var i = 0, l = layer.f.length; i < l; i++) {
    line = layer.f[i];
    geometry = new THREE.Geometry();
    for (var j = 0, m = line.pts.length; j < m; j++) {
      pt = line.pts[j];
      geometry.vertices.push(new THREE.Vector3(pt[0], pt[1], pt[2]));
    }
    obj = new THREE.Line(geometry, mat[line.m].m);
    obj.userData = [layer.index, i];
    scene.add(obj);
    if (layer.q) queryableObjs.push(obj);
    line.obj = obj;
  }
}

function buildPolygonLayer(scene, layer) {
  var polygon, pts, pt, shape, geometry, obj;
  for (var i = 0, l = layer.f.length; i < l; i++) {
    polygon = layer.f[i];
    for (var j = 0, m = polygon.bnds.length; j < m; j++) {
      pts = [];
      for (var k = 0, n = polygon.bnds[j].length; k < n; k++) {
        pt = polygon.bnds[j][k];
        pts.push(new THREE.Vector2(pt[0], pt[1]));
      }
      if (j == 0) {
        shape = new THREE.Shape(pts);
      } else {
        shape.holes.push(new THREE.Path(pts));
      }
    }
    geometry = new THREE.ExtrudeGeometry(shape, {bevelEnabled:false, amount:polygon.h});
    obj = new THREE.Mesh(geometry, mat[polygon.m].m);
    obj.position.z = polygon.z;
    obj.userData = [layer.index, i];
    scene.add(obj);
    if (layer.q) queryableObjs.push(obj);
    polygon.obj = obj;
  }
}

function buildLabels(scene) {
  var f, e, pt, geometry;
  var line_mat = new THREE.LineBasicMaterial({color:option.label_pointer_color});
  for (var i = 0, l = lyr.length; i < l; i++) {
    if (lyr[i].l === undefined) continue;

    var attr_idx = lyr[i].l, height = 10;
    for (var j = 0, m = lyr[i].f.length; j < m; j++) {
      // create div element for label
      f = lyr[i].f[j];
      e = document.createElement("div");
      e.appendChild(document.createTextNode(f.a[attr_idx]));
      e.className = "label";
      document.getElementById("webgl").appendChild(e);

      pt = f.obj.position.clone();
      pt.z += height;
      labels.push({e:e, pt:pt, obj:f.obj});

      // create pointer
      geometry = new THREE.Geometry();
      geometry.vertices.push(f.obj.position.clone());
      geometry.vertices.push(pt.clone());
      obj = new THREE.Line(geometry, line_mat);
      obj.userData = [i, j];
      scene.add(obj);
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
        if (layer.dem[j].s !== undefined) {
          // Build sides and bottom
          buildSides(scene, layer.dem[j], option["side_color"], option["side_sole_height"]);
        }
      }
    }
    else if (layer.type == "point") {
      buildPointLayer(scene, layer);
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

function updateLabels() {
  if (labels.length == 0) return;

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

  var widthHalf = width / 2, heightHalf = height / 2;
  var autosize = option.label_autosize;
  var label, dist, x, y, e, fontSize;
  var vector = new THREE.Vector3();
  for (var i = 0, l = labels.length; i < l; i++) {
    label = labels[idx_dist[i][0]];

    // calculate label position
    projector.projectVector( vector.copy(label.pt), camera );
    x = ( vector.x * widthHalf ) + widthHalf;
    y = - ( vector.y * heightHalf ) + heightHalf;

    // set label position
    e = label.e;
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
}
