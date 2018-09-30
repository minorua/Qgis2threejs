"use strict";
// mobile.js
// (C) 2018 Minoru Akagi | MIT License
// https://github.com/minorua/Qgis2threejs

var orbitControls, devControls, oldFOV;
var ARMode = false;


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
        vasp = v.videoWidth / v.videoHeight,
        c = app.renderer.domElement;
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

app.cameraAction._moveTo = app.cameraAction.moveTo;
app.cameraAction.moveTo = function () {
  app.cameraAction._moveTo(app.queryTargetPosition.x,
                           -app.queryTargetPosition.z,
                           app.queryTargetPosition.y + DH * app.scene.userData.zScale);   // + device height from ground
};

function initControls() {
  orbitControls = app.controls;
  devControls = new THREE.DeviceOrientationControls(app.camera);
  devControls.alphaOffset = DECLINATION * Math.PI / 180;    // counter-clockwise

  oldFOV = app.camera.fov;
}

function initLayerList() {
  var list = document.getElementById("layerlist");
  var updateAllLayersCheckbox = function () {};

  if (false) {
    var item = document.createElement("div");
    item.innerHTML = "<input type='checkbox' checked>All layers";
    item.children[0].addEventListener("change", function () {
      for (var i = 1; i < list.children.length; i++) {
        list.children[i].children[0].checked = this.checked;
      }
      for (var id in app.scene.mapLayers) {
        app.scene.mapLayers[id].visible = this.checked;
      }
    });
    list.appendChild(item);

    updateAllLayersCheckbox = function () {
      var checked = 0, unchecked = 0;
      for (var i = 1; i < list.children.length; i++) {
        if (list.children[i].children[0].checked) checked++;
        else unchecked++;
      }
      if (checked && unchecked) list.children[0].children[0].indeterminate = true;
      else {
        list.children[0].children[0].indeterminate = false;
        list.children[0].children[0].checked = Boolean(checked);
      }
    };
  }

  Object.keys(app.scene.mapLayers).forEach(function (layerId) {
    var layer = app.scene.mapLayers[layerId];
    var item = document.createElement("div");
    item.innerHTML = "<div><input type='checkbox'" +
                     ((layer.properties.visible) ? " checked" : "") +
                     ">" + layer.properties.name + "</div><div><input type='range'><span></span></div>";

    // visibility checkbox
    item.querySelector("input[type=checkbox]").addEventListener("change", function () {
      layer.visible = this.checked;
      updateAllLayersCheckbox();
    });

    // opacity slider
    var slider = item.querySelector("input[type=range]"),
        label = item.querySelector("span"),
        o = parseInt(layer.opacity * 100);
    slider.value = o;
    slider.addEventListener("input", function () {
      label.innerHTML = this.value + " %";
    });
    slider.addEventListener("change", function () {
      label.innerHTML = this.value + " %";
      layer.opacity = this.value / 100;
    });
    label.innerHTML = o + " %";

    list.appendChild(item);
  });
}

function startARMode() {
  ARMode = true;
  app.camera.fov = FOV;
  app.camera.updateProjectionMatrix();
  app.camera.position.set(0, 30, 0);

  app.controls = devControls;
  orbitControls.enabled = false;
  devControls.connect();
  app.startAnimation();
  document.getElementById("current-location").classList.add("touchme");

  navigator.mediaDevices.enumerateDevices().then(function (devices) {
    // use "camera" facing "back" preferentially
    devices.sort(function (a, b) {
      var p = 0;
      if ((a.label || "").match(/camera/)) p -= 1;
      if ((b.label || "").match(/camera/)) p += 1;
      if ((a.label || "").match(/back/)) p -= 1;
      if ((b.label || "").match(/back/)) p += 1;
      return p;
    });

    var id = devices[0].deviceId;
    navigator.getUserMedia({video: {optional: [{sourceId: id}]}}, function (stream) {
      var v = document.getElementById("video");
      v.addEventListener("loadedmetadata", function () {
        app.eventListener.resize();
      });
      v.srcObject = stream;

      document.getElementById("webgl").classList.add("transparent");
    }, function (error) {
      alert(error);
    });
  }).catch(function (error) {
    alert(error.message);
  });
}

function stopARMode() {
  ARMode = false;

  app.controls = orbitControls;
  devControls.disconnect();
  app.stopAnimation();
  orbitControls.enabled = true;
  document.getElementById("current-location").classList.remove("touchme");

  app.camera.position.set(0, 100, 100);
  app.camera.lookAt(0, 0, 0);
  orbitControls.target.set(0, 0, 0);

  var v = document.getElementById("video");
  v.srcObject = null;

  document.getElementById("webgl").classList.remove("transparent");

  app.camera.fov = oldFOV;
  app.camera.updateProjectionMatrix();
  app.setCanvasSize(window.innerWidth, window.innerHeight);
}

function getCurrentPosition (callback) {
  app.popup.show("Fetching current location...");

  navigator.geolocation.getCurrentPosition(function (position) {
    // error message if failed to get current position
    var pos = position.coords;
    if (pos.longitude === undefined || pos.latitude === undefined || pos.altitude === undefined) {
      app.popup.show("Could not fetch current location.", "", false, 3000);
      return;
    }

    // get z coordinate of current location from DEM layer if scene has a DEM layer
    var layer, pt = app.scene.toLocalCoordinates(pos.longitude, pos.latitude, pos.altitude);
    for (var lyrId in app.scene.mapLayers) {
      layer = app.scene.mapLayers[lyrId];
      if (layer instanceof Q3D.DEMLayer) {
        var z = layer.getZ(pt.x, pt.y);
        if (z !== null) {
          pt.z = (z + DH) * app.scene.userData.zScale;
          break;
        }
      }
    }

    callback(pt);

    var msg = "Long.: " + pos.longitude +
              "<br>Lat.: " + pos.latitude +
              "<br>(Acc.: " + pos.accuracy +
              ")<br>(Alt.: " + pos.altitude +
              ")<br>(Alt. Acc.: " + pos.altitudeAccuracy + ")";
    app.popup.show(msg, "Current location", false, 5000);
  },
  function (error) {
    app.popup.hide();
    alert("Cannot get current location: " + error.message);
  },
  {enableHighAccuracy: true});
};

function moveToCurrentLocation() {
  // AR mode is on
  document.getElementById("current-location").classList.remove("touchme");

  getCurrentPosition(function (pt) {
    // move camera
    app.cameraAction.moveTo(pt.x, pt.y, pt.z);
  });
}

function zoomToCurrentLocation() {
  // AR mode is off
  getCurrentPosition(function (pt) {
    // indicate current position using query marker
    app.queryMarker.position.set(pt.x, pt.y, pt.z); // z-up
    app.queryMarker.visible = true;
    app.queryMarker.updateMatrixWorld();

    // zoom in on current position
    app.cameraAction.zoomInTo(pt.x, pt.y, pt.z);
  });
}

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

// layers, settings and info buttons
function hideAll() {
  document.getElementById("layerlist").classList.add("hidden");
  document.getElementById("layers-button").classList.remove("pressed");

  document.getElementById("settings").classList.add("hidden");
  document.getElementById("settings-button").classList.remove("pressed");

  app.popup.hide();
  document.getElementById("info-button").classList.remove("pressed");
}

document.getElementById("layers-button").addEventListener("click", function () {
  var hidden = document.getElementById("layerlist").classList.contains("hidden");
  hideAll();
  if (hidden) {
    document.getElementById("layerlist").classList.remove("hidden");
    document.getElementById("layers-button").classList.add("pressed");
  }
});

document.getElementById("settings-button").addEventListener("click", function () {
  var fov = document.getElementById("fov");
  var hidden = document.getElementById("settings").classList.contains("hidden");
  hideAll();
  if (hidden) {
    fov.value = FOV;
    document.getElementById("settings").classList.remove("hidden");
    document.getElementById("settings-button").classList.add("pressed");
  }
});

document.getElementById("settings-ok").addEventListener("click", function () {
  FOV = document.getElementById("fov").value;
  if (ARMode) {
    app.camera.fov = FOV;
    app.camera.updateProjectionMatrix();
  }

  hideAll();
});

document.getElementById("settings-cancel").addEventListener("click", function () {
  hideAll();
});

document.getElementById("info-button").addEventListener("click", function () {
  var active = document.getElementById("info-button").classList.contains("pressed");
  hideAll();
  if (!active) {
    app.showInfo();
    document.getElementById("info-button").classList.add("pressed");
  }
});

app.popup._hide = app.popup.hide;
app.popup.hide = function () {
  document.getElementById("info-button").classList.remove("pressed");
  app.popup._hide();
};
