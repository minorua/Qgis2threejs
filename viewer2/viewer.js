var app = Q3D.application;
var featAdded = false;    // if no feature has been added, plugin layer will not update intermediate image

// this is the slot connected to the signal which Bridge class object emits
function dataReceived(jsonObject) {
  app.loadJSONObject(jsonObject);
}

// fps display
app.timer = {
  tickCount: 0,
  last: Date.now()
};
window.setInterval(function () {
  var now = Date.now(),
      elapsed = now - app.timer.last,
      fps = app.timer.tickCount / elapsed * 1000;

  document.getElementById("fps").innerHTML = "FPS: " + Math.round(fps);

  app.timer.last = now;
  app.timer.tickCount = 0;
}, 1000);

// overrides
// TODO: var origAnimate = app.animate;
app.animate = function () {
  if (app.running) requestAnimationFrame(app.animate);
  if (app.controls) app.controls.update();
  app.render();
  app.timer.tickCount++;
};

app.setCanvasSize = function (width, height) {
  app.width = width;
  app.height = height;
  //app.camera.aspect = width / height;
  app.camera.updateProjectionMatrix();
  app.renderer.setSize(width, height);
};

Q3D.Project.prototype.update = function (params) {
  for (var k in params) {
    this[k] = params[k];
  }

  var w = (this.baseExtent[2] - this.baseExtent[0]),
      h = (this.baseExtent[3] - this.baseExtent[1]);

  this.height = this.width * h / w;
  this.scale = this.width / w;
  this.zScale = this.scale * this.zExaggeration;

  this.origin = {x: this.baseExtent[0] + w / 2,
                 y: this.baseExtent[1] + h / 2,
                 z: -this.zShift};

  //this.layers = [];
  //this.models = [];
  //this.images = [];
};

Q3D.Project.prototype.setLayer = function (index, layer) {
  app.scene.remove(this.layers[index].objectGroup)
  // TODO: remove labels from app

  layer.index = index;
  layer.project = this;
  this.layers[index] = layer;

  app.queryObjNeedsUpdate = true;
  return layer;
};

function addFeat(layerIndex, f) {
  var layer = project.layers[layerIndex],
      fid = layer.f.length;
  layer.f.push(f);

  if (fid) layer.build(undefined, fid);
  else layer.build(app.scene);
  featAdded = true;
}

function createMaterials(layerIndex) {
  project.layers[layerIndex].createMaterials();
}
