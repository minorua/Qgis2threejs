// (C) 2014 Minoru Akagi
// SPDX-License-Identifier: MIT

"use strict";

Q3D.Config.gui = Q3D.Config.gui || {};
Q3D.Config.gui.customPlane = false;

Q3D.gui.dat = {

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
    i: Q3D.gui.showInfo
  }
};

(function () {

  var app = Q3D.application,
      _this = Q3D.gui.dat;

  Q3D.gui.modules.push(_this);

  var panel;

  // initialize gui
  // - setupDefaultItems: default is true
  // - params: parameter values to pass to dat.GUI constructor
  _this.init = function (setupDefaultItems, params) {
    setupDefaultItems = (setupDefaultItems === undefined) ? true : setupDefaultItems;

    panel = new dat.GUI(params);
    panel.domElement.parentElement.style.zIndex = 2000;   // display the panel on the front of labels

    this.gui = panel;

    if (setupDefaultItems) {
      this.layersFolder = panel.addFolder('Layers');
      if (Q3D.Config.gui.customPlane) this.customPlaneFolder = panel.addFolder('Custom Plane');
      if (Q3D.Config.animation.enabled) this.addAnimationFolder();
      if (Q3D.isTouchDevice) this.addCommandsFolder();
      this.addHelpButton();
    }
  };

  _this.initLayersFolder = function (scene) {
    var mapLayers = scene.mapLayers;
    var params = this.parameters;

    var visibleChanged = function (value) {
      mapLayers[this.object.i].visible = value;
    };

    var opacityChanged = function (o) {
      mapLayers[this.object.i].opacity = o;
    };

    var mtlChanged = function (idx) {
      mapLayers[this.object.i].setCurrentMaterial(idx);
    };

    var layer, folder, mtlNames, i, items;
    for (var layerId in mapLayers) {
      layer = mapLayers[layerId];
      params.lyr[layerId] = {i: layerId, v: layer.visible, o: layer.opacity, m: 0};
      folder = this.layersFolder.addFolder(layer.properties.name);
      folder.add(params.lyr[layerId], 'v').name('Visible').onChange(visibleChanged);
      folder.add(params.lyr[layerId], 'o').min(0).max(1).name('Opacity').onChange(opacityChanged);

      mtlNames = layer.properties.mtlNames;
      if (mtlNames && mtlNames.length > 1) {
        items = {};
        for (i = 0; i < mtlNames.length; i++) {
          items[mtlNames[i]] = i;
        }
        folder.add(params.lyr[layerId], 'm', items).name('Material').onChange(mtlChanged).setValue(layer.properties.mtlIdx);
      }
    }
    return this.layersFolder;
  };

  _this.customPlaneMaterial = function (color) {
    var m = new THREE.MeshLambertMaterial({color: color, transparent: true});
    if (!Q3D.isIE) m.side = THREE.DoubleSide;
    return m;
  };

  _this.initCustomPlaneFolder = function (zMin, zMax) {
    var scene = app.scene,
        p = scene.userData,
        params = this.parameters;

    if (zMin === undefined || zMax === undefined) {
      var box = new THREE.Box3().setFromObject(scene);
      if (zMin === undefined) zMin = scene.toMapCoordinates({x: 0, y: 0, z: box.min.z}).z;
      if (zMax === undefined) zMax = scene.toMapCoordinates({x: 0, y: 0, z: box.max.z}).z;
    }

    var addPlane = function (color) {
      // Add a new plane in the current scene
      var geometry = new THREE.PlaneBufferGeometry(p.baseExtent.width, p.baseExtent.height, 1, 1),
          material = _this.customPlaneMaterial(color);
      _this.customPlane = new THREE.Mesh(geometry, material);
      _this.customPlane.rotation.z = p.baseExtent.rotation * Q3D.deg2rad;
      scene.add(_this.customPlane);
      app.render();
    };
    params.cp.d = zMin;

    // Plane color
    this.customPlaneFolder.addColor(params.cp, 'c').name('Color').onChange(function (value) {
      if (_this.customPlane === undefined) addPlane(params.cp.c);
      _this.customPlane.material.color.setStyle(value);
      app.render();
    });

    // Plane altitude
    this.customPlaneFolder.add(params.cp, 'd').min(zMin).max(zMax).name('Altitude').onChange(function (value) {
      if (_this.customPlane === undefined) addPlane(params.cp.c);
      _this.customPlane.position.z = value * p.zScale;
      _this.customPlane.updateMatrixWorld();
      app.render();
    });

    // Plane opacity
    this.customPlaneFolder.add(params.cp, 'o').min(0).max(1).name('Opacity (0-1)').onChange(function (value) {
      if (_this.customPlane === undefined) addPlane(params.cp.c);
      _this.customPlane.material.opacity = value;
      app.render();
    });

    // Enlarge plane option
    this.customPlaneFolder.add(params.cp, 'l').name('Enlarge').onChange(function (value) {
      if (_this.customPlane === undefined) addPlane(params.cp.c);
      if (value) _this.customPlane.scale.set(80, 80, 1);
      else _this.customPlane.scale.set(1, 1, 1);
      _this.customPlane.updateMatrixWorld();
      app.render();
    });
  };

  _this.addAnimationFolder = function () {
    var anim = app.animation.keyframes;
    var btn, folder = panel.addFolder('Animation');

    this.parameters.anm = {
      p: function () {
        if (anim.isActive) {
          anim.pause();
          btn.name('Resume');
        }
        else if (anim.isPaused) {
          anim.resume();
          btn.name('Pause');
        }
        else {
          anim.start();
        }
    }};
    btn = folder.add(this.parameters.anm, 'p').name('Play');

    app.addEventListener('animationStarted', function () {
      btn.name('Pause');
    });

    app.addEventListener('animationStopped', function () {
      btn.name('Play');
    });
  };

  // add commands folder for touch screen devices
  _this.addCommandsFolder = function () {
    var folder = panel.addFolder('Commands');
    folder.add(this.parameters.cmd, 'rot').name('Orbit Animation').onChange(app.setRotateAnimationMode);
    folder.add(this.parameters.cmd, 'wf').name('Wireframe Mode').onChange(app.setWireframeMode);
  };

  _this.addHelpButton = function () {
    panel.add(this.parameters, 'i').name('Help');
  };
})();
