// Variables
var world = {};
var lyr = [], mat = [], tex = [], jsons=[], queryableObjs = [];
var option = {side_color: 0xc7ac92, side_sole_height: 1.5};

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
  if (dem.m !== undefined) material = mat[dem.m];
  else {
    var texture;
    if (dem.t.src === undefined) {
      var image = new Image();
      image.src = dem.t.data;
      texture = new THREE.Texture(image);
    } else {
      texture = THREE.ImageUtils.loadTexture(dem.t.src);
    }
    texture.needsUpdate = true;
    if (dem.t.o === undefined) dem.t.o = 1;
    material = new THREE.MeshPhongMaterial({map: texture, opacity: dem.t.o, transparent: (dem.t.o < 1)});
  }
  material.side = THREE.DoubleSide;
  var plane = new THREE.Mesh(geometry, material);

  if (dem.plane.offsetX != 0) plane.position.x = dem.plane.offsetX;
  if (dem.plane.offsetY != 0) plane.position.y = dem.plane.offsetY;
  scene.add(plane);
  if (layer.q) queryableObjs.push(plane);
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

  var side_material =  new THREE.MeshLambertMaterial({color: color,
                                                      ambient: color,
                                                      opacity: dem.side_opacity,
                                                      transparent: (dem.side_opacity < 1),
                                                      side: THREE.DoubleSide});

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

    var mesh = new THREE.Mesh(geom, side_material);

    // Rotation(s) and translating(s) according to the side
    switch (side) {
      case 'back' :
        mesh.position.y = dem.plane.height/2;
        mesh.rotateOnAxis(new THREE.Vector3(1,0,0), Math.PI/2);
        break;
      case 'left' :
        mesh.position.x = -dem.plane.width/2;
        mesh.rotateOnAxis(new THREE.Vector3(0,0,1), -Math.PI/2);
        mesh.rotateOnAxis(new THREE.Vector3(1,0,0), Math.PI/2);
        break;
      case 'front' :
        mesh.position.y = -dem.plane.height/2;
        mesh.rotateOnAxis(new THREE.Vector3(1,0,0), Math.PI/2);
        break;
      case 'right' :
        mesh.position.x = dem.plane.width/2;
        mesh.rotateOnAxis(new THREE.Vector3(0,0,1), -Math.PI/2);
        mesh.rotateOnAxis(new THREE.Vector3(1,0,0), Math.PI/2);
        break;
    }

    scene.add(mesh);
  }

  // Bottom
  var geom_bottom = new THREE.PlaneGeometry(dem.plane.width, dem.plane.height, 1, 1);
  var plane_bottom = new THREE.Mesh(geom_bottom, side_material);
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
        obj.rotation.set(point.rotateX || 0, point.rotateY || 0, point.rotateZ || 0);
      if (point.scale) obj.scale.set(point.scale, point.scale, point.scale);
    } else {
      if (layer.objType == "Cube") geometry = new THREE.CubeGeometry(point.w, point.h, point.d);
      else if (layer.objType == "Cylinder") geometry = new THREE.CylinderGeometry(point.rt, point.rb, point.h);
      else geometry = new THREE.SphereGeometry(point.r);
 
      obj = new THREE.Mesh(geometry, mat[point.m]);
      obj.position.set(pt[0], pt[1], pt[2]);
      if (point.rotateX != undefined) obj.rotation.x = point.rotateX;
    }
    scene.add(obj);
    if (layer.q) queryableObjs.push(obj);
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
    obj = new THREE.Line(geometry, mat[line.m]);
    scene.add(obj);
    if (layer.q) queryableObjs.push(obj);
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
    obj = new THREE.Mesh(geometry, mat[polygon.m]);
    obj.position.z = polygon.z;
    scene.add(obj);
    if (layer.q) queryableObjs.push(obj);
  }
}

function buildModels(scene) {
  for (var i = 0, l = lyr.length; i < l; i++) {
    var layer = lyr[i];
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
}
