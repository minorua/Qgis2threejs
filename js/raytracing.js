Object.assign(Q3D.Config, {
  bgColor: 0,
  lights: [
    {
      type: "ambient",
      color: 0xffffff,
      intensity: 0.6
    },
    {
      type: "directional",
      color: 0xffffff,
      intensity: 0.7,
      azimuth: 220,   // azimuth of light, in degrees.
      altitude: 45    // altitude angle in degrees.
    }
  ]
});

Object.assign(Q3D.gui.parameters, {
  lt: {
    amb: {
      i: Q3D.Config.lights[0].intensity
    },
    dir: {
      i: Q3D.Config.lights[1].intensity,
      s: 0.8,
      az: Q3D.Config.lights[1].azimuth,
      alt: Q3D.Config.lights[1].altitude
    }
  },
  ren: {
    c: "#ffffff",
    m: false,      // maximize hardware usage
    render: function () {
      var app = Q3D.application,
          gui = Q3D.gui;

      if (app.status == 0) {        // rendering has not started yet
        gui.renderButton.name('Starting...');

        app.rayRenderer.domElement.style.display = "block";
        app.rayRenderer.needsUpdate = true;

        setTimeout(function () {
          app.afrId = requestAnimationFrame(app.rayRenderingLoop);

          gui.renderButton.name('Stop Rendering');
          app.status = 1;
        }, 0);
      }
      else if (app.status == 1) {   // in rendering
        cancelAnimationFrame(app.afrId);
        app.afrId = null;

        gui.renderButton.name('Return to Preview');
        app.status = 2;
      }
      else if (app.status == 2) {   // rendering stopped
        app.rayRenderer.domElement.style.display = "none";

        gui.renderButton.name('Start Rendering');
        app.status = 0;
      }
    }
  },
  save: function () {   // set app.rayRenderer.preserveDrawingBuffer to true to use this function
    var a = document.createElement('a');
    a.href = app.rayRenderer.domElement.toDataURL();
    a.download = 'image.jpg';
    a.click();
  }
});


function init(container) {

  var app = Q3D.application,
      params = Q3D.gui.parameters;

  params.ren.w = container.clientWidth;
  params.ren.h = container.clientHeight;

  app.eventListener.resize = function () {};    // dat-gui panel has canvas size settings

  app.init(container);

  app.rayRenderer = new THREE.RayTracingRenderer();    // https://github.com/hoverinc/ray-tracing-renderer
  app.rayRenderer.setSize(container.clientWidth, container.clientHeight);
  app.rayRenderer.domElement.style.display = "none";
  container.appendChild(app.rayRenderer.domElement);

  app.afrId = null;
  app.status = 0;

  var statusElem = document.getElementById("footer");

  app.rayRenderingLoop = function (t) {
    app.afrId = requestAnimationFrame(app.rayRenderingLoop);

    app.rayRenderer.sync(t);
    app.rayRenderer.render(app.scene, app.camera);

    statusElem.innerHTML = "Rendered samples: " + app.rayRenderer.getTotalSamplesRendered();
  };

  app.scene.background = new THREE.Color().setStyle(params.ren.c);

  // shadow for preview
  app.renderer.shadowMap.enabled = true;
  app.renderer.shadowMap.type = THREE.VSMShadowMap;

  app.addEventListener("sceneLoaded", function () {
    var lightD = app.scene.lightGroup.children[1];    // (soft) directional light
    lightD.softness = params.lt.dir.s;

    var s = lightD.shadow,
        bw = app.scene.userData.width;

    s.camera.far = bw * 10;
    s.camera.top = s.camera.right = bw * 5;
    s.camera.bottom = s.camera.left = -bw * 5;
    s.mapSize.width = s.mapSize.height = 1024;

    app.scene.traverse(function (obj) {
      if (obj.isMesh) {
        obj.castShadow = true;
        obj.receiveShadow = true;
      }
      else if (obj.isDirectionalLight) {
        obj.castShadow = true;
      }
    });
    app.render();
  });

  app._setCanvasSize = app.setCanvasSize;
  app.setCanvasSize = function (w, h) {
    app._setCanvasSize(w, h);
    app.rayRenderer.setSize(w, h);
  };
}


Q3D.gui._init = Q3D.gui.init;

Q3D.gui.init = function () {

  this._init(false, {width: 340});

  this.layersFolder = this.gui.addFolder('Layers');
  this.lightsFolder = this.gui.addFolder('Lights');
  this.renderFolder = this.gui.addFolder('Render');
  this.addHelpButton();
};

Q3D.gui.initLayersFolder = function (scene) {
  var app = Q3D.application,
      mapLayers = scene.mapLayers,
      params = this.parameters;

  var visibleChanged = function (value) { mapLayers[this.object.i].visible = value; };
  var opacityChanged = function (value) { mapLayers[this.object.i].opacity = value; };
  var onMaterialChanged = function (value) {
    mapLayers[this.object.i].objectGroup.traverse(function (obj) {
      if (obj.isMesh) {
        obj.material.roughness = (value == 0) ? 1 : 0.3;
        obj.material.metalness = (value == 1) ? 1 : 0;
        obj.material.transparent = (value == 2) ? true : false;
      }
    });
    app.render();
  };

  var layer, subfolder;
  for (var layerId in mapLayers) {
    layer = mapLayers[layerId];
    params.lyr[layerId] = {
      i: layerId,
      v: layer.visible,
      o: layer.opacity,
      m: 0
    };
    subfolder = this.layersFolder.addFolder(layer.properties.name);
    subfolder.add(params.lyr[layerId], 'v').name('Visible').onChange(visibleChanged);
    subfolder.add(params.lyr[layerId], 'o').min(0).max(1).name('Opacity').onChange(opacityChanged);
    subfolder.add(params.lyr[layerId], 'm', {'Clay (Matte)': 0, 'Metal': 1, 'Glass': 2}).name('Material Type').onChange(onMaterialChanged);
  }

  this.customPlaneFolder = this.layersFolder.addFolder('Custom Plane');

  return this.layersFolder;
};

Q3D.gui.initLightsFolder = function(scene) {

  var app = Q3D.application,
      params = this.parameters,
      lights = scene.lightGroup.children,
      lightA = lights[0],
      lightD = lights[1];

  var subfolder;
  subfolder = this.lightsFolder.addFolder('Ambient');
  subfolder.add(params.lt.amb, 'i').min(0).max(1).name('Intensity').onChange(function (value) {
    lightA.intensity = value;
    app.render();
  });

  subfolder = this.lightsFolder.addFolder('Directional');
  subfolder.add(params.lt.dir, 'i').min(0).max(1).name('Intensity').onChange(function (value) {
    lightD.intensity = value;
    app.render();
  });
  subfolder.add(params.lt.dir, 's').min(0).max(1).name('Softness').onChange(function (value) {
    lightD.softness = value;
    app.render();
  });

  var deg2rad = Math.PI / 180,
      dist = scene.userData.width;

  var dirChanged = function (value) {

    var lambda = (90 - params.lt.dir.az) * deg2rad,
        phi = params.lt.dir.alt * deg2rad;

    lightD.position.set(Math.cos(phi) * Math.cos(lambda),
                        Math.cos(phi) * Math.sin(lambda),
                        Math.sin(phi)).multiplyScalar(dist);
    lightD.updateMatrixWorld();
    app.render();
  };

  subfolder.add(params.lt.dir, 'az').min(0).max(359).name('Azimuth').onChange(dirChanged);
  subfolder.add(params.lt.dir, 'alt').min(0).max(90).name('Altitude Angle').onChange(dirChanged);

  dirChanged();

  return this.lightsFolder;
};

Q3D.gui.initRenderFolder = function () {

  var app = Q3D.application,
      params = this.parameters;

  this.renderFolder.addColor(params.ren, 'c').name('Background color').onChange(function (value) {
    app.scene.background.setStyle(value);
    app.render();
  });

  var sizeChanged = function (v) {
    app.setCanvasSize(params.ren.w, params.ren.h);
    app.render();
  };
  this.renderFolder.add(params.ren, 'w').min(100).max(10000).name('Width').onChange(sizeChanged);
  this.renderFolder.add(params.ren, 'h').min(100).max(10000).name('Height').onChange(sizeChanged);

  this.renderFolder.add(params.ren, 'm').name('Max hardware usage').onChange(function (value) {
    app.rayRenderer.maxHardwareUsage = value;
  });

  this.renderButton = this.renderFolder.add(params.ren, 'render').name('Start Rendering');
  // this.renderFolder.add(params, 'save').name('Save Image');
  this.renderFolder.open();
};

Q3D.gui.customPlaneMaterial = function (color) {
  return new THREE.MeshStandardMaterial({color: color, roughness: 1});
};

Q3D.gui._initCustomPlaneFolder = Q3D.gui.initCustomPlaneFolder;
Q3D.gui.initCustomPlaneFolder = function (zMin, zMax) {

  Q3D.gui._initCustomPlaneFolder(zMin, zMax);

  var params = this.parameters;
  params.cp.m = 0;

  this.customPlaneFolder.add(params.cp, 'm', {'Clay (Matte)': 0, 'Metal': 1, 'Glass': 2}).name('Material Type').onChange(function (value) {
    var mtl = Q3D.gui.customPlane.material;
    mtl.roughness = (value == 0) ? 1 : 0.3;
    mtl.metalness = (value == 1) ? 1 : 0;
    mtl.transparent = (value == 2) ? true : false;
    Q3D.application.render();
  });
};

Q3D.Material.prototype._loadJSONObject = Q3D.Material.prototype.loadJSONObject;
Q3D.Material.prototype.loadJSONObject = function (jsonObject, callback) {

  if (jsonObject.type > Q3D.MaterialType.MeshToon) {  // && jsonObject.type != Q3D.MaterialType.MeshStandard
    console.warning("This material is not supported by ray tracing renderer: " + jsonObject.type);
  }
  else {
    if (jsonObject.roughness === undefined) jsonObject.roughness = 1;

    jsonObject.roughness = 1;
    jsonObject.metalness = 0;
    jsonObject.t = false;   // transparent
    jsonObject.type = Q3D.MaterialType.MeshStandard;
  }

  this._loadJSONObject(jsonObject, callback);
};
