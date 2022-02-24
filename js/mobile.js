// (C) 2018 Minoru Akagi
// SPDX-License-Identifier: MIT

"use strict";

Q3D.Config.AR = {
  DH: 1.5,      // device height from ground (in CRS vertical unit)
  FOV: 70,      // device camera's field of view
  MND: 0        // magnetic North direction (clockwise from upper direction of map, in degrees)
};

var app = Q3D.application,
    ARMode = false;
var orbitControls, devControls, oldFOV;


app.start = function () {
  if (ARMode) devControls.connect();
  else orbitControls.enabled = true;
};

app.pause = function () {
  if (ARMode) devControls.disconnect();
  else orbitControls.enabled = false;
};

app.resume = function () {
  if (ARMode) devControls.connect();
  else orbitControls.enabled = true;
};

app.eventListener.resize = function () {
  var width, height;
  if (ARMode) {
    var v = document.getElementById("video"),
        asp = window.innerWidth / window.innerHeight,
        vasp = v.videoWidth / v.videoHeight;
    if (vasp > asp) {
      width = window.innerWidth;
      height = parseInt(width / vasp);
    }
    else {
      height = window.innerHeight;
      width = parseInt(height * vasp);
    }
  }
  else {
    width = window.innerWidth;
    height = window.innerHeight;
  }
  app.setCanvasSize(width, height);
  app.render();
};

app.cameraAction._move = app.cameraAction.move;
app.cameraAction.move = function () {
  app.cameraAction._move(app.queryTargetPosition.x,
                         app.queryTargetPosition.y,
                         app.queryTargetPosition.z + Q3D.Config.AR.DH * app.scene.userData.zScale);   // + device height from ground
};

app._setRotateAnimationMode = app.setRotateAnimationMode;
app.setRotateAnimationMode = function (enabled) {
  app._setRotateAnimationMode(enabled);
  document.getElementById("stop-button").style.display = (enabled) ? "block" : "none";
};


function init() {
  orbitControls = app.controls;
  devControls = new THREE.DeviceOrientationControls(app.camera);
  devControls.alphaOffset = -Q3D.Config.AR.MND * Math.PI / 180;    // counter-clockwise, in radians

  // store default camera FOV (non-AR mode)
  oldFOV = app.camera.fov;

  // load settings from local storage
  try {
    var data = JSON.parse(localStorage.getItem("Qgis2threejs"));
    if (data) {
      Q3D.Config.AR.FOV = data.fov;
    }
  }
  catch (e) {
    console.log(e);
  }

  // add event listeners
  // AR mode switch
  document.getElementById("ar-checkbox").addEventListener("change", function () {
    if (this.checked) startARMode();
    else stopARMode();
  });

  // current location button
  document.getElementById("current-location").addEventListener("click", function () {
    if (ARMode) moveToCurrentLocation();
    else zoomToCurrentLocation();
  });

  // layers button
  document.getElementById("layers-button").addEventListener("click", function () {
    var panel = Q3D.gui.layerPanel;
    if (!panel.initialized) panel.init();

    var visible = panel.isVisible();
    hideAll();

    if (visible) panel.hide();
    else {
      panel.show();
      document.getElementById("layers-button").classList.add("pressed");
    }
  });

  // settings button
  document.getElementById("settings-button").addEventListener("click", function () {
    var fov = document.getElementById("fov");
    var visible = document.getElementById("settings").classList.contains("visible");
    hideAll();
    if (!visible) {
      fov.value = Q3D.Config.AR.FOV;
      document.getElementById("settings").classList.add("visible");
      document.getElementById("settings-button").classList.add("pressed");
    }
  });

  document.getElementById("settings-ok").addEventListener("click", function () {
    Q3D.Config.AR.FOV = document.getElementById("fov").value;
    if (ARMode) {
      app.camera.fov = Q3D.Config.AR.FOV;
      app.camera.updateProjectionMatrix();
    }

    hideAll();

    // save settings in local storage
    try {
      if (document.getElementById("save-in-storage").checked) {
        var data = {
          fov: Q3D.Config.AR.FOV
        };
        localStorage.setItem("Qgis2threejs", JSON.stringify(data));
      }
    }
    catch (e) {
      console.log(e);
    }
  });

  document.getElementById("settings-cancel").addEventListener("click", function () {
    hideAll();
  });

  // information (about) button
  document.getElementById("info-button").addEventListener("click", function () {
    var active = document.getElementById("info-button").classList.contains("pressed");
    hideAll();
    if (!active) {
      Q3D.gui.showInfo();
      document.getElementById("info-button").classList.add("pressed");
    }
  });

  // stop button
  document.getElementById("stop-button").addEventListener("click", function () {
    app.setRotateAnimationMode(false);
  });
}

function startARMode(position) {
  ARMode = true;
  app.camera.fov = Q3D.Config.AR.FOV;
  app.camera.updateProjectionMatrix();

  if (typeof position === "undefined") {
    app.camera.position.set(0, 0, 30);
    document.getElementById("current-location").classList.add("touchme");
  }
  else {
    app.camera.position.copy(position);
  }

  if (Q3D.Config.bgColor !== null) {
    app.renderer.setClearColor(0, 0);
  }

  if (orbitControls.autoRotate) {
    app.setRotateAnimationMode(false);
  }
  orbitControls.enabled = false;

  app.controls = devControls;
  app.controls.connect();

  app.animation.start();

  navigator.mediaDevices.getUserMedia({video: {facingMode: "environment"}}).then(function (stream) {
    var v = document.getElementById("video");
    v.addEventListener("loadedmetadata", function () {
      app.eventListener.resize();
    });
    v.srcObject = stream;

    document.getElementById("view").classList.add("transparent");
  }).catch(function (error) {
    alert(error);
  });

  document.querySelectorAll(".action-move").forEach(function (elm) {
    elm.classList.toggle("hidden");
  });
  document.querySelector(".action-zoom").classList.add("hidden");
  document.querySelector(".action-orbit").classList.add("hidden");
}

function startARModeHere() {
  var vec3 = new THREE.Vector3();
  vec3.copy(app.queryTargetPosition);
  vec3.z += Q3D.Config.AR.DH * app.scene.userData.zScale;
  startARMode(vec3);
  document.getElementById("ar-checkbox").checked = true;
}

function moveHere() {
  app.camera.position.copy(app.queryTargetPosition);
  app.camera.position.z += Q3D.Config.AR.DH * app.scene.userData.zScale;
}

function stopARMode() {
  ARMode = false;

  devControls.disconnect();

  app.controls = orbitControls;
  app.controls.enabled = true;

  app.animation.stop();
  document.getElementById("current-location").classList.remove("touchme");

  var v = Q3D.Config.viewpoint,
      p = v.pos,
      t = v.lookAt;
  app.camera.position.set(p.x, p.y, p.z);
  app.camera.lookAt(t.x, t.y, t.z);
  app.controls.target.set(t.x, t.y, t.z);

  var v = document.getElementById("video");
  v.srcObject = null;

  document.getElementById("view").classList.remove("transparent");

  app.camera.fov = oldFOV;
  app.camera.updateProjectionMatrix();
  app.setCanvasSize(window.innerWidth, window.innerHeight);

  if (Q3D.Config.bgColor !== null) app.renderer.setClearColor(Q3D.Config.bgColor || 0, 1);

  document.querySelectorAll(".action-move").forEach(function (elm) {
    elm.classList.toggle("hidden");
  });
  document.querySelector(".action-zoom").classList.remove("hidden");
  document.querySelector(".action-orbit").classList.remove("hidden");
}

function getCurrentPosition (callback) {
  Q3D.gui.popup.show("Fetching current location...");

  navigator.geolocation.getCurrentPosition(function (position) {
    // error message if failed to get current position
    var pos = position.coords;
    if (pos.longitude === undefined || pos.latitude === undefined || pos.altitude === undefined) {
      Q3D.gui.popup.show("Could not fetch current location.", "", false, 3000);
      return;
    }

    // get z coordinate of current location from DEM layer if scene has a DEM layer
    var layer, pt = app.scene.toWorldCoordinates({x: pos.longitude, y: pos.latitude, z: pos.altitude}, true);
    for (var lyrId in app.scene.mapLayers) {
      layer = app.scene.mapLayers[lyrId];
      if (layer instanceof Q3D.DEMLayer) {
        var z = layer.getZ(pt.x, pt.y);
        if (z !== null) {
          pt.z = (z + Q3D.Config.AR.DH + app.scene.userData.zShift) * app.scene.userData.zScale;
          break;
        }
      }
    }

    callback(pt);

    var acc = Number.parseFloat(pos.accuracy);
    acc = (acc > 2) ? acc.toFixed(0) : acc.toFixed(1);
    var msg = "Accuracy: <span class='accuracy'>" + acc + "</span>m";
    Q3D.gui.popup.show(msg, "Current location", false, 5000);
  },
  function (error) {
    Q3D.gui.popup.hide();
    alert("Cannot get current location: " + error.message);
  },
  {enableHighAccuracy: true});
}

function moveToCurrentLocation() {
  // AR mode is on
  document.getElementById("current-location").classList.remove("touchme");

  getCurrentPosition(function (pt) {
    // move camera
    app.cameraAction.move(pt.x, pt.y, pt.z);
  });
}

function zoomToCurrentLocation() {
  // AR mode is off
  getCurrentPosition(function (pt) {
    // indicate current position using query marker
    app.queryMarker.position.set(pt.x, pt.y, pt.z);
    app.queryMarker.visible = true;
    app.queryMarker.updateMatrixWorld();

    // zoom in on current position
    app.cameraAction.zoom(pt.x, pt.y, pt.z);
  });
}

// layers, settings and info buttons
function hideAll() {
  document.getElementById("layers-button").classList.remove("pressed");
  document.getElementById("settings-button").classList.remove("pressed");
  document.getElementById("info-button").classList.remove("pressed");

  document.getElementById("settings").classList.remove("visible");

  Q3D.gui.clean();
}

Q3D.gui.popup._hide = Q3D.gui.popup.hide;
Q3D.gui.popup.hide = function () {
  document.getElementById("info-button").classList.remove("pressed");
  Q3D.gui.popup._hide();
};

Q3D.gui.layerPanel._hide = Q3D.gui.layerPanel.hide;
Q3D.gui.layerPanel.hide = function () {
  document.getElementById("layers-button").classList.remove("pressed");
  Q3D.gui.layerPanel._hide();
};
