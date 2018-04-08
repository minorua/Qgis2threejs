Q3D.gui = {

  type: "dat-gui",

  parameters: {
    lyr: [],
    cp: {
      c: "#ffffff",
      d: 0,
      o: 1,
      l: false
    },
    cmd: {         // commands for touch screen devices
      rot: false,  // auto rotation
      wf: false    // wireframe mode
    },
    i: Q3D.application.showInfo
  },

  // initialize gui
  // - setupDefaultItems: default is true
  init: function (setupDefaultItems) {
    this.gui = new dat.GUI();
    this.gui.domElement.parentElement.style.zIndex = 1000;   // display the panel on the front of labels
    if (setupDefaultItems === undefined || setupDefaultItems == true) {
      this.addLayersFolder();
      this.addCustomPlaneFolder();
      if (Q3D.isTouchDevice) this.addCommandsFolder();
      this.addHelpButton();
    }
  },

  addLayersFolder: function () {
    var mapLayers = Q3D.application.scene.mapLayers;
    var parameters = this.parameters;
    var visibleChanged = function (value) { mapLayers[this.object.i].setVisible(value); };
    var opacityChanged = function (value) { mapLayers[this.object.i].setOpacity(value); };

    var layer, layersFolder = this.gui.addFolder('Layers');
    for (var layerId in mapLayers) {
      layer = mapLayers[layerId];
      parameters.lyr[layerId] = {i: layerId, v: layer.visible, o: layer.opacity};
      var folder = layersFolder.addFolder(layer.properties.name);
      folder.add(parameters.lyr[layerId], 'v').name('Visible').onChange(visibleChanged);
      folder.add(parameters.lyr[layerId], 'o').min(0).max(1).name('Opacity').onChange(opacityChanged);
    }
  },

  addCustomPlaneFolder: function () {
    var app = Q3D.application,
        scene = app.scene,
        p = scene.userData;

    var customPlane;
    var parameters = this.parameters;
    var addPlane = function (color) {
      // Add a new plane in the current scene
      var geometry = new THREE.PlaneBufferGeometry(p.width,p.height, 1, 1),
          material = new THREE.MeshLambertMaterial({color: color, transparent: true});
      if (!Q3D.isIE) material.side = THREE.DoubleSide;
      customPlane = new THREE.Mesh(geometry, material);
      scene.add(customPlane);
      app.render();
    };

    // Min/Max value for the plane
    var zMin = 0,
        zMax = 9000;
    /* TODO: [dat-gui] custom plane min/max
    if (layer.type == Q3D.LayerType.DEM) {
      zMin = layer.stats.min;
      zMax = layer.stats.max;

      var buffer = (zMax - zMin) * 0.1;
      if (buffer < 50) buffer = 50;
      zMin -= buffer;
      zMax += buffer;
    }
    */
    parameters.cp.d = zMin;

    // Create Custom Plane folder
    var folder = this.gui.addFolder('Custom Plane');

    // Plane color
    folder.addColor(parameters.cp, 'c').name('Color').onChange(function (value) {
      if (customPlane === undefined) addPlane(parameters.cp.c);
      customPlane.material.color.setStyle(value);
      app.render();
    });

    // Plane altitude
    folder.add(parameters.cp, 'd').min(zMin).max(zMax).name('Altitude').onChange(function (value) {
      if (customPlane === undefined) addPlane(parameters.cp.c);
      customPlane.position.z = (value + p.zShift) * p.zScale;
      customPlane.updateMatrixWorld();
      app.render();
    });

    // Plane opacity
    folder.add(parameters.cp, 'o').min(0).max(1).name('Opacity (0-1)').onChange(function (value) {
      if (customPlane === undefined) addPlane(parameters.cp.c);
      customPlane.material.opacity = value;
      app.render();
    });

    // Enlarge plane option
    folder.add(parameters.cp, 'l').name('Enlarge').onChange(function (value) {
      if (customPlane === undefined) addPlane(parameters.cp.c);
      if (value) customPlane.scale.set(10, 10, 1);
      else customPlane.scale.set(1, 1, 1);
      customPlane.updateMatrixWorld();
      app.render();
    });
  },

  // add commands folder for touch screen devices
  addCommandsFolder: function () {
    var folder = this.gui.addFolder('Commands');
    if (Q3D.Controls.type == "OrbitControls") {
      folder.add(this.parameters.cmd, 'rot').name('Rotate Animation').onChange(Q3D.application.setWireframeMode);
    }
    folder.add(this.parameters.cmd, 'wf').name('Wireframe Mode').onChange(Q3D.application.setWireframeMode);
  },

  addHelpButton: function () {
    this.gui.add(this.parameters, 'i').name('Help');
  }
};
