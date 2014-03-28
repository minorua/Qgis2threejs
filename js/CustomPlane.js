// Variables
var dem = [], tex = [], mat = [], points = [], lines = [], polygons = [], jsons = [];
var option = {nosides: false, side_color: 0xc7ac92, side_sole_height: 1.5, side_opacity: 1.0, dem_opacity: 1.0};
var customPlane;

// Terrain functions
function buildDEM(scene, dem, tex) {

  var geometry = new THREE.PlaneGeometry(dem.plane.width, dem.plane.height,
                                     dem.width - 1, dem.height - 1);

  // Filling of the DEM plane
  for (var j = 0, m = geometry.vertices.length; j < m; j++) {
    geometry.vertices[j].z = dem.data[j];
  }

  // Terrain material
  var texture;
  if (tex.substr(0, 5) == "data:") {
    var image = new Image();
    image.src = tex;
    texture = new THREE.Texture(image);
  } else {
    texture = THREE.ImageUtils.loadTexture(tex);
  }
  texture.needsUpdate = true;

  var material = new THREE.MeshPhongMaterial({map: texture, opacity: option["dem_opacity"], transparent: (option["dem_opacity"] < 1)});
  var plane = new THREE.Mesh(geometry, material);

  if (dem.plane.offsetX != 0) plane.position.x = dem.plane.offsetX;
  if (dem.plane.offsetY != 0) plane.position.y = dem.plane.offsetY;
  scene.add(plane);
}

/**
 * addPlane()
 *   - color : color of sides
 *
 *  Add a new plane in the current scene
 *  TODO: add a dropdown menu if using multiple DEM
 */

function addPlane(color) {
  var customPlaneGeometry = new THREE.PlaneGeometry(
                                    dem[0].plane.width, dem[0].plane.height,
                                     dem[0].width - 1, dem[0].height - 1);
  var customPlaneMaterial = new THREE.MeshLambertMaterial(
    {
      color:color,
      transparent:true
    });

  customPlane = new THREE.Mesh(customPlaneGeometry,customPlaneMaterial);
  scene.add(customPlane);

}

/**
 * buildSides()
 *   - scene : scene in which we add sides
 *   - dem : a dem object
 *   - color : color of sides
 *   - opacity : opacity of sides
 *   - sole_height : depth of bottom under zero
 *
 *  Creates sides and bottom of the DEM to give an impression of "extruding"
 *  and increase the 3D aspect.
 *  It adds also lights to see correctly the meshes created.
 */
function buildSides(scene, dem, color, opacity, sole_height) {
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
  var side_material =  new THREE.MeshLambertMaterial({color: color,
                                                      ambient: color,
                                                      opacity: opacity,
                                                      transparent: (opacity < 1),
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

function buildDEMs(scene) {

  for (var i = 0, l = dem.length; i < l; i++) {
    buildDEM(scene, dem[i], tex[i])
  }

  // Build sides and bottom
  if (option["nosides"] == false && dem.length == 1) {
    buildSides(scene, dem[0], option["side_color"], option["side_opacity"], option["side_sole_height"]);
  }
}


// Vector functions
function buildPoints(scene) {
  var point, pt, obj, meshes = [];
  var manager, loader, json_objs=[];
  for (var i = 0, l = points.length; i < l; i++) {
    point = points[i];
    pt = point.pt;
    if (point.type == "json") {
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
      if (point.type == "cube") geometry = new THREE.CubeGeometry(point.w, point.h, point.d);
      else if (point.type == "cylinder") geometry = new THREE.CylinderGeometry(point.rt, point.rb, point.h);
      else geometry = new THREE.SphereGeometry(point.r);

      obj = new THREE.Mesh(geometry, mat[point.m]);
      obj.position.set(pt[0], pt[1], pt[2]);
      if (point.rotateX != undefined) obj.rotation.x = point.rotateX;
    }
    scene.add(obj);
    // meshes.push(obj)  // for click event
  }
}

function buildLines(scene) {
  var line, geometry, pt, obj;
  for (var i = 0, l = lines.length; i < l; i++) {
    line = lines[i];
    geometry = new THREE.Geometry();
    for (var j = 0, m = line.pts.length; j < m; j++) {
      pt = line.pts[j];
      geometry.vertices.push(new THREE.Vector3(pt[0], pt[1], pt[2]));
    }
    obj = new THREE.Line(geometry, mat[line.m]);
    scene.add(obj);
  }
}

function buildPolygons(scene) {
  var polygon, pts, pt, shape, geometry, obj;
  for (var i = 0, l = polygons.length; i < l; i++) {
    polygon = polygons[i];
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
    // meshes.push(obj)
  }
}
//GUI
var gui = new dat.GUI();

var parameters = {
    c: "#ffffff",
    d: 0,
    o:1
}

//Crete the GUI for the plane
var maingui = gui.addFolder('Custom Plane');
var customPlaneColor = maingui.addColor(parameters,'c').name('Color');
var customPlaneHeight = maingui.add(parameters,'d').min(0).max(5000).name('Plane height (m)');
var customPlaneOpacity = maingui.add(parameters,'o').min(0).max(1).name('Opacity (0-1)');

//Change plane color
customPlaneColor.onChange(function(value) {
  if (customPlane) {
    customPlane.material.color.setStyle(value);
  } else {
    addPlane(value);
  }
});

//Change plane Z
customPlaneHeight.onChange(function(value) {
  if (customPlane) {
    customPlane.position.z = value*dem[0].multiplierZ;
  } else {
    addPlane(parameters.c);
    customPlane.position.z = value*dem[0].multiplierZ;
  }
});

//Change plane Opacity
customPlaneOpacity.onChange(function(value) {
   if (customPlane) {
     customPlane.material.opacity = value;
   } 
});

function buildVectors(scene) {
  buildPoints(scene);
  buildLines(scene);
  buildPolygons(scene);
}

function buildModels(scene) {
  buildDEMs(scene);
  buildVectors(scene);
}