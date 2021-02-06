Q3D.gui = {

  type: "dat-gui",

  parameters: {
    lyr: {},
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
  // - scene
  // - setupDefaultItems: default is true
  // - params: parameter values to pass to dat.GUI constructor
  init: function (scene, setupDefaultItems, params) {

    this.scene = scene;

    this.gui = new dat.GUI(params);
    this.gui.domElement.parentElement.style.zIndex = 2000;   // display the panel on the front of labels

    if (setupDefaultItems === undefined || setupDefaultItems == true) {
      this.addLayersFolder();
      this.customPlaneFolder = this.gui.addFolder('Custom Plane');
      if (Q3D.isTouchDevice) this.addCommandsFolder();
      this.addHelpButton();
    }
  },

  addLayersFolder: function () {
    var mapLayers = this.scene.mapLayers;
    var parameters = this.parameters;
    var visibleChanged = function (value) { mapLayers[this.object.i].visible = value; };
    var opacityChanged = function (value) { mapLayers[this.object.i].opacity = value; };

    var layer, subfolder,
        folder = this.gui.addFolder('Layers');

    for (var layerId in mapLayers) {
      layer = mapLayers[layerId];
      parameters.lyr[layerId] = {i: layerId, v: layer.visible, o: layer.opacity};
      subfolder = folder.addFolder(layer.properties.name);
      subfolder.add(parameters.lyr[layerId], 'v').name('Visible').onChange(visibleChanged);
      subfolder.add(parameters.lyr[layerId], 'o').min(0).max(1).name('Opacity').onChange(opacityChanged);
    }
    return folder;
  },

  customPlaneMaterial: function (color) {
    var m = new THREE.MeshLambertMaterial({color: color, transparent: true})
    if (!Q3D.isIE) m.side = THREE.DoubleSide;
    return m;
  },

  initCustomPlaneFolder: function (zMin, zMax) {
    var app = Q3D.application;

    var scene = this.scene,
        p = scene.userData,
        parameters = this.parameters;

    if (zMin === undefined || zMax === undefined) {
      var box = new THREE.Box3().setFromObject(scene);
      if (zMin === undefined) zMin = scene.toMapCoordinates(0, 0, box.min.z).z;
      if (zMax === undefined) zMax = scene.toMapCoordinates(0, 0, box.max.z).z;
    }

    var customPlane;

    var addPlane = function (color) {
      // Add a new plane in the current scene
      var geometry = new THREE.PlaneBufferGeometry(p.width,p.height, 1, 1),
          material = Q3D.gui.customPlaneMaterial(color);
      customPlane = new THREE.Mesh(geometry, material);
      scene.add(customPlane);
      Q3D.gui.customPlane = customPlane;
      app.render();
    };
    parameters.cp.d = zMin;

    // Plane color
    this.customPlaneFolder.addColor(parameters.cp, 'c').name('Color').onChange(function (value) {
      if (customPlane === undefined) addPlane(parameters.cp.c);
      customPlane.material.color.setStyle(value);
      app.render();
    });

    // Plane altitude
    this.customPlaneFolder.add(parameters.cp, 'd').min(zMin).max(zMax).name('Altitude').onChange(function (value) {
      if (customPlane === undefined) addPlane(parameters.cp.c);
      customPlane.position.z = (value + p.zShift) * p.zScale;
      customPlane.updateMatrixWorld();
      app.render();
    });

    // Plane opacity
    this.customPlaneFolder.add(parameters.cp, 'o').min(0).max(1).name('Opacity (0-1)').onChange(function (value) {
      if (customPlane === undefined) addPlane(parameters.cp.c);
      customPlane.material.opacity = value;
      app.render();
    });

    // Enlarge plane option
    this.customPlaneFolder.add(parameters.cp, 'l').name('Enlarge').onChange(function (value) {
      if (customPlane === undefined) addPlane(parameters.cp.c);
      if (value) customPlane.scale.set(80, 80, 1);
      else customPlane.scale.set(1, 1, 1);
      customPlane.updateMatrixWorld();
      app.render();
    });
  },

  // add commands folder for touch screen devices
  addCommandsFolder: function () {
    var folder = this.gui.addFolder('Commands');
    folder.add(this.parameters.cmd, 'rot').name('Rotate Animation').onChange(Q3D.application.setRotateAnimationMode);
    folder.add(this.parameters.cmd, 'wf').name('Wireframe Mode').onChange(Q3D.application.setWireframeMode);
  },

  addHelpButton: function () {
    this.gui.add(this.parameters, 'i').name('Help');
  }

};
