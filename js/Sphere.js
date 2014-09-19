var earth, meridians, parallels, graticule_material, lights = {};
var rotateSpeed = 0, rotateSpeedMultiplier = 0.0001;
var deg2rad = Math.PI / 180;
var guiParams = {
  c: "#eeeeee",      // background color
  l: {
    a: {      // ambient
      c: "#ffffff"
    },
    d: {      // directional
      c: "#ffffff",
      i: 0,    // intensity
      d: -45   // direction (left=-90, near=0, right=90)
    }
  },
  tilt: 0,
  g: {      // graticule
    m: true,
    p: true,
    c: "#666666",
    o: 0.3
  },
  m: {      // meridians
    v: true
  },
  p: {      // parallels
    v: true
  },
  sp: 0,    // rotation speed
  i: function () {
       showInfo();
     }
};

function buildLights(scene) {
  // ambient light
  lights.ambient = new THREE.AmbientLight(rgb2int(guiParams.l.a.c));
  scene.add(lights.ambient);

  // directional light
  var lambda = guiParams.l.d.d * deg2rad;
  lights.directional = new THREE.DirectionalLight(rgb2int(guiParams.l.d.c), guiParams.l.d.i);
  lights.directional.position.set(Math.sin(lambda), -Math.cos(lambda), 0);
  scene.add(lights.directional);
}

function buildModels(scene) {
  // build sphere
  var r = 50;
  var opacity = 1;

  var geometry = new THREE.SphereGeometry(r, 32, 24);
  var texture = createTexture(tex);
  var material = new THREE.MeshPhongMaterial({map: texture, opacity: opacity, transparent: (opacity < 1)});
  var sphere = new THREE.Mesh(geometry, material);
  queryableObjs.push(sphere);

  // graticule
  graticule_material = new THREE.LineBasicMaterial({color:rgb2int(guiParams.g.c), opacity: guiParams.g.o, transparent: (guiParams.g.o < 1)});
  meridians = createMeridians(r + 0.00001, 10, 5, graticule_material);
  parallels = createParallels(r + 0.00001, 10, 5, graticule_material);

  earth = new THREE.Object3D();
  earth.add(sphere);
  earth.add(meridians);
  earth.add(parallels);
  setAxisTilt(guiParams.tilt);
  scene.add(earth);
}

function createMeridians(radius, interval, line_segments, material) {
  var lines = new THREE.Object3D();
  var phi, x, y, dlat = interval / line_segments;
  for (var lon = -180; lon < 180; lon += interval) {
    var lambda = lon * deg2rad;
    var geometry = new THREE.Geometry();
    for (var lat = -90; lat <= 90; lat += dlat) {
      phi = lat * deg2rad;
      x = radius * Math.cos(phi);
      y = radius * Math.sin(phi);
      geometry.vertices.push(new THREE.Vector3(x * Math.cos(lambda), y, -x * Math.sin(lambda)));
    }
    lines.add(new THREE.Line(geometry, material));
  }
  /*
  // x-axis
  var geometry = new THREE.Geometry();
  geometry.vertices.push(new THREE.Vector3(0, 0, 0));
  geometry.vertices.push(new THREE.Vector3(100, 0, 0));
  var line = new THREE.Line(geometry, line_mat);
  lines.add(line);
  */
  return lines;
}

function createParallels(radius, interval, line_segments, material) {
  var lines = new THREE.Object3D();
  var phi, rp, z, lambda, dlon = interval / line_segments;
  for (var lat = -90 + interval; lat < 90; lat += interval) {
    phi = lat * deg2rad;
    rp = radius * Math.cos(phi);
    z = radius * Math.sin(phi);
    var geometry = new THREE.Geometry();
    for (var lon = -180; lon <= 180; lon += dlon) {
      lambda = lon * deg2rad;
      geometry.vertices.push(new THREE.Vector3(rp * Math.cos(lambda), z, rp * Math.sin(lambda)));
    }
    lines.add(new THREE.Line(geometry, material));
  }
  return lines;
}

function setAxisTilt(tilt) {
  earth.rotation.set((90 - tilt) * deg2rad, 0, -90 * deg2rad, "ZXY");  // tilt to right
  //earth.rotation.set((90 + tilt) * deg2rad, -90 * deg2rad, 0);  // bow
}

function rgb2int(rgb) {
  return parseInt(rgb.replace("#", "0x"));
}

function initGUI(gui) {
  var folder = gui.addFolder("Scene");
  folder.addColor(guiParams, "c").name("Background color").onChange(function(value) {
    renderer.setClearColor(value);
  });

  folder = gui.addFolder("Lights");
  subfolder = folder.addFolder("Ambient");
  subfolder.addColor(guiParams.l.a, "c").name("Color").onChange(function(value) {
    lights.ambient.color.setHex(rgb2int(value));
  });

  subfolder = folder.addFolder("Directional");
  subfolder.addColor(guiParams.l.d, "c").name("Color").onChange(function(value) {
    lights.directional.color.setHex(rgb2int(value));
  });
  subfolder.add(guiParams.l.d, "i").min(0).max(3).name("Intensity").onChange(function(value) {
    lights.directional.intensity = value;
  });
  subfolder.add(guiParams.l.d, "d").min(-180).max(180).name("Direction").onChange(function(value) {
    light_lambda = value * Math.PI / 180;
    lights.directional.position.set(Math.sin(light_lambda), -Math.cos(light_lambda), 0);
  });

  /*
  folder = gui.addFolder("Earth");
  folder.add(guiParams, "tilt").min(0).max(90).name("Axis tilt").onChange(setAxisTilt);
  */

  folder = gui.addFolder("Graticule");
  //subfolder = folder.addFolder("Meridians");
  folder.add(guiParams.g, "m").name("Meridians").onChange(function(value) {
    for (var i = meridians.children.length; i--;)
      meridians.children[i].visible = value;
  });

  //subfolder = folder.addFolder("Parallels");
  folder.add(guiParams.g, "p").name("Parallels").onChange(function(value) {
    for (var i = parallels.children.length; i--;)
      parallels.children[i].visible = value;
  });

  folder.addColor(guiParams.g, "c").name("Line color").onChange(function(value) {
    graticule_material.color.setHex(rgb2int(value));
  });

  folder.add(guiParams.g, "o").min(0).max(1).name("Line opacity").onChange(function(value) {
    graticule_material.opacity = value;
    graticule_material.transparent = (value < 1);
  });

  folder = gui.addFolder("Animation");
  guiControllers.sp = folder.add(guiParams, 'sp').min(0).max(500).name('Rotation speed (%)');
  guiControllers.sp.onChange(function(value) {
    rotateSpeed = rotateSpeedMultiplier * value;
  });

  // Add Help button
  gui.add(guiParams, 'i').name('Help');
}
