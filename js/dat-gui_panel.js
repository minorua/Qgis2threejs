// (C) 2014 Minoru Akagi
// SPDX-License-Identifier: MIT

"use strict";

Q3D.Config.gui = Q3D.Config.gui || {};
Q3D.Config.gui.customPlane = false;

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
  // - setupDefaultItems: default is true
  // - params: parameter values to pass to dat.GUI constructor
  init: function (setupDefaultItems, params) {

    this.gui = new dat.GUI(params);
    this.gui.domElement.parentElement.style.zIndex = 2000;   // display the panel on the front of labels

    if (setupDefaultItems === undefined || setupDefaultItems == true) {
      this.layersFolder = this.gui.addFolder('Layers');
      if (Q3D.Config.gui.customPlane) this.customPlaneFolder = this.gui.addFolder('Custom Plane');
      if (window.TWEEN !== undefined) this.addAnimationFolder();
      if (Q3D.isTouchDevice) this.addCommandsFolder();
      this.addHelpButton();
    }
  },

  initLayersFolder: function (scene) {
    var mapLayers = scene.mapLayers;
    var parameters = this.parameters;
    var visibleChanged = function (value) { mapLayers[this.object.i].visible = value; };
    var opacityChanged = function (o) { mapLayers[this.object.i].opacity = o; };
    var mtlChanged = function (idx) { mapLayers[this.object.i].setCurrentMaterial(idx); };

    var layer, folder, mtlNames, i, items;
    for (var layerId in mapLayers) {
      layer = mapLayers[layerId];
      parameters.lyr[layerId] = {i: layerId, v: layer.visible, o: layer.opacity, m: 0};
      folder = this.layersFolder.addFolder(layer.properties.name);
      folder.add(parameters.lyr[layerId], 'v').name('Visible').onChange(visibleChanged);
      folder.add(parameters.lyr[layerId], 'o').min(0).max(1).name('Opacity').onChange(opacityChanged);

      mtlNames = layer.properties.mtlNames;
      if (mtlNames && mtlNames.length > 1) {
        items = {};
        for (i = 0; i < mtlNames.length; i++) {
          items[mtlNames[i]] = i;
        }
        folder.add(parameters.lyr[layerId], 'm', items).name('Material').onChange(mtlChanged);
      }
    }
    return this.layersFolder;
  },

  customPlaneMaterial: function (color) {
    var m = new THREE.MeshLambertMaterial({color: color, transparent: true})
    if (!Q3D.isIE) m.side = THREE.DoubleSide;
    return m;
  },

  initCustomPlaneFolder: function (zMin, zMax) {
    var app = Q3D.application,
        gui = Q3D.gui;

    var scene = app.scene,
        p = scene.userData,
        parameters = gui.parameters;

    if (zMin === undefined || zMax === undefined) {
      var box = new THREE.Box3().setFromObject(scene);
      if (zMin === undefined) zMin = scene.toMapCoordinates({x: 0, y: 0, z: box.min.z}).z;
      if (zMax === undefined) zMax = scene.toMapCoordinates({x: 0, y: 0, z: box.max.z}).z;
    }

    var addPlane = function (color) {
      // Add a new plane in the current scene
      var geometry = new THREE.PlaneBufferGeometry(p.baseExtent.width, p.baseExtent.height, 1, 1),
          material = gui.customPlaneMaterial(color);
      gui.customPlane = new THREE.Mesh(geometry, material);
      gui.customPlane.rotation.z = p.baseExtent.rotation * Q3D.deg2rad;
      scene.add(gui.customPlane);
      app.render();
    };
    parameters.cp.d = zMin;

    // Plane color
    this.customPlaneFolder.addColor(parameters.cp, 'c').name('Color').onChange(function (value) {
      if (gui.customPlane === undefined) addPlane(parameters.cp.c);
      gui.customPlane.material.color.setStyle(value);
      app.render();
    });

    // Plane altitude
    this.customPlaneFolder.add(parameters.cp, 'd').min(zMin).max(zMax).name('Altitude').onChange(function (value) {
      if (gui.customPlane === undefined) addPlane(parameters.cp.c);
      gui.customPlane.position.z = (value + p.zShift) * p.zScale;
      gui.customPlane.updateMatrixWorld();
      app.render();
    });

    // Plane opacity
    this.customPlaneFolder.add(parameters.cp, 'o').min(0).max(1).name('Opacity (0-1)').onChange(function (value) {
      if (gui.customPlane === undefined) addPlane(parameters.cp.c);
      gui.customPlane.material.opacity = value;
      app.render();
    });

    // Enlarge plane option
    this.customPlaneFolder.add(parameters.cp, 'l').name('Enlarge').onChange(function (value) {
      if (gui.customPlane === undefined) addPlane(parameters.cp.c);
      if (value) gui.customPlane.scale.set(80, 80, 1);
      else gui.customPlane.scale.set(1, 1, 1);
      gui.customPlane.updateMatrixWorld();
      app.render();
    });
  },

  addAnimationFolder: function () {
    var k = Q3D.application.animation.keyframes;
    var btn, folder = this.gui.addFolder('Animation');

    this.parameters.anm = {
      p: function () {
        if (k.isActive) {
          k.pause();
          btn.name('Resume');
        }
        else {
          if (k.isPaused) k.resume();
          else k.start();
          btn.name('Pause');
        }
    }};
    btn = folder.add(this.parameters.anm, 'p').name('Play');

    k.onStop = function () {
      btn.name('Play');
    };
  },

  // add commands folder for touch screen devices
  addCommandsFolder: function () {
    var folder = this.gui.addFolder('Commands');
    folder.add(this.parameters.cmd, 'rot').name('Orbit Animation').onChange(Q3D.application.setRotateAnimationMode);
    folder.add(this.parameters.cmd, 'wf').name('Wireframe Mode').onChange(Q3D.application.setWireframeMode);
  },

  addHelpButton: function () {
    this.gui.add(this.parameters, 'i').name('Help');
  }

};
