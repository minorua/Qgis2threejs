// a polyfill for three.min.js (r90)
if (typeof ImageBitmap === "undefined") ImageBitmap = HTMLImageElement;

// a polyfill for GLTFExporter.js (r90)
Array.prototype.fill = function (value) {
  var O = Object(this),
      len = O.length >>> 0;
  for (var k = 0; k < len; k++) {
    O[k] = value;
  }
  return O;
};

// WebKit bridge: access to pyObj object
function fetchData() {
  return pyObj.data();
}


var app = Q3D.application;
app.timer = {tickCount: 0};


function loadJSONObject(jsonObject) {
  app.loadJSONObject(jsonObject);

  if (jsonObject.type == "scene" && jsonObject.properties !== undefined) {
    updateNorthArrowRotation(jsonObject.properties.rotation);
  }
}

function loadScriptFile(url, callback) {
  for (var elm in document.head.getElementsByTagName("script")) {
    if (elm.src == url) {
      if (callback) callback();
      return false;
    }
  }

  var s = document.createElement("script");
  s.src = url;
  if (callback) s.onload = callback;
  document.head.appendChild(s);
  return true;
}

function loadModel(url) {
  function loadToScene(res) {
    var boxsize = new THREE.Box3().setFromObject(res.scene).getSize(),
        scale = 50 / Math.max(boxsize.x, boxsize.y, boxsize.z);

    var parent = new THREE.Group();
    parent.scale.set(scale, scale, scale);
    parent.rotation.x = Math.PI / 2;
    parent.add(res.scene);
    app.scene.add(parent);

    console.log(url + " loaded. scale = " + scale);
    showMessageBar('Model preview: Successfully loaded "' + url.split("/").pop() + '". See console for details.', 3000);

    app.setIntervalRender(250, 20);
  }
  function onError(e) {
    console.log(e.message);
    showMessageBar('Model preview: Failed to load "' + url.split("/").pop() + '". See console for details.', 5000, true);
  }

  var ext = url.split(".").pop();
  if (ext == "dae") {
    loadScriptFile("../js/threejs/loaders/ColladaLoader.js", function () {
      var loader = new THREE.ColladaLoader();
      loader.load(url, loadToScene, undefined, onError);
    });
  }
  else if (ext == "gltf" || ext == "glb") {
    loadScriptFile("../js/polyfill/polyfill.min.js", function () {
      loadScriptFile("../js/threejs/loaders/GLTFLoader.js", function () {
        var loader = new THREE.GLTFLoader();
        loader.load(url, loadToScene, undefined, onError);
      });
    });
  }
}

function init() {
  var container = document.getElementById("view");
  app.init(container, false);

  if (Q3D.Config.northArrow.visible) {
    app.buildNorthArrow(document.getElementById("northarrow"), 0);
  }

  // check extension support of web view
  // see https://github.com/minorua/Qgis2threejs/issues/147
  var gl = app.renderer.context;    // WebGLRenderingContext
  if (gl.getExtension("WEBGL_depth_texture") === null) {
    var msg = "Any 3D objects not rendered? There is a compatibility issue with QGIS 3D view. " +
              "You need to restart QGIS to use preview.";
    showMessageBar(msg, undefined, true);
  }
}

function displayFPS() {
  app.timer.last = Date.now();

  window.setInterval(function () {
    var now = Date.now(),
        elapsed = now - app.timer.last,
        fps = app.timer.tickCount / elapsed * 1000;

    document.getElementById("fps").innerHTML = "FPS: " + Math.round(fps);

    app.timer.last = now;
    app.timer.tickCount = 0;
  }, 1000);
}

function saveModelAsGLTF(filename) {
  console.log("Saving model to " + filename);

  var scene = new THREE.Scene(), layer, group;
  for (var k in app.scene.mapLayers) {
    layer = app.scene.mapLayers[k];
    group = layer.objectGroup;
    group.rotation.set(-Math.PI / 2, 0, 0);
    group.name = layer.properties.name;
    scene.add(group);
  }
  scene.updateMatrixWorld();

  var options = {
    binary: (filename.split(".").pop().toLowerCase() == "glb"),
    onlyVisible: true
    //trs: true/false,
    //truncateDrawRange: true/false,
  };

  var gltfExporter = new THREE.GLTFExporter();
  gltfExporter.parse(scene, function(result) {

    if (result instanceof ArrayBuffer) {
      pyObj.saveBytes(new Uint8Array(result), filename);
    }
    else {
      pyObj.saveString(JSON.stringify(result, null, 2), filename);
    }
    console.log("Model has been saved.");
    showMessageBar("Successfully saved the model.", 5000);

    // restore preview
    for (var k in app.scene.mapLayers) {
      layer = app.scene.mapLayers[k];
      group = layer.objectGroup;
      group.rotation.set(0, 0, 0);
      app.scene.add(group);
    }
    app.scene.updateMatrixWorld();
    app.render();
  }, options);
}

var barTimerId = null;
function showMessageBar(message, duration, warning) {
  if (barTimerId !== null) {
    clearTimeout(barTimerId);
    barTimerId = null;
  }
  if (duration) {
    barTimerId = setTimeout(closeMessageBar, duration);
  }
  var e = document.getElementById("messagebar");
  e.innerHTML = message;
  e.style.display = "block";
  if (warning) {
    e.classList.add("warning");
  }
  else {
    e.classList.remove("warning");
  }
}

function closeMessageBar() {
  document.getElementById("messagebar").style.display = "none";
  barTimerId = null;
}

function setBackgroundColor(color, alpha) {
  app.renderer.setClearColor(color, alpha);
  app.render();
}

function switchCamera(is_ortho) {
  app.buildCamera(is_ortho);
  app.controls.object = app.camera;
  console.log("Camera switched to " + ((is_ortho) ? "orthographic" : "perspective") + " camera.")
  app.render(true);
}

function setNorthArrowVisible(visible) {
  document.getElementById("northarrow").style.display = (visible) ? "block" : "none";
  if (visible && app.scene2 === undefined) {
    app.buildNorthArrow(document.getElementById("northarrow"), app.scene.userData.rotation);
    app.render();
  }
}

function setNorthArrowColor(color) {
  if (app.scene2 === undefined) {
    Q3D.Config.northArrow.color = color;
  }
  else {
    app.scene2.children[app.scene2.children.length - 1].material.color = new THREE.Color(color);
    app.render();
  }
}

function updateNorthArrowRotation(rotation) {
  if (app.scene2 === undefined) return;

  var mesh = app.scene2.children[app.scene2.children.length - 1];
  mesh.rotation.z = -rotation * Math.PI / 180;
  mesh.updateMatrixWorld();
}

function setFooterLabel(html) {
  document.getElementById("footer").innerHTML = html;
}

// overrides
var origRender = app.render;
app.render = function (updateControls) {
  origRender(updateControls);
  app.timer.tickCount++;
};

app._saveCanvasImage = app.saveCanvasImage;
app.saveCanvasImage = function (width, height, fill_background) {
  var saveCanvasImage = function (canvas) {
    pyObj.saveImage(width, height, canvas.toDataURL("image/png"));
    app.popup.hide();
  };
  app._saveCanvasImage(width, height, fill_background, saveCanvasImage);
};
