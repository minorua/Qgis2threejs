Q3D.Options.bgcolor = null;
app.start = function () {
  if (app.controls) app.controls.connect();
};

function startARMode() {
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
        var asp = window.innerWidth / window.innerHeight,
            vasp = v.videoWidth / v.videoHeight,
            c = app.renderer.domElement;

        var width, height;
        if (vasp > asp) {
          width = window.innerWidth;
          height = parseInt(width / vasp);
        }
        else {
          height = window.innerHeight;
          width = parseInt(height * vasp);
        }
        app.setCanvasSize(width, height);
      });
      v.srcObject = stream;
    }, function (error) {
      alert(error);
    });
  }).catch(function (error) {
    alert(error.message);
  });
}

function stopARMode() {
  // TODO
  var v = document.getElementById("video");
  v.srcObject = null;
  app.setCanvasSize(window.innerWidth, window.innerHeight);
}

function moveToCurrentLocation() {
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

    // move camera
    app.camera.position.set(pt.x, pt.z, -pt.y);

    var msg = "Long.: " + pos.longitude +
              "<br>Lat.: " + pos.latitude +
              "<br>(Acc.: " + pos.accuracy +
              ")<br>(Alt.: " + pos.altitude +
              ")<br>(Alt. Acc.: " + pos.altitudeAccuracy + ")";
    app.popup.show(msg, "Camera position updated");
    setTimeout(function () {
      app.popup.hide();
    }, 10000);
  },
  function (error) {
    app.popup.hide();
    alert("Cannot get your current location: " + error.message);
  },
  {enableHighAccuracy: true});
}

document.getElementById("camera-checkbox").addEventListener("change", function () {
  if (this.checked) startARMode();
  else stopARMode();
});

document.getElementById("current-location").addEventListener("click", moveToCurrentLocation);
document.getElementById("info-button").addEventListener("click", function () {
  alert("TODO");
  app.showInfo();
});


