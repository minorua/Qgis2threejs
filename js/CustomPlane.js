var customPlane;

/**
 * addPlane()
 *   - color : color of sides
 *
 *  Add a new plane in the current scene
 *  TODO: add a dropdown menu if using multiple DEM
 */

function addPlane(color) {
  var customPlaneGeometry = new THREE.PlaneGeometry(world.width, world.height, 1, 1);
  var customPlaneMaterial = new THREE.MeshLambertMaterial(
    {
      color:color,
      transparent:true
    });

  customPlane = new THREE.Mesh(customPlaneGeometry,customPlaneMaterial);
  scene.add(customPlane);

}

// GUI
var gui = new dat.GUI();

var parameters = {
  lyr: [],
  cp: {
    c: "#ffffff",
    d: 0,
    o: 1
  },
  i: showInfo
}

initGUI();

function initGUI() {

  // Create Layers folder
  var layersFolder = gui.addFolder('Layers');
  var folder;
  for (var i = 0, l = lyr.length; i < l; i++) {
    folder = layersFolder.addFolder(lyr[i].name);
    parameters.lyr[i] = {i: i, v: true, o: 1};
    folder.add(parameters.lyr[i], 'v').name('Visible').onChange(function(value) {
      lyr[this.object.i].setVisible(value);
    });
  }

  // Max value for the plane
  var zMax = lyr[0].stats.max;

  // Create Custom Plane folder
  var maingui = gui.addFolder('Custom Plane');
  var customPlaneColor = maingui.addColor(parameters.cp, 'c').name('Color');
  var customPlaneHeight = maingui.add(parameters.cp, 'd').min(0).max(zMax).name('Plane height (m)');
  var customPlaneOpacity = maingui.add(parameters.cp, 'o').min(0).max(1).name('Opacity (0-1)');

  // Change plane color
  customPlaneColor.onChange(function(value) {
    if (customPlane) {
      customPlane.material.color.setStyle(value);
    } else {
      addPlane(value);
    }
  });

  // Change plane Z
  customPlaneHeight.onChange(function(value) {
    if (customPlane === undefined) addPlane(parameters.cp.c);
    customPlane.position.z = (value + world.zShift) * world.zScale;
  });

  // Change plane Opacity
  customPlaneOpacity.onChange(function(value) {
     if (customPlane) {
       customPlane.material.opacity = value;
     }
  });

  // Add Help button
  gui.add(parameters, 'i').name('Help');
}
