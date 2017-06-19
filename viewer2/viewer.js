var app = Q3D.application;

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
var origRender = app.render;
app.render = function () {
  origRender();
  app.timer.tickCount++;
};

app.setCanvasSize = function (width, height) {
  app.width = width;
  app.height = height;
  //app.camera.aspect = width / height;
  app.camera.updateProjectionMatrix();
  app.renderer.setSize(width, height);
};
