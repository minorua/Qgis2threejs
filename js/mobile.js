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

function initControls() {
  orbitControls = app.controls;
  devControls = new THREE.DeviceOrientationControls(app.camera);
  devControls.alphaOffset = DECLINATION * Math.PI / 180;    // counter-clockwise

  oldFOV = app.camera.fov;
}

function startARMode() {
  ARMode = true;
  app.camera.fov = FOV;
  app.camera.updateProjectionMatrix();
  app.camera.position.set(0, 30, 0);

  app.controls = devControls;
  orbitControls.enabled = false;
  devControls.connect();

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
        moveToCurrentLocation();
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
  orbitControls.enabled = true;

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
      app.popup.show("Could not fetch current location.");
      setTimeout(function () {
        app.popup.hide();
      }, 3000);
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
    app.popup.show(msg, "Current location");
    setTimeout(function () {
      app.popup.hide();
    }, 5000);
  },
  function (error) {
    app.popup.hide();
    alert("Cannot get current location: " + error.message);
  },
  {enableHighAccuracy: true});
};

function moveToCurrentLocation() {
  // AR mode is on
  getCurrentPosition(function (pt) {
    // move camera
    app.camera.position.set(pt.x, pt.z, -pt.y);
  });
}

function zoomToCurrentLocation() {
  // AR mode is off
  getCurrentPosition(function (pt) {
    // indicate current position using query marker
    app.queryMarker.position.set(pt.x, pt.y, pt.z); // this is z-up
    app.queryMarker.visible = true;
    app.queryMarker.updateMatrixWorld();

    // zoom in on current position
    var x = pt.x,
        y = pt.y - 10.0,
        z = pt.z + 10.0;
    app.camera.position.set(x, z, -y);
    app.camera.lookAt(pt.x, pt.z, -pt.y);
    orbitControls.target.set(pt.x, pt.z, -pt.y);
  });
}

document.getElementById("ar-checkbox").addEventListener("change", function () {
  if (this.checked) startARMode();
  else stopARMode();
});

document.getElementById("current-location").addEventListener("click", function () {
  if (ARMode) moveToCurrentLocation();
  else zoomToCurrentLocation();
});

document.getElementById("layers-button").addEventListener("click", function () {
  alert("TODO");
});

document.getElementById("settings-button").addEventListener("click", function () {
  alert("TODO");
});

document.getElementById("info-button").addEventListener("click", function () {
  app.showInfo();
});
