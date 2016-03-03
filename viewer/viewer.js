var app = Q3D.application;

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
