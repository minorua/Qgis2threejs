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
    var parameters = this.parameters;
    var layersFolder = this.gui.addFolder('Layers');

    var visibleChanged = function (value) { project.layers[this.object.i].setVisible(value); };
    var opacityChanged = function (value) { project.layers[this.object.i].setOpacity(value); };
    var sideVisibleChanged = function (value) { project.layers[this.object.i].setSideVisibility(value); };

    project.layers.forEach(function (layer, i) {
      parameters.lyr[i] = {i: i, v: layer.visible, o: layer.opacity};
      var folder = layersFolder.addFolder(layer.name);
      folder.add(parameters.lyr[i], 'v').name('Visible').onChange(visibleChanged);

      if (layer.type == Q3D.LayerType.DEM) {
        var itemName = '';
        if (layer.blocks[0].sides) itemName = 'Sides and bottom';
        else if (layer.blocks[0].frame) itemName = 'Frame';

        if (itemName) {
          parameters.lyr[i].sv = true;
          folder.add(parameters.lyr[i], 'sv').name(itemName).onChange(sideVisibleChanged);
        }
      }
      else if (layer.type == Q3D.LayerType.Polygon && layer.objType == 'Overlay') {
        var j, f = layer.f, m = f.length;
        for (j = 0; j < m; j++) {
          if (f[j].mb === undefined) continue;
          parameters.lyr[i].border = true;
          folder.add(parameters.lyr[i], 'border').name('Borders').onChange(function (value) {
            project.layers[this.object.i].setBorderVisibility(value);
          });
          break;
        }

        for (j = 0; j < m; j++) {
          if (f[j].ms === undefined) continue;
          parameters.lyr[i].side = true;
          folder.add(parameters.lyr[i], 'side').name('Sides').onChange(function (value) {
            project.layers[this.object.i].setSideVisibility(value);
          });
          break;
        }
      }

      folder.add(parameters.lyr[i], 'o').min(0).max(1).name('Opacity').onChange(opacityChanged);
    });
  },

  addCustomPlaneFolder: function () {
    var customPlane;
    var parameters = this.parameters;
    var addPlane = function (color) {
      // Add a new plane in the current scene
      var geometry = new THREE.PlaneBufferGeometry(project.width, project.height, 1, 1),
          material = new THREE.MeshLambertMaterial({color: color, transparent: true});
      if (!Q3D.isIE) material.side = THREE.DoubleSide;
      customPlane = new THREE.Mesh(geometry, material);
      Q3D.application.scene.add(customPlane);
    };

    // Min/Max value for the plane
    var zMin = (project.layers[0].type == Q3D.LayerType.DEM) ? project.layers[0].stats.min - 500 : 0,
        zMax = (project.layers[0].type == Q3D.LayerType.DEM) ? project.layers[0].stats.max + 1000 : 9000;
    parameters.cp.d = zMin;

    // Create Custom Plane folder
    var folder = this.gui.addFolder('Custom Plane');

    // Plane color
    folder.addColor(parameters.cp, 'c').name('Color').onChange(function (value) {
      if (customPlane === undefined) addPlane(parameters.cp.c);
      customPlane.material.color.setStyle(value);
    });

    // Plane height
    folder.add(parameters.cp, 'd').min(zMin).max(zMax).name('Plane height').onChange(function (value) {
      if (customPlane === undefined) addPlane(parameters.cp.c);
      customPlane.position.z = (value + project.zShift) * project.zScale;
      customPlane.updateMatrixWorld();
    });

    // Plane opacity
    folder.add(parameters.cp, 'o').min(0).max(1).name('Opacity (0-1)').onChange(function (value) {
      if (customPlane === undefined) addPlane(parameters.cp.c);
      customPlane.material.opacity = value;
    });

    // Enlarge plane option
    folder.add(parameters.cp, 'l').name('Enlarge').onChange(function (value) {
      if (customPlane === undefined) addPlane(parameters.cp.c);
      if (value) customPlane.scale.set(10, 10, 1);
      else customPlane.scale.set(1, 1, 1);
      customPlane.updateMatrixWorld();
    });
  },

  // add commands folder for touch screen devices
  addCommandsFolder: function () {
    var folder = this.gui.addFolder('Commands');
    if (Q3D.Controls.type == "OrbitControls") {
      folder.add(this.parameters.cmd, 'rot').name('Auto Rotation').onChange(function (value) {
        Q3D.application.controls.autoRotate = value;
      });
    }
    folder.add(this.parameters.cmd, 'wf').name('Wireframe Mode').onChange(Q3D.application.setWireframeMode);
  },

  addHelpButton: function () {
    this.gui.add(this.parameters, 'i').name('Help');
  }
};
