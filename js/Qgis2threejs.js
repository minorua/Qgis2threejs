// (C) 2014 Minoru Akagi
// SPDX-License-Identifier: MIT
// https://github.com/minorua/Qgis2threejs

"use strict";

var Q3D = {
  VERSION: "2.7",
  application: {},
  gui: {}
};

Q3D.Config = {

  // renderer
  renderer: {
    hiDpi: true       // HD-DPI support
  },

  texture: {
    anisotropy: -4    // zero means max available value. negative value means max / -v.
  },

  // scene
  autoAdjustCameraPos: true,  // automatic camera height adjustment
  bgColor: null,              // null is sky

  // camera
  orthoCamera: false,
  viewpoint: {      // z-up
    default: {      // assumed that origin is (0, 0, 0) and base extent width in 3D world coordinates is 1
      pos: new THREE.Vector3(0, -1, 1),
      lookAt: new THREE.Vector3()
    }
  },

  // light
  lights: {
    directional: [
      {
        type: "ambient",
        color: 0x999999,
        intensity: 0.8
      },
      {
        type: "directional",
        color: 0xffffff,
        intensity: 0.7,
        azimuth: 220,   // azimuth of light, in degrees. default light azimuth of gdaldem hillshade is 315.
        altitude: 45    // altitude angle in degrees.
      }
    ],
    point: [
      {
        type: "ambient",
        color: 0x999999,
        intensity: 0.9
      },
      {
        type: "point",
        color: 0xffffff,
        intensity: 0.6,
        height: 10
      }
    ]
  },

  // layer
  allVisible: false,   // set every layer visible property to true on load if set to true

  line: {
    dash: {
      dashSize: 1,
      gapSize: 0.5
    }
  },

  label: {
    visible: true,
    canvasHeight: 64,
    clickable: true
  },

  // widgets
  navigation: {
    enabled: true
  },

  northArrow: {
    color: 0x8b4513,
    cameraDistance: 30,
    enabled: false
  },

  // animation
  animation: {
    enabled: false,
    startOnLoad: false,
    easingCurve: "Cubic"
  },

  // others
  qmarker: {
    radius: 0.004,
    color: 0xffff00,
    opacity: 0.8,
    k: 0.2    // size factor for ortho camera
  },

  measure: {
    marker: {
      radius: 0.004,
      color: 0xffff00,
      opacity: 0.5
      /* k: 0.2 */
    },
    line: {
      color: 0xffff00
    }
  },

  coord: {
    visible: true,
    latlon: false
  },

  potree: {},

  debugMode: false
};

// consts
Q3D.LayerType = {
  DEM: "dem",
  Point: "point",
  Line: "line",
  Polygon: "polygon",
  PointCloud: "pc"
};

Q3D.MaterialType = {
  MeshLambert: 0,
  MeshPhong: 1,
  MeshToon: 2,
  Line: 3,
  MeshLine: 4,
  Sprite: 5,
  Point: 6,
  MeshStandard: 7,
  Unknown: -1
};

Q3D.KeyframeType = {
  CameraMotion: 64,
  Opacity: 65,
  Texture: 66,
  GrowingLine: 67
};

Q3D.uv = {
  i: new THREE.Vector3(1, 0, 0),
  j: new THREE.Vector3(0, 1, 0),
  k: new THREE.Vector3(0, 0, 1)
};

Q3D.deg2rad = Math.PI / 180;

Q3D.ua = window.navigator.userAgent.toLowerCase();
Q3D.isIE = (Q3D.ua.indexOf("msie") != -1 || Q3D.ua.indexOf("trident") != -1);
Q3D.isTouchDevice = ("ontouchstart" in window);

Q3D.E = function (id) {
  return document.getElementById(id);
};

/*
Q3D.Group -> THREE.Group -> THREE.Object3D
*/
Q3D.Group = function () {
  THREE.Group.call(this);
};

Q3D.Group.prototype = Object.create(THREE.Group.prototype);
Q3D.Group.prototype.constructor = Q3D.Group;

Q3D.Group.prototype.add = function (object) {
  THREE.Group.prototype.add.call(this, object);
  object.updateMatrixWorld();
};

Q3D.Group.prototype.clear = function () {
  for (var i = this.children.length - 1; i >= 0; i--) {
    this.remove(this.children[i]);
  }
};

/*
Q3D.application
*/
(function () {
  var app = Q3D.application,
      gui = Q3D.gui,
      conf = Q3D.Config,
      E = Q3D.E;

  var vec3 = new THREE.Vector3();

  var listeners = {};
  app.dispatchEvent = function (event) {
    var ls = listeners[event.type] || [];
    for (var i = 0; i < ls.length; i++) {
      ls[i](event);
    }
  };

  app.addEventListener = function (type, listener, prepend) {
    listeners[type] = listeners[type] || [];
    if (prepend) {
      listeners[type].unshift(listener);
    }
    else {
      listeners[type].push(listener);
    }
  };

  app.removeEventListener = function (type, listener) {
    var array = listeners[type];
    if (array !== undefined) {
      var idx = array.indexOf(listener);
      if (idx !== -1) array.splice(idx, 1);
    }
  };

  app.init = function (container) {

    app.container = container;

    app.selectedObject = null;
    app.highlightObject = null;

    app.modelBuilders = [];
    app._wireframeMode = false;

    // URL parameters
    var params = app.parseUrlParameters();
    app.urlParams = params;

    if ("popup" in params) {
      // open popup window
      var c = window.location.href.split("?");
      window.open(c[0] + "?" + c[1].replace(/&?popup/, ""), "popup", "width=" + params.width + ",height=" + params.height);
      gui.popup.show("Another window has been opened.");
      return;
    }

    if (params.hiDpi == "no") conf.renderer.hiDpi = false;
    if (params.anisotropy) conf.texture.anisotropy = parseFloat(params.anisotropy);

    if (params.cx !== undefined) conf.viewpoint.pos = new THREE.Vector3(parseFloat(params.cx), parseFloat(params.cy), parseFloat(params.cz));
    if (params.tx !== undefined) conf.viewpoint.lookAt  = new THREE.Vector3(parseFloat(params.tx), parseFloat(params.ty), parseFloat(params.tz));

    if (params.width && params.height) {
      container.style.width = params.width + "px";
      container.style.height = params.height + "px";
    }

    app.width = container.clientWidth;
    app.height = container.clientHeight;

    var bgcolor = conf.bgColor;
    if (bgcolor === null) container.classList.add("sky");

    // WebGLRenderer
    app.renderer = new THREE.WebGLRenderer({alpha: true, antialias: true});

    if (conf.renderer.hiDpi) {
      app.renderer.setPixelRatio(window.devicePixelRatio);
    }

    app.renderer.setSize(app.width, app.height);
    app.renderer.setClearColor(bgcolor || 0, (bgcolor === null) ? 0 : 1);
    app.container.appendChild(app.renderer.domElement);

    if (conf.texture.anisotropy <= 0) {
      var maxAnis = app.renderer.capabilities.getMaxAnisotropy() || 1;

      if (conf.texture.anisotropy == 0) {
        conf.texture.anisotropy = maxAnis;
      }
      else {
        conf.texture.anisotropy = (maxAnis > -conf.texture.anisotropy) ? -maxAnis / conf.texture.anisotropy : 1;
      }
    }

    // outline effect
    if (THREE.OutlineEffect !== undefined) app.effect = new THREE.OutlineEffect(app.renderer);

    // scene
    app.scene = new Q3D.Scene();

    app.scene.addEventListener("renderRequest", function (event) {
      app.render();
    });

    app.scene.addEventListener("cameraUpdateRequest", function (event) {
      app.camera.position.copy(event.pos);
      app.camera.lookAt(event.focal);
      if (app.controls.target !== undefined) app.controls.target.copy(event.focal);
      if (app.controls.saveState !== undefined) app.controls.saveState();

      if (event.far !== undefined) {
        app.camera.near = (app.camera.isOrthographicCamera) ? 0 : event.near;
        app.camera.far = event.far;
        app.camera.updateProjectionMatrix();
      }
    });

    app.scene.addEventListener("lightChanged", function (event) {
      if (event.light == "point") {
        app.scene.add(app.camera);
        app.camera.add(app.scene.lightGroup);
      }
      else {    // directional
        app.scene.remove(app.camera);
        app.scene.add(app.scene.lightGroup);
      }
    });

    app.scene.addEventListener("mapRotationChanged", function (event) {
      if (app.scene2) {
        app.scene2.lightGroup.clear();
        app.scene2.buildLights(Q3D.Config.lights.directional, event.rotation);
      }
    });

    // camera
    app.buildCamera(conf.orthoCamera);

    // controls
    if (THREE.OrbitControls) {
      app.controls = new THREE.OrbitControls(app.camera, app.renderer.domElement);

      app.controls.addEventListener("change", function (event) {
        app.render();
      });

      app.controls.update();
    }

    // navigation
    if (conf.navigation.enabled && typeof ViewHelper !== "undefined") {
      app.buildViewHelper(E("navigation"));
    }

    // north arrow
    if (conf.northArrow.enabled) {
      app.buildNorthArrow(E("northarrow"));
    }

    // labels
    app.labelVisible = conf.label.visible;

    // create a marker for queried point
    var opt = conf.qmarker;
    app.queryMarker = new THREE.Mesh(new THREE.SphereBufferGeometry(opt.radius, 32, 32),
                                     new THREE.MeshLambertMaterial({color: opt.color, opacity: opt.opacity, transparent: (opt.opacity < 1)}));
    app.queryMarker.name = "marker";

    app.queryMarker.onBeforeRender = function (renderer, scene, camera, geometry, material, group) {
      this.scale.setScalar(this.position.distanceTo(camera.position) * ((camera.isPerspectiveCamera) ? 1 : conf.qmarker.k));
      this.updateMatrixWorld();
    };

    app.highlightMaterial = new THREE.MeshLambertMaterial({emissive: 0x999900, transparent: true, opacity: 0.5});

    if (!Q3D.isIE) app.highlightMaterial.side = THREE.DoubleSide;    // Shader compilation error occurs with double sided material on IE11

    // loading manager
    app.initLoadingManager();

    // event listeners
    app.addEventListener("sceneLoaded", function () {
      if (conf.viewpoint.pos === undefined && conf.autoAdjustCameraPos) {
        app.adjustCameraPosition();
      }
      app.render();

      if (conf.animation.startOnLoad) {
        app.animation.keyframes.start();
      }
    }, true);

    window.addEventListener("keydown", app.eventListener.keydown);
    window.addEventListener("resize", app.eventListener.resize);

    app.renderer.domElement.addEventListener("mousedown", app.eventListener.mousedown);
    app.renderer.domElement.addEventListener("mouseup", app.eventListener.mouseup);

    gui.init();
  };

  app.parseUrlParameters = function () {
    var p, vars = {};
    var params = window.location.search.substring(1).split('&').concat(window.location.hash.substring(1).split('&'));
    params.forEach(function (param) {
      p = param.split('=');
      vars[p[0]] = p[1];
    });
    return vars;
  };

  app.initLoadingManager = function () {
    if (app.loadingManager) {
      app.loadingManager.onLoad = app.loadingManager.onProgress = app.loadingManager.onError = undefined;
    }

    app.loadingManager = new THREE.LoadingManager(function () {   // onLoad
      app.loadingManager.isLoading = false;

      E("progressbar").classList.add("fadeout");

      app.dispatchEvent({type: "sceneLoaded"});
    },
    function (url, loaded, total) {   // onProgress
      E("progressbar").style.width = (loaded / total * 100) + "%";
    },
    function () {   // onError
      app.loadingManager.isLoading = false;

      app.dispatchEvent({type: "sceneLoadError"});
    });

    app.loadingManager.onStart = function () {
      app.loadingManager.isLoading = true;
    };

    app.loadingManager.isLoading = false;
  };

  app.loadFile = function (url, type, callback) {

    var loader = new THREE.FileLoader(app.loadingManager);
    loader.setResponseType(type);

    var onError = function (e) {
      if (location.protocol == "file:") {
        gui.popup.show("This browser doesn't allow loading local files via Ajax. See <a href='https://github.com/minorua/Qgis2threejs/wiki/Browser-Support'>plugin wiki page</a> for details.", "Error", true);
      }
    };

    try {
      loader.load(url, callback, undefined, onError);
    }
    catch (e) {      // for IE
      onError(e);
    }
  };

  app.loadJSONObject = function (jsonObject) {
    app.scene.loadJSONObject(jsonObject);
    if (jsonObject.animation !== undefined) app.animation.keyframes.load(jsonObject.animation.groups);
  };

  app.loadJSONFile = function (url, callback) {
    app.loadFile(url, "json", function (obj) {
      app.loadJSONObject(obj);
      if (callback) callback(obj);
    });
  };

  app.loadSceneFile = function (url, sceneFileLoadedCallback, sceneLoadedCallback) {

    var onload = function () {
      if (sceneFileLoadedCallback) sceneFileLoadedCallback(app.scene);
    };

    if (sceneLoadedCallback) {
      app.addEventListener("sceneLoaded", function () {
        sceneLoadedCallback(app.scene);
      });
    }

    var ext = url.split(".").pop();
    if (ext == "json") app.loadJSONFile(url, onload);
    else if (ext == "js") {
      var e = document.createElement("script");
      e.src = url;
      e.onload = onload;
      document.body.appendChild(e);
    }
  };

  app.loadTextureFile = function (url, callback) {
    return new THREE.TextureLoader(app.loadingManager).load(url, callback);
  };

  app.loadModelFile = function (url, callback) {
    var loader,
        ext = url.split(".").pop();
    if (ext == "dae") {
      loader = new THREE.ColladaLoader(app.loadingManager);
    }
    else if (ext == "gltf" || ext == "glb") {
      loader = new THREE.GLTFLoader(app.loadingManager);
    }
    else {
      console.log("Model file type not supported: " + url);
      return;
    }

    app.loadingManager.itemStart("M" + url);

    loader.load(url, function (model) {
      if (callback) callback(model);
      app.loadingManager.itemEnd("M" + url);
    },
    undefined,
    function (e) {
      console.log("Failed to load model: " + url);
      app.loadingManager.itemError("M" + url);
    });
  };

  app.loadModelData = function (data, ext, resourcePath, callback) {

    if (ext == "dae") {
      var model = new THREE.ColladaLoader(app.loadingManager).parse(data, resourcePath);
      if (callback) callback(model);
    }
    else if (ext == "gltf" || ext == "glb") {
      new THREE.GLTFLoader(app.loadingManager).parse(data, resourcePath, function (model) {
        if (callback) callback(model);
      }, function (e) {
        console.log("Failed to load a glTF model: " + e);
      });
    }
    else {
      console.log("Model file type not supported: " + ext);
      return;
    }
  };

  app.mouseDownPoint = new THREE.Vector2();
  app.mouseUpPoint = new THREE.Vector2();

  app.eventListener = {

    keydown: function (e) {
      if (e.ctrlKey) return;

      if (e.shiftKey) {
        switch (e.keyCode) {
          case 82:  // Shift + R
            app.controls.reset();
            return;
          case 83:  // Shift + S
            gui.showPrintDialog();
            return;
        }
        return;
      }

      switch (e.keyCode) {
        case 8:   // BackSpace
          if (app.measure.isActive) app.measure.removeLastPoint();
          return;
        case 13:  // Enter
          app.animation.keyframes.resume();
          return;
        case 27:  // ESC
          if (gui.popup.isVisible()) {
            app.cleanView();
          }
          else if (app.controls.autoRotate) {
            app.setRotateAnimationMode(false);
          }
          return;
        case 73:  // I
          gui.showInfo();
          return;
        case 76:  // L
          app.setLabelVisible(!app.labelVisible);
          return;
        case 82:  // R
          app.setRotateAnimationMode(!app.controls.autoRotate);
          return;
        case 87:  // W
          app.setWireframeMode(!app._wireframeMode);
          return;
      }
    },

    mousedown: function (e) {
      app.mouseDownPoint.set(e.clientX, e.clientY);
    },

    mouseup: function (e) {
      app.mouseUpPoint.set(e.clientX, e.clientY);
      if (app.mouseDownPoint.equals(app.mouseUpPoint)) app.canvasClicked(e);
    },

    resize: function () {
      app.setCanvasSize(app.container.clientWidth, app.container.clientHeight);
      app.render();
    }

  };

  app.setCanvasSize = function (width, height) {
    var changed = (app.width != width || app.height != height);

    app.width = width;
    app.height = height;
    app.camera.aspect = width / height;
    app.camera.updateProjectionMatrix();
    app.renderer.setSize(width, height);

    if (changed) app.dispatchEvent({type: "canvasSizeChanged"});
  };

  app.buildCamera = function (is_ortho) {
    if (is_ortho) {
      app.camera = new THREE.OrthographicCamera(-app.width / 10, app.width / 10, app.height / 10, -app.height / 10);
    }
    else {
      app.camera = new THREE.PerspectiveCamera(45, app.width / app.height);
    }

    // magic to change y-up world to z-up
    app.camera.up.set(0, 0, 1);

    var be = app.scene.userData.baseExtent;
    if (be) {
      app.camera.near = (is_ortho) ? 0 : 0.001 * be.width;
      app.camera.far = 100 * be.width;
      app.camera.updateProjectionMatrix();
    }
  };

  // move camera target to center of scene
  app.adjustCameraPosition = function (force) {
    if (!force) {
      app.render();

      // stay at current position if rendered objects exist
      var r = app.renderer.info.render;
      if (r.triangles + r.points + r.lines) return;
    }
    var bbox = app.scene.boundingBox();
    if (bbox.isEmpty()) return;

    bbox.getCenter(vec3);
    app.cameraAction.zoom(vec3.x, vec3.y, (bbox.max.z + vec3.z) / 2, app.scene.userData.baseExtent.width);
  };

  // declination: clockwise from +y, in degrees
  app.buildNorthArrow = function (container, declination) {
    container.style.display = "block";

    app.renderer2 = new THREE.WebGLRenderer({alpha: true, antialias: true});
    app.renderer2.setClearColor(0, 0);
    app.renderer2.setSize(container.clientWidth, container.clientHeight);

    app.container2 = container;
    app.container2.appendChild(app.renderer2.domElement);

    app.camera2 = new THREE.PerspectiveCamera(45, container.clientWidth / container.clientHeight, 1, 1000);
    app.camera2.position.set(0, 0, conf.northArrow.cameraDistance);
    app.camera2.up = app.camera.up;

    app.scene2 = new Q3D.Scene();
    app.scene2.buildLights(conf.lights.directional, 0);

    // an arrow object
    var geometry = new THREE.Geometry();
    geometry.vertices.push(
      new THREE.Vector3(-5, -10, 0),
      new THREE.Vector3(0, 10, 0),
      new THREE.Vector3(0, -7, 3),
      new THREE.Vector3(5, -10, 0)
    );
    geometry.faces.push(
      new THREE.Face3(0, 1, 2),
      new THREE.Face3(2, 1, 3)
    );
    geometry.computeFaceNormals();

    var material = new THREE.MeshLambertMaterial({color: conf.northArrow.color, side: THREE.DoubleSide});
    var mesh = new THREE.Mesh(geometry, material);
    if (declination) mesh.rotation.z = -declination * Q3D.deg2rad;
    app.scene2.add(mesh);
  };

  app.buildViewHelper = function (container) {

    if (app.renderer3 === undefined) {
      container.style.display = "block";

      app.renderer3 = new THREE.WebGLRenderer({alpha: true, antialias: true});
      app.renderer3.setClearColor(0, 0);
      app.renderer3.setSize(container.clientWidth, container.clientHeight);

      app.container3 = container;
      app.container3.appendChild(app.renderer3.domElement);
    }

    if (app.viewHelper !== undefined) {
      app.viewHelper.removeEventListener("requestAnimation", app.startViewHelperAnimation);
    }

    app.viewHelper = new ViewHelper(app.camera, {dom: container});
    app.viewHelper.controls = app.controls;

    app.viewHelper.addEventListener("requestAnimation", app.startViewHelperAnimation);
  };

  var clock = new THREE.Clock();
  app.startViewHelperAnimation = function () {
    clock.start();
    requestAnimationFrame(app.animate);
  };

  app.currentViewUrl = function () {
    var c = app.scene.toMapCoordinates(app.camera.position),
        t = app.scene.toMapCoordinates(app.controls.target),
        hash = "#cx=" + c.x.toFixed(3) + "&cy=" + c.y.toFixed(3) + "&cz=" + c.z.toFixed(3);
    if (t.x || t.y || t.z) hash += "&tx=" + t.x.toFixed(3) + "&ty=" + t.y.toFixed(3) + "&tz=" + t.z.toFixed(3);
    return window.location.href.split("#")[0] + hash;
  };

  // enable the controls
  app.start = function () {
    if (app.controls) app.controls.enabled = true;
  };

  app.pause = function () {
    app.animation.isActive = false;
    if (app.controls) app.controls.enabled = false;
  };

  app.resume = function () {
    if (app.controls) app.controls.enabled = true;
  };

  // animation loop
  app.animate = function () {

    if (app.animation.isActive) {
      requestAnimationFrame(app.animate);

      if (app.animation.keyframes.isActive) TWEEN.update();
      else if (app.controls.enabled) app.controls.update();
    }
    else if (app.viewHelper && app.viewHelper.animating) {
      requestAnimationFrame(app.animate);

      app.viewHelper.update(clock.getDelta());
    }

    app.render();
  };

  app.animation = {

    isActive: false,

    start: function () {
      this.isActive = true;
      app.animate();
    },

    stop: function () {
      this.isActive = false;
    },

    keyframes: {    // keyframe animation

      isActive: false,

      isPaused: false,

      isLoop: false,

      curveFactor: 0,

      easingFunction: function (easing) {
        if (easing == 1) return TWEEN.Easing.Linear.None;
        if (easing > 1) {
          var f = TWEEN.Easing[Q3D.Config.animation.easingCurve];
          if (easing == 2) return f["InOut"];
          else if (easing == 3) return f["In"];
          else return f["Out"];   // easing == 4
        }
      },

      keyframeGroups: [],

      clear: function () {
        this.keyframeGroups = [];
      },

      load: function (group) {
        if (!Array.isArray(group)) group = [group];

        this.keyframeGroups = this.keyframeGroups.concat(group);
      },

      start: function () {

        var _this = this,
            e = E("narrativebox"),
            btn = E("nextbtn"),
            currentNarElem;

        this.keyframeGroups.forEach(function (group) {

          var t;
          for (var p in Q3D.Tweens) {
            if (Q3D.Tweens[p].type == group.type) {
              t = Q3D.Tweens[p];
              break;
            }
          }
          if (t === undefined) {
            console.warn("unknown animation type: " + group.type);
            return;
          }

          var layer = (group.layerId !== undefined) ? app.scene.mapLayers[group.layerId] : undefined;

          group.completed = false;
          group.currentIndex = 0;
          group.prop_list = [];

          t.init(group, layer);

          var keyframes = group.keyframes;

          var showNBox = function (idx) {
            // narrative box
            var n = keyframes[idx].narration;
            if (n && e) {
              if (currentNarElem) {
                currentNarElem.classList.remove("visible");
              }

              currentNarElem = E(n.id);
              if (currentNarElem) {
                currentNarElem.classList.add("visible");
              }
              else {    // preview
                E("narbody").innerHTML = n.text;
              }

              if (btn) {
                if (idx < keyframes.length - 1) {
                  btn.className = "nextbtn";
                  btn.innerHTML =  "";
                }
                else {
                  btn.className = "";
                  btn.innerHTML = "Close";
                }
              }

              setTimeout(function () {
                _this.pause();
                e.classList.add("visible");
              }, 0);
            }
          };

          var onStart = function () {
            if (group.onStart) group.onStart();

            app.dispatchEvent({type: "tweenStarted", index: group.currentIndex});

            // pause if narrative box is shown
            if (e && e.classList.contains("visible")) {
              e.classList.remove("visible");
            }
          };

          var onComplete = function (obj) {
            if (!keyframes[group.currentIndex].easing) {
              group.onUpdate(obj, 1);
            }

            if (group.onComplete) group.onComplete(obj);

            var index = ++group.currentIndex;
            if (index == keyframes.length - 1) {
              group.completed = true;

              var completed = true;
              for (var i = 0; i < _this.keyframeGroups.length; i++) {
                if (!_this.keyframeGroups[i].completed) completed = false;
              }

              if (completed) {
                if (_this.isLoop) {
                  setTimeout(function () {
                    _this.start();
                  }, 0);
                }
                else {
                  _this.stop();
                }
              }
            }

            // show narrative box if the current keyframe has a narrative content
            showNBox(index);
          };

          var t0, t1, t2;
          for (var i = 0; i < keyframes.length - 1; i++) {

            t2 = new TWEEN.Tween(group.prop_list[i]).delay(keyframes[i].delay).onStart(onStart)
                             .to(group.prop_list[i + 1], keyframes[i].duration).onComplete(onComplete);

            if (keyframes[i].easing) {
              t2.easing(_this.easingFunction(keyframes[i].easing)).onUpdate(group.onUpdate);
            }

            if (i == 0) {
              t0 = t2;
            }
            else {
              t1.chain(t2);
            }
            t1 = t2;
          }

          showNBox(0);

          t0.start();
        });

        app.animation.isActive = this.isActive = true;
        app.dispatchEvent({type: "animationStarted"});
        app.animate();
      },

      stop: function () {

        TWEEN.removeAll();

        app.animation.isActive = this.isActive = this.isPaused = false;
        this._pausedTweens = null;

        app.dispatchEvent({type: "animationStopped"});
      },

      pause: function () {

        if (this.isPaused) return;

        this._pausedTweens = TWEEN.getAll();

        if (this._pausedTweens.length) {
          for (var i = 0; i < this._pausedTweens.length; i++) {
            this._pausedTweens[i].pause();
          }
          this.isPaused = true;
        }
        app.animation.isActive = this.isActive = false;
      },

      resume: function () {

        var box = E("narrativebox");
        if (box && box.classList.contains("visible")) {
          box.classList.remove("visible");
        }

        if (!this.isPaused) return;

        for (var i = 0; i < this._pausedTweens.length; i++) {
          this._pausedTweens[i].resume();
        }
        this._pausedTweens = null;

        app.animation.isActive = this.isActive = true;
        this.isPaused = false;

        app.animate();
      }
    },

    orbit: {      // orbit animation

      isActive: false,

      start: function () {

        app.controls.autoRotate = true;
        app.animation.isActive = this.isActive = true;

        app.animate();
      },

      stop: function () {

        app.controls.autoRotate = false;
        app.animation.isActive = this.isActive = false;
      }
    }
  };

  app.render = function (updateControls) {
    if (updateControls) {
      app.controls.update();
    }

    if (app.camera.parent) {
      app.camera.updateMatrixWorld();
    }

    // render
    if (app.effect) {
      app.effect.render(app.scene, app.camera);
    }
    else {
      app.renderer.render(app.scene, app.camera);
    }

    // North arrow
    if (app.renderer2) {
      app.scene2.quaternion.copy(app.camera.quaternion).inverse();
      app.scene2.updateMatrixWorld();

      app.renderer2.render(app.scene2, app.camera2);
    }

    // navigation widget
    if (app.viewHelper) {
      app.viewHelper.render(app.renderer3);
    }
  };

  (function () {
    var dly, rpt, times, id = null;
    var func = function () {
      app.render();
      if (rpt <= ++times) {
        clearInterval(id);
        id = null;
      }
    };
    app.setIntervalRender = function (delay, repeat) {
      if (id === null || delay != dly) {
        if (id !== null) {
          clearInterval(id);
        }
        id = setInterval(func, delay);
        dly = delay;
      }
      rpt = repeat;
      times = 0;
    };
  })();

  app.setLabelVisible = function (visible) {
    app.labelVisible = visible;
    app.scene.labelGroup.visible = visible;
    app.scene.labelConnectorGroup.visible = visible;
    app.render();
  };

  app.setRotateAnimationMode = function (enabled) {
    if (enabled) {
      app.animation.orbit.start();
    }
    else {
      app.animation.orbit.stop();
    }
  };

  app.setWireframeMode = function (wireframe) {
    if (wireframe == app._wireframeMode) return;

    for (var id in app.scene.mapLayers) {
      app.scene.mapLayers[id].setWireframeMode(wireframe);
    }

    app._wireframeMode = wireframe;
    app.render();
  };

  app.intersectObjects = function (offsetX, offsetY) {
    var vec2 = new THREE.Vector2((offsetX / app.width) * 2 - 1,
                                 -(offsetY / app.height) * 2 + 1);
    var ray = new THREE.Raycaster();
    ray.linePrecision = 0.2;
    ray.setFromCamera(vec2, app.camera);
    return ray.intersectObjects(app.scene.visibleObjects(app.labelVisible));
  };

  app._offset = function (elm) {
    var top = 0, left = 0;
    do {
      top += elm.offsetTop || 0; left += elm.offsetLeft || 0; elm = elm.offsetParent;
    } while (elm);
    return {top: top, left: left};
  };

  app.queryTargetPosition = new THREE.Vector3();

  app.cameraAction = {

    move: function (x, y, z) {
      if (x === undefined) app.camera.position.copy(app.queryTargetPosition);
      else app.camera.position.set(x, y, z);
      app.render(true);
      app.cleanView();
    },

    vecZoom: new THREE.Vector3(0, -1, 1).normalize(),

    zoom: function (x, y, z, dist) {
      if (x === undefined) vec3.copy(app.queryTargetPosition);
      else vec3.set(x, y, z);

      if (dist === undefined) dist = app.scene.userData.baseExtent.width * 0.1;

      app.camera.position.copy(app.cameraAction.vecZoom).multiplyScalar(dist).add(vec3);
      app.camera.lookAt(vec3);
      if (app.controls.target !== undefined) app.controls.target.copy(vec3);
      app.render(true);
      app.cleanView();
    },

    zoomToLayer: function (layer) {
      if (!layer) return;

      var bbox = layer.boundingBox();

      bbox.getSize(vec3);
      var dist = Math.max(vec3.x, vec3.y * 3 / 4) * 1.2;

      bbox.getCenter(vec3);
      app.cameraAction.zoom(vec3.x, vec3.y, vec3.z, dist);
    },

    orbit: function (x, y, z) {
      if (app.controls.target === undefined) return;

      if (x === undefined) app.controls.target.copy(app.queryTargetPosition);
      else app.controls.target.set(x, y, z);
      app.setRotateAnimationMode(true);
      app.cleanView();
    }

  };

  app.cleanView = function () {
    gui.clean();

    app.scene.remove(app.queryMarker);
    app.highlightFeature(null);
    app.measure.clear();
    app.render();

    app.selectedLayer = null;

    if (app._canvasImageUrl) {
      URL.revokeObjectURL(app._canvasImageUrl);
      app._canvasImageUrl = null;
    }
  };

  app.highlightFeature = function (object) {
    if (app.highlightObject) {
      // remove highlight object from the scene
      app.scene.remove(app.highlightObject);
      app.selectedObject = null;
      app.highlightObject = null;
    }

    if (object === null) return;

    var layer = app.scene.mapLayers[object.userData.layerId];
    if (!layer || layer.type == Q3D.LayerType.DEM || layer.type == Q3D.LayerType.PointCloud) return;
    if (layer.properties.objType == "Billboard") return;

    // create a highlight object (if layer type is Point, slightly bigger than the object)
    var s = (layer.type == Q3D.LayerType.Point) ? 1.01 : 1;

    var clone = object.clone();
    clone.traverse(function (obj) {
      obj.material = app.highlightMaterial;
    });
    if (s != 1) clone.scale.multiplyScalar(s);

    // add the highlight object to the scene
    app.scene.add(clone);

    app.selectedObject = object;
    app.highlightObject = clone;
  };

  app.canvasClicked = function (e) {

    // button 2: right click
    if (e.button == 2 && app.measure.isActive) {
      app.measure.removeLastPoint();
      return;
    }

    var canvasOffset = app._offset(app.renderer.domElement);
    var objs = app.intersectObjects(e.clientX - canvasOffset.left, e.clientY - canvasOffset.top);

    var obj, o, layer, layerId;
    for (var i = 0, l = objs.length; i < l; i++) {
      obj = objs[i];

      if (app.measure.isActive) {
        app.measure.addPoint(obj.point);
        return;
      }

      // get layerId of clicked object
      o = obj.object;
      while (o) {
        layerId = o.userData.layerId;
        if (layerId !== undefined) break;
        o = o.parent;
      }

      if (layerId === undefined) break;

      layer = app.scene.mapLayers[layerId];
      if (!layer.clickable) break;

      app.selectedLayer = layer;
      app.queryTargetPosition.copy(obj.point);

      // query marker
      app.queryMarker.position.copy(obj.point);
      app.scene.add(app.queryMarker);

      if (o.userData.isLabel) {
        o = o.userData.objs[o.userData.partIdx];    // label -> object
      }

      app.highlightFeature(o);
      app.render();
      gui.showQueryResult(obj.point, layer, o, conf.coord.visible);

      return;
    }
    if (app.measure.isActive) return;

    app.cleanView();

    if (app.controls.autoRotate) {
      app.setRotateAnimationMode(false);
    }
  };

  app.saveCanvasImage = function (width, height, fill_background, saveImageFunc) {
    if (fill_background === undefined) fill_background = true;

    // set canvas size
    var old_size;
    if (width && height) {
      old_size = [app.width, app.height];
      app.setCanvasSize(width, height);
    }

    // functions
    var saveBlob = function (blob) {
      var filename = "image.png";

      // ie
      if (window.navigator.msSaveBlob !== undefined) {
        window.navigator.msSaveBlob(blob, filename);
        gui.popup.hide();
      }
      else {
        // create object url
        if (app._canvasImageUrl) URL.revokeObjectURL(app._canvasImageUrl);
        app._canvasImageUrl = URL.createObjectURL(blob);

        // display a link to save the image
        var e = document.createElement("a");
        e.className = "download-link";
        e.href = app._canvasImageUrl;
        e.download = filename;
        e.innerHTML = "Save";
        gui.popup.show("Click to save the image to a file." + e.outerHTML, "Image is ready");
      }
    };

    var saveCanvasImage = saveImageFunc || function (canvas) {
      if (canvas.toBlob !== undefined) {
        canvas.toBlob(saveBlob);
      }
      else {    // !HTMLCanvasElement.prototype.toBlob
        // https://developer.mozilla.org/en-US/docs/Web/API/HTMLCanvasElement.toBlob
        var binStr = atob(canvas.toDataURL("image/png").split(',')[1]),
            len = binStr.length,
            arr = new Uint8Array(len);

        for (var i = 0; i < len; i++) {
          arr[i] = binStr.charCodeAt(i);
        }

        saveBlob(new Blob([arr], {type: "image/png"}));
      }
    };

    var restoreCanvasSize = function () {
      // restore canvas size
      if (old_size) app.setCanvasSize(old_size[0], old_size[1]);
      app.render();
    };

    // background option
    if (!fill_background) app.renderer.setClearColor(0, 0);

    // render
    app.renderer.preserveDrawingBuffer = true;

    if (app.effect) {
      app.effect.render(app.scene, app.camera);
    }
    else {
      app.renderer.render(app.scene, app.camera);
    }

    // restore clear color
    var bgcolor = conf.bgColor;
    app.renderer.setClearColor(bgcolor || 0, (bgcolor === null) ? 0 : 1);

    if (fill_background && bgcolor === null) {
      var canvas = document.createElement("canvas");
      canvas.width = width;
      canvas.height = height;

      var ctx = canvas.getContext("2d");
      if (fill_background && bgcolor === null) {
        // render "sky-like" background
        var grad = ctx.createLinearGradient(0, 0, 0, height);
        grad.addColorStop(0, "#98c8f6");
        grad.addColorStop(0.4, "#cbebff");
        grad.addColorStop(1, "#f0f9ff");
        ctx.fillStyle = grad;
        ctx.fillRect(0, 0, width, height);
      }

      var image = new Image();
      image.onload = function () {
        // draw webgl canvas image
        ctx.drawImage(image, 0, 0, width, height);

        // save canvas image
        saveCanvasImage(canvas);
        restoreCanvasSize();
      };
      image.src = app.renderer.domElement.toDataURL("image/png");
    }
    else {
      // save webgl canvas image
      saveCanvasImage(app.renderer.domElement);
      restoreCanvasSize();
    }
  };

  (function () {

    var path = [];

    app.measure = {

      isActive: false,

      precision: 3,

      start: function () {
        app.scene.remove(app.queryMarker);

        if (!this.geom) {
          var opt = conf.measure.marker;
          this.geom = new THREE.SphereBufferGeometry(opt.radius, 32, 32);
          this.mtl = new THREE.MeshLambertMaterial({color: opt.color, opacity: opt.opacity, transparent: (opt.opacity < 1)});
          opt = conf.measure.line;
          this.lineMtl = new THREE.LineBasicMaterial({color: opt.color});
          this.markerGroup = new Q3D.Group();
          this.markerGroup.name = "measure marker";
          this.lineGroup = new Q3D.Group();
          this.lineGroup.name = "measure line";
        }

        this.isActive = true;

        app.scene.add(this.markerGroup);
        app.scene.add(this.lineGroup);

        this.addPoint(app.queryTargetPosition);
      },

      addPoint: function (pt) {
        // add a marker
        var marker = new THREE.Mesh(this.geom, this.mtl);
        marker.position.copy(pt);
        marker.onBeforeRender = app.queryMarker.onBeforeRender;

        this.markerGroup.updateMatrixWorld();
        this.markerGroup.add(marker);

        path.push(marker.position);

        if (path.length > 1) {
          // add a line
          var v = path[path.length - 2].toArray().concat(path[path.length - 1].toArray()),
              geom = new THREE.BufferGeometry().setAttribute("position", new THREE.Float32BufferAttribute(v, 3)),
              line = new THREE.Line(geom, this.lineMtl);
          this.lineGroup.add(line);
        }

        app.render();
        this.showResult();
      },

      removeLastPoint: function () {
        path.pop();
        this.markerGroup.children.pop();
        this.lineGroup.children.pop();

        app.render();

        if (path.length) this.showResult();
        else app.cleanView();
      },

      clear: function () {
        if (!this.isActive) return;

        this.markerGroup.clear();
        this.lineGroup.clear();

        app.scene.remove(this.markerGroup);
        app.scene.remove(this.lineGroup);

        path = [];
        this.isActive = false;
      },

      formatLength: function (length) {
        return (length) ? length.toFixed(this.precision) : 0;
      },

      showResult: function () {
        var vec2 = new THREE.Vector2(),
            zScale = app.scene.userData.zScale;
        var total = 0, totalxy = 0, dz = 0;
        if (path.length > 1) {
          var dxy;
          for (var i = path.length - 1; i > 0; i--) {
            dxy = vec2.copy(path[i]).distanceTo(path[i - 1]);
            dz = (path[i].z - path[i - 1].z) / zScale;

            total += Math.sqrt(dxy * dxy + dz * dz);
            totalxy += dxy;
          }
          dz = (path[path.length - 1].z - path[0].z) / zScale;
        }

        var html = '<table class="measure">';
        html += "<tr><td>Total distance:</td><td>" + this.formatLength(total) + " m</td><td></td></tr>";
        html += "<tr><td>Horizontal distance:</td><td>" + this.formatLength(totalxy) + " m</td><td></td></tr>";
        html += "<tr><td>Vertical difference:</td><td>" + this.formatLength(dz) + ' m</td><td><span class="tooltip tooltip-btn" data-tooltip="elevation difference between start point and end point">?</span></td></tr>';
        html += "</table>";

        gui.popup.show(html, "Measure distance");
      }
    };
  })();
})();

/*
Q3D.gui
*/
(function () {
  var app = Q3D.application,
      gui = Q3D.gui,
      conf = Q3D.Config,
      E = Q3D.E,
      VIS = "visible";

  function CE(tagName, parent, innerHTML) {
    var elem = document.createElement(tagName);
    if (parent) parent.appendChild(elem);
    if (innerHTML) elem.innerHTML = innerHTML;
    return elem;
  }

  function ON_CLICK(id, listener) {
    var e = document.getElementById(id);
    if (e) e.addEventListener("click", listener);
  }

  gui.modules = [];

  gui.init = function () {
    // tool buttons
    ON_CLICK("layerbtn", function () {
      if (!gui.layerPanel.initialized) gui.layerPanel.init();

      if (gui.layerPanel.isVisible()) {
        gui.layerPanel.hide();
      }
      else {
        if (gui.popup.isVisible()) {
          gui.popup.hide();
        }
        gui.layerPanel.show();
      }
    });

    ON_CLICK("infobtn", function () {
      gui.layerPanel.hide();

      if (gui.popup.isVisible() && gui.popup.content == "pageinfo") gui.popup.hide();
      else gui.showInfo();
    });

    var btn = E("animbtn");
    if (conf.animation.enabled && btn) {
      var anim = app.animation.keyframes;

      btn.classList.remove("hidden");

      var playButton = function () {
        btn.className = "playbtn";
      };

      var pauseButton = function () {
        btn.className = "pausebtn";
      };

      playButton();

      btn.onclick = function () {
        if (anim.isActive) {
          anim.pause();
          playButton();
        }
        else if (anim.isPaused) {
          anim.resume();
          pauseButton();
        }
        else anim.start();
      };

      app.addEventListener('animationStarted', pauseButton);
      app.addEventListener('animationStopped', playButton);
    }

    // popup
    ON_CLICK("closebtn", app.cleanView);
    ON_CLICK("zoomtolayer", function () {
      app.cameraAction.zoomToLayer(app.selectedLayer);
    });
    ON_CLICK("zoomtopoint", function () {
      app.cameraAction.zoom();
    });
    ON_CLICK("orbitbtn", function () {
      app.cameraAction.orbit();
    });
    ON_CLICK("measurebtn", function () {
      app.measure.start();
    });

    // narrative box
    ON_CLICK("nextbtn", function () {
      app.animation.keyframes.resume();
    });

    // attribution
    if (typeof proj4 === "undefined") {
      var e = E("lib_proj4js");
      if (e) e.classList.add("hidden");
    }

    // initialize modules
    for (var i = 0; i < gui.modules.length; i++) {
      gui.modules[i].init();
    }
  };

  gui.clean = function () {
    gui.popup.hide();
    if (gui.layerPanel.initialized) gui.layerPanel.hide();
  };

  gui.popup = {

    modal: false,

    content: null,

    timerId: null,

    isVisible: function () {
      return E("popup").classList.contains(VIS);
    },

    // show box
    // obj: html, element or content id ("queryresult" or "pageinfo")
    // modal: boolean
    // duration: int [milliseconds]
    show: function (obj, title, modal, duration) {

      if (modal) app.pause();
      else if (this.modal) app.resume();

      this.content = obj;
      this.modal = Boolean(modal);

      var e = E("layerpanel");
      if (e) e.classList.remove(VIS);

      var content = E("popupcontent");
      [content, E("queryresult"), E("pageinfo")].forEach(function (e) {
        if (e) e.classList.remove(VIS);
      });

      if (obj == "queryresult" || obj == "pageinfo") {
        E(obj).classList.add(VIS);
      }
      else {
        if (obj instanceof HTMLElement) {
          content.innerHTML = "";
          content.appendChild(obj);
        }
        else {
          content.innerHTML = obj;
        }
        content.classList.add(VIS);
      }
      E("popupbar").innerHTML = title || "";
      E("popup").classList.add(VIS);

      if (this.timerId !== null) {
        clearTimeout(this.timerId);
        this.timerId = null;
      }

      if (duration) {
        this.timerId = setTimeout(function () {
          gui.popup.hide();
        }, duration);
      }
    },

    hide: function () {
      E("popup").classList.remove(VIS);
      if (this.timerId !== null) clearTimeout(this.timerId);
      this.timerId = null;
      this.content = null;
      if (this.modal) app.resume();
    }

  };

  gui.showInfo = function () {
    var e = E("urlbox");
    if (e) e.value = app.currentViewUrl();
    gui.popup.show("pageinfo");
  };

  gui.showQueryResult = function (point, layer, obj, show_coords) {
    // layer name
    var e = E("qr_layername");
    if (layer && e) e.innerHTML = layer.properties.name;

    // clicked coordinates
    e = E("qr_coords_table");
    if (e) {
      if (show_coords) {
        e.classList.remove("hidden");

        var pt = app.scene.toMapCoordinates(point);

        e = E("qr_coords");

        if (conf.coord.latlon) {
          var lonLat = proj4(app.scene.userData.proj).inverse([pt.x, pt.y]);
          e.innerHTML = Q3D.Utils.convertToDMS(lonLat[1], lonLat[0]) + ", Elev. " + pt.z.toFixed(2);
        }
        else {
          e.innerHTML = [pt.x.toFixed(2), pt.y.toFixed(2), pt.z.toFixed(2)].join(", ");
        }

        if (conf.debugMode) {
          var p = app.scene.userData,
              be = p.baseExtent;
          e.innerHTML += "<br>WLD: " + [point.x.toFixed(8), point.y.toFixed(8), point.z.toFixed(8)].join(", ");
          e.innerHTML += "<br><br>ORG: " + [p.origin.x.toFixed(8), p.origin.y.toFixed(8), p.origin.z.toFixed(8)].join(", ");
          e.innerHTML += "<br>BE CNTR: " + [be.cx.toFixed(8), be.cy.toFixed(8)].join(", ");
          e.innerHTML += "<br>BE SIZE: " + [be.width.toFixed(8), be.height.toFixed(8)].join(", ");
          e.innerHTML += "<br>ROT: " + be.rotation + "<br>Z SC: " + p.zScale;
        }
      }
      else {
        e.classList.add("hidden");
      }
    }

    e = E("qr_attrs_table");
    if (e) {
      for (var i = e.children.length - 1; i >= 0; i--) {
        if (e.children[i].tagName.toUpperCase() == "TR") e.removeChild(e.children[i]);
      }

      if (layer && layer.properties.propertyNames !== undefined) {
        var row;
        for (var i = 0, l = layer.properties.propertyNames.length; i < l; i++) {
          row = document.createElement("tr");
          row.innerHTML = "<td>" + layer.properties.propertyNames[i] + "</td>" +
                          "<td>" + obj.userData.properties[i] + "</td>";
          e.appendChild(row);
        }
        e.classList.remove("hidden");
      }
      else {
        e.classList.add("hidden");
      }
    }
    gui.popup.show("queryresult");
  };

  gui.showPrintDialog = function () {

    var f = CE("form");
    f.className = "print";

    var d1 = CE("div", f, "Image Size");
    d1.style.textDecoration = "underline";

    var d2 = CE("div", f),
        l1 = CE("label", d2, "Width:"),
        width = CE("input", d2);
    d2.style.cssFloat = "left";
    l1.htmlFor = width.id = width.name = "printwidth";
    width.type = "text";
    width.value = app.width;
    CE("span", d2, "px,");

    var d3 = CE("div", f),
        l2 = CE("label", d3, "Height:"),
        height = CE("input", d3);
    l2.htmlFor = height.id = height.name = "printheight";
    height.type = "text";
    height.value = app.height;
    CE("span", d3, "px");

    var d4 = CE("div", f),
        ka = CE("input", d4);
    ka.type = "checkbox";
    ka.checked = true;
    CE("span", d4, "Keep Aspect Ratio");

    var d5 = CE("div", f, "Option");
    d5.style.textDecoration = "underline";

    var d6 = CE("div", f),
        bg = CE("input", d6);
    bg.type = "checkbox";
    bg.checked = true;
    CE("span", d6, "Fill Background");

    var d7 = CE("div", f),
        ok = CE("span", d7, "OK"),
        cancel = CE("span", d7, "Cancel");
    d7.className = "buttonbox";

    CE("input", f).type = "submit";

    // event handlers
    // width and height boxes
    var aspect = app.width / app.height;

    width.oninput = function () {
      if (ka.checked) height.value = Math.round(width.value / aspect);
    };

    height.oninput = function () {
      if (ka.checked) width.value = Math.round(height.value * aspect);
    };

    ok.onclick = function () {
      gui.popup.show("Rendering...");
      window.setTimeout(function () {
        app.saveCanvasImage(width.value, height.value, bg.checked);
      }, 10);
    };

    cancel.onclick = app.cleanView;

    // enter key pressed
    f.onsubmit = function () {
      ok.onclick();
      return false;
    };

    gui.popup.show(f, "Save Image", true);   // modal
  };

  gui.layerPanel = {

    init: function () {
      var panel = E("layerpanel");

      var p, item, e, slider, o, select, i;
      Object.keys(app.scene.mapLayers).forEach(function (layerId) {

        var layer = app.scene.mapLayers[layerId];
        p = layer.properties;
        item = CE("div", panel);
        item.className = "layer";

        // visible
        e = CE("div", item, "<input type='checkbox'" +  ((p.visible) ? " checked" : "") + ">" + p.name);
        e.querySelector("input[type=checkbox]").addEventListener("change", function () {
          layer.visible = this.checked;
        });

        // opacity slider
        e = CE("div", item, "Opacity: <input type='range'><output></output>");
        slider = e.querySelector("input[type=range]");

        var label = e.querySelector("output");

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

        // material dropdown
        if (p.mtlNames && p.mtlNames.length > 1) {
          select = CE("select", CE("div", item, "Material: "));
          for (i = 0; i < p.mtlNames.length; i++) {
            CE("option", select, p.mtlNames[i]).setAttribute("value", i);
          }
          select.value = p.mtlIdx;
          select.addEventListener("change", function () {
            layer.setCurrentMaterial(this.value);
          });
        }
      });
      gui.layerPanel.initialized = true;
    },

    isVisible: function () {
      return E("layerpanel").classList.contains(VIS);
    },

    show: function () {
      E("layerpanel").classList.add(VIS);
    },

    hide: function () {
      E("layerpanel").classList.remove(VIS);
    }

  };

})();

/*
Q3D.Material
*/
Q3D.Material = function () {
  this.loaded = false;
};

Q3D.Material.prototype = {

  constructor: Q3D.Material,

  // material: a THREE.Material-based object
  set: function (material) {
    this.mtl = material;
    this.origProp = {};
    return this;
  },

  // callback is called when material has been completely loaded
  loadJSONObject: function (jsonObject, callback) {
    this.origProp = jsonObject;
    this.groupId = jsonObject.mtlIndex;

    var m = jsonObject, opt = {}, defer = false;

    if (m.ds && !Q3D.isIE) opt.side = THREE.DoubleSide;

    if (m.flat) opt.flatShading = true;

    // texture
    if (m.image !== undefined) {
      var _this = this;
      if (m.image.url !== undefined) {
        opt.map = Q3D.application.loadTextureFile(m.image.url, function () {
          _this._loadCompleted(callback);
        });
        defer = true;
      }
      else if (m.image.object !== undefined) {    // WebKit Bridge
        opt.map = new THREE.Texture(m.image.object.toImageData());
        opt.map.needsUpdate = true;

        delete m.image.object;
      }
      else {    // base64
        var img = new Image();
        img.onload = function () {
          opt.map.needsUpdate = true;
          _this._loadCompleted(callback);
        };
        img.src = m.image.base64;
        opt.map = new THREE.Texture(img);
        defer = true;

        delete m.image.base64;
      }
      opt.map.anisotropy = Q3D.Config.texture.anisotropy;
    }

    if (m.c !== undefined) opt.color = m.c;

    if (m.o !== undefined && m.o < 1) {
      opt.opacity = m.o;
      opt.transparent = true;
    }

    if (m.t) opt.transparent = true;

    if (m.w) opt.wireframe = true;

    if (m.bm) {
      this.mtl = new THREE.MeshBasicMaterial(opt);
    }
    else if (m.type == Q3D.MaterialType.MeshLambert) {
      this.mtl = new THREE.MeshLambertMaterial(opt);
    }
    else if (m.type == Q3D.MaterialType.MeshPhong) {
      this.mtl = new THREE.MeshPhongMaterial(opt);
    }
    else if (m.type == Q3D.MaterialType.MeshToon) {
      this.mtl = new THREE.MeshToonMaterial(opt);
    }
    else if (m.type == Q3D.MaterialType.Point) {
      opt.size = m.s;
      this.mtl = new THREE.PointsMaterial(opt);
    }
    else if (m.type == Q3D.MaterialType.Line) {

      if (m.dashed) {
        opt.dashSize = Q3D.Config.line.dash.dashSize;
        opt.gapSize = Q3D.Config.line.dash.gapSize;
        this.mtl = new THREE.LineDashedMaterial(opt);
      }
      else {
        this.mtl = new THREE.LineBasicMaterial(opt);
      }
    }
    else if (m.type == Q3D.MaterialType.MeshLine) {

      opt.lineWidth = m.thickness;
      if (m.dashed) {
        opt.dashArray = 0.03;
        opt.dashRatio = 0.45;
        opt.dashOffset = 0.015;
        opt.transparent = true;
      }
      // opt.sizeAttenuation = 1;

      var mtl = this.mtl = new MeshLineMaterial(opt);
      var updateAspect = this._listener = function () {
        mtl.resolution = new THREE.Vector2(Q3D.application.width, Q3D.application.height);
      };

      updateAspect();
      Q3D.application.addEventListener("canvasSizeChanged", updateAspect);
    }
    else if (m.type == Q3D.MaterialType.Sprite) {
      opt.color = 0xffffff;
      this.mtl = new THREE.SpriteMaterial(opt);
    }
    else {
      if (m.roughness !== undefined) opt.roughness = m.roughness;
      if (m.metalness !== undefined) opt.metalness = m.metalness;

      this.mtl = new THREE.MeshStandardMaterial(opt);
    }

    if (!defer) this._loadCompleted(callback);
  },

  _loadCompleted: function (anotherCallback) {
    this.loaded = true;

    if (this._callbacks !== undefined) {
      for (var i = 0; i < this._callbacks.length; i++) {
        this._callbacks[i]();
      }
      this._callbacks = [];
    }

    if (anotherCallback) anotherCallback();
  },

  callbackOnLoad: function (callback) {
    if (this.loaded) return callback();

    if (this._callbacks === undefined) this._callbacks = [];
    this._callbacks.push(callback);
  },

  dispose: function () {
    if (!this.mtl) return;

    if (this.mtl.map) this.mtl.map.dispose();   // dispose of texture
    this.mtl.dispose();
    this.mtl = null;

    if (this._listener) {
      Q3D.application.removeEventListener("canvasSizeChanged", this._listener);
      this._listener = undefined;
    }
  }
};

/*
Q3D.Scene -> THREE.Scene -> THREE.Object3D

scene properties (userData):
 - baseExtent(cx, cy, width, height, rotation): map base extent in map coordinates. center is (cx, cy).
 - origin: origin of 3D world in map coordinates
 - zScale: vertical scale factor
 - proj: (optional) proj string. used to display clicked position in long/lat.
*/
Q3D.Scene = function () {
  THREE.Scene.call(this);
  this.autoUpdate = false;

  this.mapLayers = {};    // map layers contained in this scene. key is layerId.

  this.lightGroup = new Q3D.Group();
  this.lightGroup.name = "light";
  this.add(this.lightGroup);

  this.labelGroup = new Q3D.Group();
  this.labelGroup.name = "label";
  this.add(this.labelGroup);

  this.labelConnectorGroup = new Q3D.Group();
  this.labelConnectorGroup.name = "label connector";
  this.add(this.labelConnectorGroup);
};

Q3D.Scene.prototype = Object.create(THREE.Scene.prototype);
Q3D.Scene.prototype.constructor = Q3D.Scene;

Q3D.Scene.prototype.add = function (object) {
  THREE.Scene.prototype.add.call(this, object);
  object.updateMatrixWorld();
};

Q3D.Scene.prototype.loadJSONObject = function (jsonObject) {
  if (jsonObject.type == "scene") {
    var p = jsonObject.properties;
    if (p !== undefined) {
      // fog
      if (p.fog) {
        this.fog = new THREE.FogExp2(p.fog.color, p.fog.density);
      }

      // light
      var rotation0 = (this.userData.baseExtent) ? this.userData.baseExtent.rotation : 0;
      if (p.light != this.userData.light || p.baseExtent.rotation != rotation0) {
        this.lightGroup.clear();
        this.buildLights(Q3D.Config.lights[p.light] || Q3D.Config.lights.directional, p.baseExtent.rotation);
        this.dispatchEvent({type: "lightChanged", light: p.light});
      }

      var be = p.baseExtent;
      p.pivot = new THREE.Vector3(be.cx, be.cy, p.origin.z).sub(p.origin);   // 2D center of extent in 3D world coordinates

      // set initial camera position and parameters
      if (this.userData.origin === undefined) {

        var s = be.width,
            v = Q3D.Config.viewpoint,
            pos, focal;

        if (v.pos === undefined) {
          v = v.default;
          if (be.rotation) {
            v = {
              pos: v.pos.clone().applyAxisAngle(Q3D.uv.k, be.rotation * Q3D.deg2rad),
              lookAt: v.lookAt.clone().applyAxisAngle(Q3D.uv.k, be.rotation * Q3D.deg2rad)
            };
          }
          pos = v.pos.clone().multiplyScalar(s).add(p.pivot);
          focal = v.lookAt.clone().multiplyScalar(s).add(p.pivot);
        }
        else {
          pos = new THREE.Vector3().copy(v.pos).sub(p.origin);
          focal = new THREE.Vector3().copy(v.lookAt).sub(p.origin);
        }

        var near = 0.001 * s,
            far = 100 * s;

        this.requestCameraUpdate(pos, focal, near, far);
      }

      if (p.baseExtent.rotation != rotation0) {
        this.dispatchEvent({type: "mapRotationChanged", rotation: p.baseExtent.rotation});
      }

      this.userData = p;
    }

    // load layers
    if (jsonObject.layers !== undefined) {
      jsonObject.layers.forEach(function (layer) {
        this.loadJSONObject(layer);
      }, this);
    }
  }
  else if (jsonObject.type == "layer") {
    var layer = this.mapLayers[jsonObject.id];
    if (layer === undefined) {
      // create a layer
      var type = jsonObject.properties.type;
      if (type == "dem") layer = new Q3D.DEMLayer();
      else if (type == "point") layer = new Q3D.PointLayer();
      else if (type == "line") layer = new Q3D.LineLayer();
      else if (type == "polygon") layer = new Q3D.PolygonLayer();
      else if (type == "pc") layer = new Q3D.PointCloudLayer();
      else {
        console.error("unknown layer type:" + type);
        return;
      }
      layer.id = jsonObject.id;
      layer.objectGroup.userData.layerId = jsonObject.id;
      layer.addEventListener("renderRequest", this.requestRender.bind(this));

      this.mapLayers[jsonObject.id] = layer;
      this.add(layer.objectGroup);
    }

    layer.loadJSONObject(jsonObject, this);

    this.requestRender();
  }
  else if (jsonObject.type == "block") {
    var layer = this.mapLayers[jsonObject.layer];
    if (layer === undefined) {
      // console.error("layer not exists:" + jsonObject.layer);
      return;
    }
    layer.loadJSONObject(jsonObject, this);

    this.requestRender();
  }
};

Q3D.Scene.prototype.buildLights = function (lights, rotation) {
  var p, light;
  for (var i = 0; i < lights.length; i++) {
    p = lights[i];
    if (p.type == "ambient") {
      light = new THREE.AmbientLight(p.color, p.intensity);
    }
    else if (p.type == "directional") {
      light = new THREE.DirectionalLight(p.color, p.intensity);
      light.position.copy(Q3D.uv.j)
                    .applyAxisAngle(Q3D.uv.i, p.altitude * Q3D.deg2rad)
                    .applyAxisAngle(Q3D.uv.k, (rotation - p.azimuth) * Q3D.deg2rad);
    }
    else if (p.type == "point") {
      light = new THREE.PointLight(p.color, p.intensity);
      light.position.set(0, 0, p.height);
    }
    else {
      continue;
    }
    this.lightGroup.add(light);
  }
};

Q3D.Scene.prototype.requestRender = function () {
  this.dispatchEvent({type: "renderRequest"});
};

Q3D.Scene.prototype.requestCameraUpdate = function (pos, focal, near, far) {
  this.dispatchEvent({type: "cameraUpdateRequest", pos: pos, focal: focal, near: near, far: far});
};

Q3D.Scene.prototype.visibleObjects = function (labelVisible) {
  var layer, objs = [];
  for (var id in this.mapLayers) {
    layer = this.mapLayers[id];
    if (layer.visible) {
      objs = objs.concat(layer.visibleObjects());
      if (labelVisible && layer.labels) objs = objs.concat(layer.labels);
    }
  }
  return objs;
};

// 3D world coordinates to map coordinates
Q3D.Scene.prototype.toMapCoordinates = function (pt) {
  var p = this.userData;
  return {
    x: p.origin.x + pt.x,
    y: p.origin.y + pt.y,
    z: p.origin.z + pt.z / p.zScale
  };
};

// map coordinates to 3D world coordinates
Q3D.Scene.prototype.toWorldCoordinates = function (pt, isLonLat) {
  var p = this.userData;
  if (isLonLat && typeof proj4 !== "undefined") {
    // WGS84 long,lat to map coordinates
    var t = proj4(p.proj).forward([pt.x, pt.y]);
    pt = {x: t[0], y: t[1], z: pt.z};
  }

  return {
    x: pt.x - p.origin.x,
    y: pt.y - p.origin.y,
    z: (pt.z - p.origin.z) * p.zScale
  };
};

// return bounding box in 3d world coordinates
Q3D.Scene.prototype.boundingBox = function () {
  var box = new THREE.Box3();
  for (var id in this.mapLayers) {
    if (this.mapLayers[id].visible) {
      box.union(this.mapLayers[id].boundingBox());
    }
  }
  return box;
};

/*
Q3D.Materials
*/
Q3D.Materials = function () {
  this.array = [];
};

Q3D.Materials.prototype = Object.create(THREE.EventDispatcher.prototype);
Q3D.Materials.prototype.constructor = Q3D.Materials;

// material: instance of Q3D.Material object or THREE.Material-based object
Q3D.Materials.prototype.add = function (material) {
  if (material instanceof Q3D.Material) {
    this.array.push(material);
  }
  else {
    this.array.push(new Q3D.Material().set(material));
  }
};

Q3D.Materials.prototype.get = function (index) {
  return this.array[index];
};

Q3D.Materials.prototype.mtl = function (index) {
  return this.array[index].mtl;
};

Q3D.Materials.prototype.loadJSONObject = function (jsonObject) {
  var _this = this, iterated = false;
  var callback = function () {
    if (iterated) _this.dispatchEvent({type: "renderRequest"});
  };

  for (var i = 0, l = jsonObject.length; i < l; i++) {
    var mtl = new Q3D.Material();
    mtl.loadJSONObject(jsonObject[i], callback);
    this.add(mtl);
  }
  iterated = true;
};

Q3D.Materials.prototype.dispose = function () {
  for (var i = 0, l = this.array.length; i < l; i++) {
    this.array[i].dispose();
  }
  this.array = [];
};

Q3D.Materials.prototype.addFromObject3D = function (object) {
  var mtls = [];

  object.traverse(function (obj) {
    if (obj.material === undefined) return;
    ((obj.material instanceof Array) ? obj.material : [obj.material]).forEach(function (mtl) {
      if (mtls.indexOf(mtl) == -1) {
        mtls.push(mtl);
      }
    });
  });

  for (var i = 0, l = mtls.length; i < l; i++) {
    this.array.push(new Q3D.Material().set(mtls[i]));
  }
};

// opacity
Q3D.Materials.prototype.opacity = function () {
  if (this.array.length == 0) return 1;

  var sum = 0;
  for (var i = 0, l = this.array.length; i < l; i++) {
    sum += this.array[i].mtl.opacity;
  }
  return sum / this.array.length;
};

Q3D.Materials.prototype.setOpacity = function (opacity) {
  var m;
  for (var i = 0, l = this.array.length; i < l; i++) {
    m = this.array[i];
    m.mtl.transparent = Boolean(m.origProp.t) || (opacity < 1);
    m.mtl.opacity = opacity;
  }
};

// wireframe: boolean
Q3D.Materials.prototype.setWireframeMode = function (wireframe) {
  var m;
  for (var i = 0, l = this.array.length; i < l; i++) {
    m = this.array[i];
    if (m.origProp.w || m.mtl instanceof THREE.LineBasicMaterial) continue;
    m.mtl.wireframe = wireframe;
  }
};

Q3D.Materials.prototype.removeItem = function (material, dispose) {
  for (var i = this.array.length - 1; i >= 0; i--) {
    if (this.array[i].mtl === material) {
      this.array.splice(i, 1);
      break;
    }
  }
  if (dispose) material.dispose();
};

Q3D.Materials.prototype.removeGroupItems = function (groupId) {
  for (var i = this.array.length - 1; i >= 0; i--) {
    if (this.array[i].groupId === groupId) {
      this.array.splice(i, 1);
    }
  }
};

/*
Q3D.DEMBlock
*/
Q3D.DEMBlock = function () {
  this.materials = [];
  this.currentMtlIndex = 0;
};

Q3D.DEMBlock.prototype = {

  constructor: Q3D.DEMBlock,

  // obj: object decoded from JSON
  loadJSONObject: function (obj, layer, callback) {

    this.data = obj;

    // load material
    var m, mtl;
    for (var i = 0, l = (obj.materials || []).length; i < l; i++) {
      m = obj.materials[i];

      mtl = new Q3D.Material();
      mtl.loadJSONObject(m, function () {
        layer.requestRender();
      });
      this.materials[m.mtlIndex] = mtl;

      if (m.useNow) {
        this.currentMtlIndex = m.mtlIndex;
        if (this.obj) {
          layer.materials.removeItem(this.obj.material, true);

          this.obj.material = mtl.mtl;
          layer.requestRender();
        }
        layer.materials.add(mtl);
      }
    }

    if (obj.grid === undefined) return;

    // create a plane geometry
    var geom, grid = obj.grid;
    if (layer.geometryCache) {
      var params = layer.geometryCache.parameters || {};
      if (params.width === obj.width && params.height === obj.height &&
          params.widthSegments === grid.width - 1 && params.heightSegments === grid.height - 1) {
        geom = layer.geometryCache.clone();
        geom.parameters = layer.geometryCache.parameters;
      }
    }
    geom = geom || new THREE.PlaneBufferGeometry(obj.width, obj.height, grid.width - 1, grid.height - 1);
    layer.geometryCache = geom;

    // create a mesh
    var mesh = new THREE.Mesh(geom, (this.materials[this.currentMtlIndex] || {}).mtl);
    mesh.position.fromArray(obj.translate);
    mesh.scale.z = obj.zScale;
    layer.addObject(mesh);

    // set z values
    var buildGeometry = function (grid_values) {
      var vertices = geom.attributes.position.array;
      for (var i = 0, j = 0, l = vertices.length; i < l; i++, j += 3) {
        vertices[j + 2] = grid_values[i];
      }
      geom.attributes.position.needsUpdate = true;
      geom.computeVertexNormals();

      if (callback) callback(mesh);
    };

    if (grid.url !== undefined) {
      Q3D.application.loadFile(grid.url, "arraybuffer", function (buf) {
        grid.array = new Float32Array(buf);
        buildGeometry(grid.array);
      });
    }
    else {    // local mode or WebKit Bridge
      if (grid.binary !== undefined) grid.array = new Float32Array(grid.binary.buffer, 0, grid.width * grid.height);
      buildGeometry(grid.array);
    }

    this.obj = mesh;
    return mesh;
  },

  buildSides: function (layer, parent, material, z0) {
    var planeWidth = this.data.width,
        planeHeight = this.data.height,
        grid = this.data.grid,
        grid_values = grid.array,
        w = grid.width,
        h = grid.height,
        k = w * (h - 1);

    var band_width = -2 * z0;

    // front and back
    var geom_fr = new THREE.PlaneBufferGeometry(planeWidth, band_width, w - 1, 1),
        geom_ba = geom_fr.clone();

    var vertices_fr = geom_fr.attributes.position.array,
        vertices_ba = geom_ba.attributes.position.array;

    var i, mesh;
    for (i = 0; i < w; i++) {
      vertices_fr[i * 3 + 1] = grid_values[k + i];
      vertices_ba[i * 3 + 1] = grid_values[w - 1 - i];
    }
    mesh = new THREE.Mesh(geom_fr, material);
    mesh.rotation.x = Math.PI / 2;
    mesh.position.y = -planeHeight / 2;
    mesh.name = "side";
    parent.add(mesh);

    mesh = new THREE.Mesh(geom_ba, material);
    mesh.rotation.x = Math.PI / 2;
    mesh.rotation.y = Math.PI;
    mesh.position.y = planeHeight / 2;
    mesh.name = "side";
    parent.add(mesh);

    // left and right
    var geom_le = new THREE.PlaneBufferGeometry(band_width, planeHeight, 1, h - 1),
        geom_ri = geom_le.clone();

    var vertices_le = geom_le.attributes.position.array,
        vertices_ri = geom_ri.attributes.position.array;

    for (i = 0; i < h; i++) {
      vertices_le[(i * 2 + 1) * 3] = grid_values[w * i];
      vertices_ri[i * 2 * 3] = -grid_values[w * (i + 1) - 1];
    }
    mesh = new THREE.Mesh(geom_le, material);
    mesh.rotation.y = -Math.PI / 2;
    mesh.position.x = -planeWidth / 2;
    mesh.name = "side";
    parent.add(mesh);

    mesh = new THREE.Mesh(geom_ri, material);
    mesh.rotation.y = Math.PI / 2;
    mesh.position.x = planeWidth / 2;
    mesh.name = "side";
    parent.add(mesh);

    // bottom
    var geom = new THREE.PlaneBufferGeometry(planeWidth, planeHeight, 1, 1);
    mesh = new THREE.Mesh(geom, material);
    mesh.rotation.x = Math.PI;
    mesh.position.z = z0;
    mesh.name = "bottom";
    parent.add(mesh);

    parent.updateMatrixWorld();
  },

  addEdges: function (layer, parent, material, z0) {

    var i, x, y,
        grid = this.data.grid,
        grid_values = grid.array,
        w = grid.width,
        h = grid.height,
        k = w * (h - 1),
        planeWidth = this.data.width,
        planeHeight = this.data.height,
        hpw = planeWidth / 2,
        hph = planeHeight / 2,
        psw = planeWidth / (w - 1),
        psh = planeHeight / (h - 1);

    var vl = [];

    // terrain edges
    var vl_fr = [],
        vl_bk = [],
        vl_le = [],
        vl_ri = [];

    for (i = 0; i < w; i++) {
      x = -hpw + psw * i;
      vl_fr.push(x, -hph, grid_values[k + i]);
      vl_bk.push(x, hph, grid_values[i]);
    }

    for (i = 0; i < h; i++) {
      y = hph - psh * i;
      vl_le.push(-hpw, y, grid_values[w * i]);
      vl_ri.push(hpw, y, grid_values[w * (i + 1) - 1]);
    }

    vl.push(vl_fr, vl_bk, vl_le, vl_ri);

    if (z0 !== undefined) {
      // horizontal rectangle at bottom
      vl.push([-hpw, -hph, z0,
                hpw, -hph, z0,
                hpw,  hph, z0,
               -hpw,  hph, z0,
               -hpw, -hph, z0]);

      // vertical lines at corners
      [[-hpw, -hph, grid_values[grid_values.length - w]],
       [ hpw, -hph, grid_values[grid_values.length - 1]],
       [ hpw,  hph, grid_values[w - 1]],
       [-hpw,  hph, grid_values[0]]].forEach(function (v) {

        vl.push([v[0], v[1], v[2], v[0], v[1], z0]);

      });
    }

    vl.forEach(function (v) {

      var geom = new THREE.BufferGeometry().setAttribute("position", new THREE.Float32BufferAttribute(v, 3));
      var obj = new THREE.Line(geom, material);
      obj.name = "frame";
      parent.add(obj);

    });

    parent.updateMatrixWorld();
  },

  // add quad wireframe
  addWireframe: function (layer, parent, material) {

    var grid = this.data.grid,
        grid_values = grid.array,
        w = grid.width,
        h = grid.height,
        planeWidth = this.data.width,
        planeHeight = this.data.height,
        hpw = planeWidth / 2,
        hph = planeHeight / 2,
        psw = planeWidth / (w - 1),
        psh = planeHeight / (h - 1);

    var v, geom, x, y, vx, vy, group = new THREE.Group();

    for (x = w - 1; x >= 0; x--) {
      v = [];
      vx = -hpw + psw * x;

      for (y = h - 1; y >= 0; y--) {
        v.push(vx, hph - psh * y, grid_values[x + w * y]);
      }

      geom = new THREE.BufferGeometry().setAttribute("position", new THREE.Float32BufferAttribute(v, 3));

      group.add(new THREE.Line(geom, material));
    }

    for (y = h - 1; y >= 0; y--) {
      v = [];
      vy = hph - psh * y;

      for (x = w - 1; x >= 0; x--) {
        v.push(-hpw + psw * x, vy, grid_values[x + w * y]);
      }

      geom = new THREE.BufferGeometry().setAttribute("position", new THREE.Float32BufferAttribute(v, 3));

      group.add(new THREE.Line(geom, material));
    }

    parent.add(group);
    parent.updateMatrixWorld();
  },

  getValue: function (x, y) {
    var grid = this.data.grid;
    if (0 <= x && x < grid.width && 0 <= y && y < grid.height) return grid.array[x + grid.width * y];
    return null;
  },

  contains: function (x, y) {
    var translate = this.data.translate,
        xmin = translate[0] - this.data.width / 2,
        xmax = translate[0] + this.data.width / 2,
        ymin = translate[1] - this.data.height / 2,
        ymax = translate[1] + this.data.height / 2;
    if (xmin <= x && x <= xmax && ymin <= y && y <= ymax) return true;
    return false;
  }

};


/*
Q3D.ClippedDEMBlock
*/
Q3D.ClippedDEMBlock = function () {
  this.materials = [];
  this.currentMtlIndex = 0;
};

Q3D.ClippedDEMBlock.prototype = {

  constructor: Q3D.ClippedDEMBlock,

  loadJSONObject: function (obj, layer, callback) {
    this.data = obj;
    var _this = this;

    // load material
    var m, mtl;
    for (var i = 0, l = (obj.materials || []).length; i < l; i++) {
      m = obj.materials[i];

      mtl = new Q3D.Material();
      mtl.loadJSONObject(m, function () {
        layer.requestRender();
      });
      this.materials[m.mtlIndex] = mtl;

      if (m.useNow) {
        if (this.obj) {
          layer.materials.removeItem(this.obj.material, true);

          this.obj.material = mtl.mtl;

          layer.materials.add(mtl);
          layer.requestRender();
        }
        this.currentMtlIndex = m.mtlIndex;
      }
    }

    if (obj.geom === undefined) return;

    var geom = new THREE.BufferGeometry(),
        mesh = new THREE.Mesh(geom, (this.materials[this.currentMtlIndex] || {}).mtl);
    mesh.position.fromArray(obj.translate);
    mesh.scale.z = obj.zScale;
    layer.addObject(mesh);

    var buildGeometry = function (obj) {

      var v = obj.triangles.v,
          origin = layer.sceneData.origin,
          be = layer.sceneData.baseExtent,
          base_width = be.width,
          base_height = be.height,
          x0 = be.cx - origin.x - base_width * 0.5,
          y0 = be.cy - origin.y - base_height * 0.5;

      var normals = [], uvs = [];
      for (var i = 0, l = v.length; i < l; i += 3) {
        normals.push(0, 0, 1);
        uvs.push((v[i] - x0) / base_width, (v[i + 1] - y0) / base_height);
      }

      geom.setIndex(obj.triangles.f);
      geom.setAttribute("position", new THREE.Float32BufferAttribute(v, 3));
      geom.setAttribute("normal", new THREE.Float32BufferAttribute(normals, 3));
      geom.setAttribute("uv", new THREE.Float32BufferAttribute(uvs, 2));
      geom.computeVertexNormals();

      geom.attributes.position.needsUpdate = true;
      geom.attributes.normal.needsUpdate = true;
      geom.attributes.uv.needsUpdate = true;

      _this.data.polygons = obj.polygons;
      if (callback) callback(mesh);
    };

    if (obj.geom.url !== undefined) {
      Q3D.application.loadFile(obj.geom.url, "json", function (obj) {
        buildGeometry(obj);
      });
    }
    else {    // local mode or WebKit Bridge
      buildGeometry(obj.geom);
    }

    this.obj = mesh;
    return mesh;
  },

  buildSides: function (layer, parent, material, z0) {
    var polygons = this.data.polygons,
        bzFunc = function (x, y) { return z0; };

    // make back-side material for bottom
    var mat_back = material.clone();
    mat_back.side = THREE.BackSide;
    layer.materials.add(mat_back);

    var geom, mesh, shape;
    for (var i = 0, l = polygons.length; i < l; i++) {
      var bnds = polygons[i];

      // sides
      for (var j = 0, m = bnds.length; j < m; j++) {
        geom = Q3D.Utils.createWallGeometry(bnds[j], bzFunc, true);
        mesh = new THREE.Mesh(geom, material);
        mesh.name = "side";
        parent.add(mesh);
      }

      // bottom
      shape = new THREE.Shape(Q3D.Utils.flatArrayToVec2Array(bnds[0], 3));
      for (j = 1, m = bnds.length; j < m; j++) {
        shape.holes.push(new THREE.Path(Q3D.Utils.flatArrayToVec2Array(bnds[j], 3)));
      }
      geom = new THREE.ShapeBufferGeometry(shape);
      mesh = new THREE.Mesh(geom, mat_back);
      mesh.position.z = z0;
      mesh.name = "bottom";
      parent.add(mesh);
    }
    parent.updateMatrixWorld();
  },

  // not implemented
  getValue: function (x, y) {
    return null;
  },

  // not implemented
  contains: function (x, y) {
    return false;
  }

};

/*
Q3D.MapLayer
*/
Q3D.MapLayer = function () {
  this.properties = {};

  this.materials = new Q3D.Materials();
  this.materials.addEventListener("renderRequest", this.requestRender.bind(this));

  this.objectGroup = new Q3D.Group();
  this.objectGroup.name = "layer";
  this.objects = [];
};

Q3D.MapLayer.prototype = Object.create(THREE.EventDispatcher.prototype);
Q3D.MapLayer.prototype.constructor = Q3D.MapLayer;

Q3D.MapLayer.prototype.addObject = function (object) {

  object.userData.layerId = this.id;
  this.objectGroup.add(object);

  var o = this.objects;
  object.traverse(function (obj) {
    o.push(obj);
  });
  return this.objectGroup.children.length - 1;
};

Q3D.MapLayer.prototype.addObjects = function (objects) {
  for (var i = 0; i < objects.length; i++) {
    this.addObject(objects[i]);
  }
};

Q3D.MapLayer.prototype.clearObjects = function () {
  // dispose of geometries
  this.objectGroup.traverse(function (obj) {
    if (obj.geometry) obj.geometry.dispose();
  });

  // dispose of materials
  this.materials.dispose();

  // remove all child objects from object group
  for (var i = this.objectGroup.children.length - 1; i >= 0; i--) {
    this.objectGroup.remove(this.objectGroup.children[i]);
  }
  this.objects = [];
};

Q3D.MapLayer.prototype.visibleObjects = function () {
  return (this.visible) ? this.objects : [];
};

Q3D.MapLayer.prototype.loadJSONObject = function (jsonObject, scene) {
  if (jsonObject.type == "layer") {
    // properties
    if (jsonObject.properties !== undefined) {
      this.properties = jsonObject.properties;
      this.visible = (jsonObject.properties.visible || Q3D.Config.allVisible) ? true : false;
    }

    if (jsonObject.data !== undefined) {
      this.clearObjects();

      // materials
      if (jsonObject.data.materials !== undefined) {
        this.materials.loadJSONObject(jsonObject.data.materials);
      }
    }

    this.sceneData = scene.userData;
  }
};

Object.defineProperty(Q3D.MapLayer.prototype, "clickable", {
  get: function () {
    return this.properties.clickable;
  }
});

Object.defineProperty(Q3D.MapLayer.prototype, "opacity", {
  get: function () {
    return this.materials.opacity();
  },
  set: function (value) {
    this.materials.setOpacity(value);

    if (this.labelGroup) {
      this.labelGroup.traverse(function (obj) {
        if (obj.material) obj.material.opacity = value;
      });
    }

    if (this.labelConnectorGroup && this.labelConnectorGroup.children.length) {
      this.labelConnectorGroup.children[0].material.opacity = value;
    }

    this.requestRender();
  }
});

Object.defineProperty(Q3D.MapLayer.prototype, "visible", {
  get: function () {
    return this.objectGroup.visible;
  },
  set: function (value) {
    this.objectGroup.visible = value;
    this.requestRender();
  }
});

Q3D.MapLayer.prototype.boundingBox = function () {
  return new THREE.Box3().setFromObject(this.objectGroup);
};

Q3D.MapLayer.prototype.setWireframeMode = function (wireframe) {
  this.materials.setWireframeMode(wireframe);
};

Q3D.MapLayer.prototype.requestRender = function () {
  this.dispatchEvent({type: "renderRequest"});
};


/*
Q3D.DEMLayer --> Q3D.MapLayer
*/
Q3D.DEMLayer = function () {
  Q3D.MapLayer.call(this);
  this.type = Q3D.LayerType.DEM;
  this.blocks = [];
};

Q3D.DEMLayer.prototype = Object.create(Q3D.MapLayer.prototype);
Q3D.DEMLayer.prototype.constructor = Q3D.DEMLayer;

Q3D.DEMLayer.prototype.loadJSONObject = function (jsonObject, scene) {
  var old_blockIsClipped = this.properties.clipped;

  Q3D.MapLayer.prototype.loadJSONObject.call(this, jsonObject, scene);
  if (jsonObject.type == "layer") {
    if (old_blockIsClipped !== jsonObject.properties.clipped) {
      // DEM type changed
      this.blocks = [];
    }

    var p = scene.userData,
        rotation = p.baseExtent.rotation;

    if (jsonObject.properties.clipped) {
      this.objectGroup.position.set(0, 0, 0);
      this.objectGroup.rotation.z = 0;

      if (rotation) {
        // rotate around center of base extent
        this.objectGroup.position.copy(p.pivot).negate();
        this.objectGroup.position.applyAxisAngle(Q3D.uv.k, rotation * Q3D.deg2rad);
        this.objectGroup.position.add(p.pivot);
        this.objectGroup.rotateOnAxis(Q3D.uv.k, rotation * Q3D.deg2rad);
      }
    }
    else {
      this.objectGroup.position.copy(p.pivot);
      this.objectGroup.position.z *= p.zScale;
      this.objectGroup.rotation.z = rotation * Q3D.deg2rad;
    }
    this.objectGroup.updateMatrixWorld();

    if (jsonObject.data !== undefined) {
      jsonObject.data.forEach(function (obj) {
        this.buildBlock(obj, scene, this);
      }, this);
    }
  }
  else if (jsonObject.type == "block") {
    this.buildBlock(jsonObject, scene, this);
  }
};

Q3D.DEMLayer.prototype.buildBlock = function (jsonObject, scene, layer) {
  var _this = this,
      block = this.blocks[jsonObject.block];

  if (block === undefined) {
    block = (layer.properties.clipped) ? (new Q3D.ClippedDEMBlock()) : (new Q3D.DEMBlock());
    this.blocks[jsonObject.block] = block;
  }

  block.loadJSONObject(jsonObject, this, function (mesh) {

    var material;
    if (jsonObject.wireframe) {
      material = new Q3D.Material();
      material.loadJSONObject(jsonObject.wireframe.mtl);
      _this.materials.add(material);

      block.addWireframe(_this, mesh, material.mtl);

      var mtl = block.material.mtl;
      mtl.polygonOffset = true;
      mtl.polygonOffsetFactor = 1;
      mtl.polygonOffsetUnits = 1;
    }

    if (jsonObject.sides) {
      // sides and bottom
      material = new Q3D.Material();
      material.loadJSONObject(jsonObject.sides.mtl);
      _this.materials.add(material);

      block.buildSides(_this, mesh, material.mtl, jsonObject.sides.bottom);
      _this.sideVisible = true;
    }

    if (jsonObject.edges) {
      material = new Q3D.Material();
      material.loadJSONObject(jsonObject.edges.mtl);
      _this.materials.add(material);

      block.addEdges(_this, mesh, material.mtl, (jsonObject.sides) ? jsonObject.sides.bottom : undefined);
    }

    _this.requestRender();
  });
};

// calculate elevation at the coordinates (x, y) on triangle face
Q3D.DEMLayer.prototype.getZ = function (x, y) {
  for (var i = 0, l = this.blocks.length; i < l; i++) {
    var block = this.blocks[i],
        data = block.data;
    if (!block.contains(x, y)) continue;

    var ix = data.width / (data.grid.width - 1),
        iy = data.height / (data.grid.height - 1);

    var xmin = data.translate[0] - data.width / 2,
        ymax = data.translate[1] + data.height / 2;

    var mx0 = Math.floor((x - xmin) / ix),
        my0 = Math.floor((ymax - y) / iy);

    var z = [block.getValue(mx0, my0),
             block.getValue(mx0 + 1, my0),
             block.getValue(mx0, my0 + 1),
             block.getValue(mx0 + 1, my0 + 1)];

    var px0 = xmin + ix * mx0,
        py0 = ymax - iy * my0;

    var sdx = (x - px0) / ix,
        sdy = (py0 - y) / iy;

    if (sdx <= 1 - sdy) return z[0] + (z[1] - z[0]) * sdx + (z[2] - z[0]) * sdy;
    else return z[3] + (z[2] - z[3]) * (1 - sdx) + (z[1] - z[3]) * (1 - sdy);
  }
  return null;
};

Q3D.DEMLayer.prototype.segmentizeLineString = function (lineString, zFunc) {
  // does not support multiple blocks
  if (zFunc === undefined) zFunc = function () { return 0; };
  var width = this.sceneData.width,
      height = this.sceneData.height;
  var xmin = -width / 2,
      ymax = height / 2;
  var grid = this.blocks[0].data.grid,
      ix = width / (grid.width - 1),
      iy = height / (grid.height - 1);
  var sort_func = function (a, b) { return a - b; };

  var pts = [];
  for (var i = 1, l = lineString.length; i < l; i++) {
    var pt1 = lineString[i - 1], pt2 = lineString[i];
    var x1 = pt1[0], x2 = pt2[0], y1 = pt1[1], y2 = pt2[1], z1 = pt1[2], z2 = pt2[2];
    var nx1 = (x1 - xmin) / ix,
        nx2 = (x2 - xmin) / ix;
    var ny1 = (ymax - y1) / iy,
        ny2 = (ymax - y2) / iy;
    var ns1 = Math.abs(ny1 + nx1),
        ns2 = Math.abs(ny2 + nx2);

    var p = [0], nvp = [[nx1, nx2], [ny1, ny2], [ns1, ns2]];
    for (var j = 0; j < 3; j++) {
      var v1 = nvp[j][0], v2 = nvp[j][1];
      if (v1 == v2) continue;
      var k = Math.ceil(Math.min(v1, v2));
      var n = Math.floor(Math.max(v1, v2));
      for (; k <= n; k++) {
        p.push((k - v1) / (v2 - v1));
      }
    }

    p.sort(sort_func);

    var x, y, z, lp = null;
    for (var j = 0, m = p.length; j < m; j++) {
      if (lp === p[j]) continue;
      if (p[j] == 1) break;

      x = x1 + (x2 - x1) * p[j];
      y = y1 + (y2 - y1) * p[j];

      if (z1 === undefined || z2 === undefined) z = zFunc(x, y);
      else z = z1 + (z2 - z1) * p[j];

      pts.push(new THREE.Vector3(x, y, z));

      // Q3D.Utils.putStick(x, y, zFunc);

      lp = p[j];
    }
  }
  // last point (= the first point)
  var pt = lineString[lineString.length - 1];
  pts.push(new THREE.Vector3(pt[0], pt[1], (pt[2] === undefined) ? zFunc(pt[0], pt[1]) : pt[2]));

  /*
  for (var i = 0, l = lineString.length - 1; i < l; i++) {
    Q3D.Utils.putStick(lineString[i][0], lineString[i][1], zFunc, 0.8);
  }
  */
  return pts;
};

Q3D.DEMLayer.prototype.setCurrentMaterial = function (mtlIndex) {

  this.materials.removeGroupItems(this.currentMtlIndex);

  this.currentMtlIndex = mtlIndex;

  var b, m;
  for (var i = 0, l = this.blocks.length; i < l; i++) {
    b = this.blocks[i];
    m = b.materials[mtlIndex];
    if (m !== undefined) {
      b.obj.material = m.mtl;
      this.materials.add(m);
    }
  }
  this.requestRender();
};

Q3D.DEMLayer.prototype.setSideVisible = function (visible) {
  this.sideVisible = visible;
  this.objectGroup.traverse(function (obj) {
    if (obj.name == "side" || obj.name == "bottom") obj.visible = visible;
  });
};

// texture animation
Q3D.DEMLayer.prototype.prepareTexAnimation = function (from, to) {

  function imageData2Canvas(img) {
    var cnvs = document.createElement("canvas");
    cnvs.width = img.width;
    cnvs.height = img.height;

    var ctx = cnvs.getContext("2d");
    ctx.putImageData(img, 0, 0);
    return cnvs;
  }

  this.anim = [];

  var m, canvas, ctx, opt, mtl;
  var img_from, img_to;
  for (var i = 0; i < this.blocks.length; i++) {

    m = this.blocks[i].obj.material;

    img_from = this.blocks[i].materials[from].mtl.map.image;
    img_to = this.blocks[i].materials[to].mtl.map.image;

    canvas = document.createElement("canvas");
    canvas.width = (img_from.width > img_to.width) ? img_from.width : img_to.width;
    canvas.height = (img_from.width > img_to.width) ? img_from.height : img_to.height;

    ctx = canvas.getContext("2d");

    opt = {};
    opt.map = new THREE.CanvasTexture(canvas);
    opt.map.anisotropy = Q3D.Config.texture.anisotropy;
    opt.transparent = true;

    mtl = undefined;
    if (m) {
      if (m.isMeshToonMaterial) {
        mtl = new THREE.MeshToonMaterial(opt);
      }
      else if (m.isMeshPhongMaterial) {
        mtl = new THREE.MeshPhongMaterial(opt);
      }
    }
    if (mtl === undefined) {
      mtl = new THREE.MeshLambertMaterial(opt);
    }

    if (img_from instanceof ImageData) {    // WebKit Bridge
      img_from = imageData2Canvas(img_from);
      img_to = imageData2Canvas(img_to);
    }

    this.blocks[i].obj.material = mtl;

    this.materials.add(mtl);

    this.anim.push({
      img_from: img_from,
      img_to: img_to,
      ctx: ctx,
      tex: mtl.map
    });
  }
};

Q3D.DEMLayer.prototype.setTextureAt = function (progress, effect) {

  if (this.anim === undefined) return;

  var a, w, h, w0, h0, w1, h1, ew, ew1;
  for (var i = 0; i < this.anim.length; i++) {
    a = this.anim[i];
    w = a.ctx.canvas.width;
    h = a.ctx.canvas.height;
    w0 = a.img_from.width;
    h0 = a.img_from.height;
    w1 = a.img_to.width;
    h1 = a.img_to.height;

    if (effect == 0) {  // fade in
      a.ctx.globalAlpha = 1;
      a.ctx.drawImage(a.img_from, 0, 0, w0, h0,
                                  0, 0, w, h);
      a.ctx.globalAlpha = progress;
      a.ctx.drawImage(a.img_to, 0, 0, w1, h1,
                                0, 0, w, h);
    }
    else if (effect == 2) {  // slide to left (not used)
      if (progress === null) {
        a.ctx.drawImage(a.img_from, 0, 0, w0, h0,
                                    0, 0, w, h);
      }
      else {
        ew1 = w1 * progress;
        ew = w * progress;
        a.ctx.drawImage(a.img_to, w1 - ew1, 0, ew1, h1,
                                  w - ew, 0, ew, h);
      }
    }
    a.tex.needsUpdate = true;
  }
};

/*
Q3D.VectorLayer --> Q3D.MapLayer
*/
Q3D.VectorLayer = function () {
  Q3D.MapLayer.call(this);

  this.features = [];
  this.labels = [];
};

Q3D.VectorLayer.prototype = Object.create(Q3D.MapLayer.prototype);
Q3D.VectorLayer.prototype.constructor = Q3D.VectorLayer;

// Q3D.VectorLayer.prototype.build = function (features, startIndex) {};

Q3D.VectorLayer.prototype.addFeature = function (featureIdx, f, objs) {
  Q3D.MapLayer.prototype.addObjects.call(this, objs);

  for (var i = 0; i < objs.length; i++) {
    objs[i].userData.featureIdx = featureIdx;
  }
  f.objs = objs;

  this.features[featureIdx] = f;
  return f;
};

Q3D.VectorLayer.prototype.clearLabels = function () {
  this.labels = [];
  if (this.labelGroup) this.labelGroup.clear();
  if (this.labelConnectorGroup) this.labelConnectorGroup.clear();
};

Q3D.VectorLayer.prototype.buildLabels = function (features, getPointsFunc) {
  if (this.properties.label === undefined || getPointsFunc === undefined) return;

  var _this = this,
      p = this.properties,
      label = p.label,
      bs = this.sceneData.baseExtent.width * 0.016,
      sc = bs * Math.pow(1.2, label.size);

  var hasOtl = (label.olcolor !== undefined),
      hasConn = (label.cncolor !== undefined);

  if (hasConn) {
    var line_mtl = new THREE.LineBasicMaterial({
      color: label.cncolor,
      opacity: this.materials.opacity(),
      transparent: true
    });
  }

  var hasUnderline = Boolean(hasConn && label.underline);
  if (hasUnderline) {
    var ul_geom = new THREE.BufferGeometry();
    ul_geom.setAttribute("position", new THREE.Float32BufferAttribute([0, 0, 0, 1, 0, 0], 3));

    var onBeforeRender = function (renderer, scene, camera, geometry, material, group) {
      this.quaternion.copy(camera.quaternion);
      this.updateMatrixWorld();
    };
  }

  var canvas = document.createElement("canvas"),
      ctx = canvas.getContext("2d");

  var font, tw, th, cw, ch;
  th = ch = Q3D.Config.label.canvasHeight;
  font = th + "px " + (label.font || "sans-serif");

  canvas.height = ch;

  var f, text, partIdx, vec, sprite, mtl, geom, conn, x, y, j, sc, opacity;
  var underline;

  for (var i = 0, l = features.length; i < l; i++) {
    f = features[i];
    text = f.lbl;
    if (!text) continue;

    opacity = this.materials.mtl(f.mtl).opacity;

    partIdx = 0;
    getPointsFunc(f).forEach(function (pt) {

      // label position
      vec = new THREE.Vector3(pt[0], pt[1], (label.relative) ? pt[2] + f.lh : f.lh);

      // render label text
      ctx.font = font;
      tw = ctx.measureText(text).width + 2;
      cw = THREE.Math.ceilPowerOfTwo(tw);
      x = cw / 2;
      y = ch / 2;

      canvas.width = cw;
      ctx.clearRect(0, 0, cw, ch);

      if (label.bgcolor !== undefined) {
        ctx.fillStyle = label.bgcolor;
        ctx.roundRect((cw - tw) / 2, (ch - th) / 2, tw, th, 4).fill();    // definition is in this file
      }

      ctx.font = font;
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";

      if (hasOtl) {
        // outline effect
        ctx.fillStyle = label.olcolor;
        for (j = 0; j < 9; j++) {
          if (j != 4) ctx.fillText(text, x + Math.floor(j / 3) - 1, y + j % 3 - 1);
        }
      }

      ctx.fillStyle = label.color;
      ctx.fillText(text, x, y);

      mtl = new THREE.SpriteMaterial({
        map: new THREE.TextureLoader().load(canvas.toDataURL(), function () { _this.requestRender(); }),
        opacity: opacity,
        transparent: true
      });

      sprite = new THREE.Sprite(mtl);
      if (hasUnderline) {
        sprite.center.set((1 - tw / cw) * 0.5, 0);
      }
      else {
        sprite.center.set(0.5, 0);
      }
      sprite.position.copy(vec);
      sprite.scale.set(sc * cw / ch, sc, 1);

      sprite.userData.layerId = this.id;
      sprite.userData.properties = f.prop;
      sprite.userData.objs = f.objs;
      sprite.userData.partIdx = partIdx;
      sprite.userData.isLabel = true;

      this.labelGroup.add(sprite);

      if (Q3D.Config.label.clickable) this.labels.push(sprite);

      if (hasConn) {
        // a connector
        geom = new THREE.BufferGeometry();
        geom.setAttribute("position", new THREE.Float32BufferAttribute(vec.toArray().concat(pt), 3));

        conn = new THREE.Line(geom, line_mtl);
        conn.userData = sprite.userData;

        this.labelConnectorGroup.add(conn);

        if (hasUnderline) {
          underline = new THREE.Line(ul_geom, line_mtl);
          underline.position.copy(vec);
          underline.scale.x = sc * tw / th;
          underline.updateMatrixWorld();
          underline.onBeforeRender = onBeforeRender;
          conn.add(underline);
        }
      }
      partIdx++;
    }, this);
  }
};

Q3D.VectorLayer.prototype.loadJSONObject = function (jsonObject, scene) {
  Q3D.MapLayer.prototype.loadJSONObject.call(this, jsonObject, scene);
  if (jsonObject.type == "layer") {
    if (jsonObject.data !== undefined) {
      this.features = [];
      this.clearLabels();

      // build labels
      if (this.properties.label !== undefined) {
        // create a label group and a label connector group
        if (this.labelGroup === undefined) {
          this.labelGroup = new Q3D.Group();
          this.labelGroup.userData.layerId = this.id;
          this.labelGroup.visible = this.visible;
          scene.labelGroup.add(this.labelGroup);
        }

        if (this.labelConnectorGroup === undefined) {
          this.labelConnectorGroup = new Q3D.Group();
          this.labelConnectorGroup.userData.layerId = this.id;
          this.labelConnectorGroup.visible = this.visible;
          scene.labelConnectorGroup.add(this.labelConnectorGroup);
        }
      }

      (jsonObject.data.blocks || []).forEach(function (block) {
        if (block.url !== undefined) Q3D.application.loadJSONFile(block.url);
        else {
          this.build(block.features, block.startIndex);
          if (this.properties.label !== undefined) this.buildLabels(block.features);
        }
      }, this);
    }
  }
  else if (jsonObject.type == "block") {
    this.build(jsonObject.features, jsonObject.startIndex);
    if (this.properties.label !== undefined) this.buildLabels(jsonObject.features);
  }
};

Object.defineProperty(Q3D.VectorLayer.prototype, "visible", {
  get: function () {
    return Object.getOwnPropertyDescriptor(Q3D.MapLayer.prototype, "visible").get.call(this);
  },
  set: function (value) {
    if (this.labelGroup) this.labelGroup.visible = value;
    if (this.labelConnectorGroup) this.labelConnectorGroup.visible = value;
    Object.getOwnPropertyDescriptor(Q3D.MapLayer.prototype, "visible").set.call(this, value);
  }
});


/*
Q3D.PointLayer --> Q3D.VectorLayer
*/
Q3D.PointLayer = function () {
  Q3D.VectorLayer.call(this);
  this.type = Q3D.LayerType.Point;
};

Q3D.PointLayer.prototype = Object.create(Q3D.VectorLayer.prototype);
Q3D.PointLayer.prototype.constructor = Q3D.PointLayer;

Q3D.PointLayer.prototype.loadJSONObject = function (jsonObject, scene) {
  if (jsonObject.type == "layer" && jsonObject.properties.objType == "3D Model" && jsonObject.data !== undefined) {
    if (this.models === undefined) {
      var _this = this;

      this.models = new Q3D.Models();
      this.models.addEventListener("modelLoaded", function (event) {
        _this.materials.addFromObject3D(event.model.scene);
        _this.requestRender();
      });
    }
    else {
      this.models.clear();
    }
    this.models.loadJSONObject(jsonObject.data.models);
  }

  Q3D.VectorLayer.prototype.loadJSONObject.call(this, jsonObject, scene);
};

Q3D.PointLayer.prototype.build = function (features, startIndex) {
  var objType = this.properties.objType;
  if (objType == "Point") {
    return this.buildPoints(features, startIndex);
  }
  else if (objType == "Billboard") {
    return this.buildBillboards(features, startIndex);
  }
  else if (objType == "3D Model") {
    return this.buildModels(features, startIndex);
  }

  var unitGeom, transform;
  if (this.cachedGeometryType === objType) {
    unitGeom = this.geometryCache;
    transform = this.transformCache;
  }
  else {
    var gt = this.geomAndTransformFunc(objType);
    unitGeom = gt[0];
    transform = gt[1];
  }

  var f, mtl, pts, i, l, mesh, meshes;
  for (var fidx = 0; fidx < features.length; fidx++) {
    f = features[fidx];
    pts = f.geom.pts;
    mtl = this.materials.mtl(f.mtl);

    meshes = [];
    for (i = 0, l = pts.length; i < l; i++) {
      mesh = new THREE.Mesh(unitGeom, mtl);
      transform(mesh, f.geom, pts[i]);

      mesh.userData.properties = f.prop;

      meshes.push(mesh);
    }
    this.addFeature(fidx + startIndex, f, meshes);
  }

  this.cachedGeometryType = objType;
  this.geometryCache = unitGeom;
  this.transformCache = transform;
};

Q3D.PointLayer.prototype.geomAndTransformFunc = function (objType) {

  var deg2rad = Q3D.deg2rad,
      rx = 90 * deg2rad;

  if (objType == "Sphere") {
    return [
      new THREE.SphereBufferGeometry(1, 32, 32),
      function (mesh, geom, pt) {
        mesh.scale.setScalar(geom.r);
        mesh.position.fromArray(pt);
      }
    ];
  }
  else if (objType == "Box") {
    return [
      new THREE.BoxBufferGeometry(1, 1, 1),
      function (mesh, geom, pt) {
        mesh.scale.set(geom.w, geom.h, geom.d);
        mesh.rotation.x = rx;
        mesh.position.set(pt[0], pt[1], pt[2] + geom.h / 2);
      }
    ];
  }
  else if (objType == "Disk") {
    var sz = this.sceneData.zScale;
    return [
      new THREE.CircleBufferGeometry(1, 32),
      function (mesh, geom, pt) {
        mesh.scale.set(geom.r, geom.r * sz, 1);
        mesh.rotateOnWorldAxis(Q3D.uv.i, -geom.d * deg2rad);
        mesh.rotateOnWorldAxis(Q3D.uv.k, -geom.dd * deg2rad);
        mesh.position.fromArray(pt);
      }
    ];
  }
  else if (objType == "Plane") {
    var sz = this.sceneData.zScale;
    return [
      new THREE.PlaneBufferGeometry(1, 1, 1, 1),
      function (mesh, geom, pt) {
        mesh.scale.set(geom.w, geom.l * sz, 1);
        mesh.rotateOnWorldAxis(Q3D.uv.i, -geom.d * deg2rad);
        mesh.rotateOnWorldAxis(Q3D.uv.k, -geom.dd * deg2rad);
        mesh.position.fromArray(pt);
      }
    ];
  }

  // Cylinder or Cone
  var radiusTop = (objType == "Cylinder") ? 1 : 0;
  return [
    new THREE.CylinderBufferGeometry(radiusTop, 1, 1, 32),
    function (mesh, geom, pt) {
      mesh.scale.set(geom.r, geom.h, geom.r);
      mesh.rotation.x = rx;
      mesh.position.set(pt[0], pt[1], pt[2] + geom.h / 2);
    }
  ];
};

Q3D.PointLayer.prototype.buildPoints = function (features, startIndex) {
  var f, geom, mtl, obj;
  for (var fidx = 0; fidx < features.length; fidx++) {
    f = features[fidx];

    geom = new THREE.BufferGeometry().setAttribute("position", new THREE.Float32BufferAttribute(f.geom.pts, 3));
    mtl = this.materials.mtl(f.mtl);

    obj = new THREE.Points(geom, mtl);
    obj.userData.properties = f.prop;

    this.addFeature(fidx + startIndex, f, [obj]);
  }
};

Q3D.PointLayer.prototype.buildBillboards = function (features, startIndex) {

  features.forEach(function (f, fidx) {

    var material = this.materials.get(f.mtl);

    var sprite, sprites = [];
    for (var i = 0; i < f.geom.pts.length; i++) {
      sprite = new THREE.Sprite(material.mtl);
      sprite.position.fromArray(f.geom.pts[i]);
      sprite.userData.properties = f.prop;

      sprites.push(sprite);
    }

    material.callbackOnLoad(function () {
      var img = material.mtl.map.image;
      for (var i = 0; i < sprites.length; i++) {
        sprites[i].scale.set(f.geom.size,
                             f.geom.size * img.height / img.width,
                             1);
        sprites[i].updateMatrixWorld();
      }
    });

    this.addFeature(fidx + startIndex, f, sprites);
  }, this);
};

Q3D.PointLayer.prototype.buildModels = function (features, startIndex) {
  var q = new THREE.Quaternion(),
      e = new THREE.Euler(),
      deg2rad = Q3D.deg2rad;

  features.forEach(function (f, fidx) {

    var model = this.models.get(f.model);
    if (!model) {
      console.log("3D Model: There is a missing model.");
      return;
    }

    var parents = [];
    var pt, pts = f.geom.pts;
    for (var i = 0; i < pts.length; i++) {
      pt = pts[i];

      var parent = new Q3D.Group();
      parent.position.fromArray(pt);
      parent.scale.set(1, 1, this.sceneData.zScale);

      parent.userData.properties = f.prop;

      parents.push(parent);
    }

    model.callbackOnLoad(function (m) {
      var parent, obj;
      for (var i = 0; i < parents.length; i++) {
        parent = parents[i];

        obj = m.scene.clone();
        obj.scale.setScalar(f.geom.scale);

        if (obj.rotation.x) {
          // reset coordinate system to z-up and specified rotation
          obj.rotation.set(0, 0, 0);
          obj.quaternion.multiply(q.setFromEuler(e.set(f.geom.rotateX * deg2rad,
                                                       f.geom.rotateY * deg2rad,
                                                       f.geom.rotateZ * deg2rad,
                                                       f.geom.rotateO || "XYZ")));
        }
        else {
          // y-up to z-up and specified rotation
          obj.quaternion.multiply(q.setFromEuler(e.set(f.geom.rotateX * deg2rad,
                                                       f.geom.rotateY * deg2rad,
                                                       f.geom.rotateZ * deg2rad,
                                                       f.geom.rotateO || "XYZ")));
          obj.quaternion.multiply(q.setFromEuler(e.set(Math.PI / 2, 0, 0)));
        }
        parent.add(obj);
      }
    });

    this.addFeature(fidx + startIndex, f, parents);
  }, this);
};

Q3D.PointLayer.prototype.buildLabels = function (features) {
  Q3D.VectorLayer.prototype.buildLabels.call(this, features, function (f) { return f.geom.pts; });
};


/*
Q3D.LineLayer --> Q3D.VectorLayer
*/
Q3D.LineLayer = function () {
  Q3D.VectorLayer.call(this);
  this.type = Q3D.LayerType.Line;
};

Q3D.LineLayer.prototype = Object.create(Q3D.VectorLayer.prototype);
Q3D.LineLayer.prototype.constructor = Q3D.LineLayer;

Q3D.LineLayer.prototype.clearObjects = function () {
  Q3D.VectorLayer.prototype.clearObjects.call(this);

  if (this.origMtls) {
    this.origMtls.dispose();
    this.origMtls = undefined;
  }
};

Q3D.LineLayer.prototype.build = function (features, startIndex) {

  if (this._lastObjType !== this.properties.objType) this._createObject = null;

  var createObject = this._createObject || this.createObjFunc(this.properties.objType);

  var f, i, lines, obj, objs;
  for (var fidx = 0; fidx < features.length; fidx++) {
    f = features[fidx];
    lines = f.geom.lines;

    objs = [];
    for (i = 0; i < lines.length; i++) {
      obj = createObject(f, lines[i]);
      obj.userData.properties = f.prop;
      obj.userData.mtl = f.mtl;

      objs.push(obj);
    }
    this.addFeature(fidx + startIndex, f, objs);
  }

  this._lastObjType = this.properties.objType;
  this._createObject = createObject;
};

Q3D.LineLayer.prototype.createObjFunc = function (objType) {
  var materials = this.materials;

  if (objType == "Line") {
    return function (f, vertices) {
      var geom = new THREE.BufferGeometry().setAttribute("position", new THREE.Float32BufferAttribute(vertices, 3));

      var obj = new THREE.Line(geom, materials.mtl(f.mtl));
      if (obj.material instanceof THREE.LineDashedMaterial) obj.computeLineDistances();
      return obj;
    };
  }
  else if (objType == "Thick Line") {
    return function (f, vertices) {
      var line = new MeshLine();
      line.setPoints(vertices);

      return new THREE.Mesh(line, materials.mtl(f.mtl));
    };
  }
  else if (objType == "Pipe" || objType == "Cone") {
    var jointGeom, cylinGeom;
    if (objType == "Pipe") {
      jointGeom = new THREE.SphereBufferGeometry(1, 32, 32);
      cylinGeom = new THREE.CylinderBufferGeometry(1, 1, 1, 32);
    }
    else {
      cylinGeom = new THREE.CylinderBufferGeometry(0, 1, 1, 32);
    }

    var group, mesh, axis = Q3D.uv.j;
    var pt0 = new THREE.Vector3(), pt1 = new THREE.Vector3(), sub = new THREE.Vector3();

    return function (f, points) {
      group = new Q3D.Group();

      pt0.fromArray(points[0]);
      for (var i = 1, l = points.length; i < l; i++) {
        pt1.fromArray(points[i]);

        mesh = new THREE.Mesh(cylinGeom, materials.mtl(f.mtl));
        mesh.scale.set(f.geom.r, pt0.distanceTo(pt1), f.geom.r);
        mesh.position.set((pt0.x + pt1.x) / 2, (pt0.y + pt1.y) / 2, (pt0.z + pt1.z) / 2);
        mesh.quaternion.setFromUnitVectors(axis, sub.subVectors(pt1, pt0).normalize());
        group.add(mesh);

        if (jointGeom && i < l - 1) {
          mesh = new THREE.Mesh(jointGeom, materials.mtl(f.mtl));
          mesh.scale.setScalar(f.geom.r);
          mesh.position.copy(pt1);
          group.add(mesh);
        }

        pt0.copy(pt1);
      }
      return group;
    };
  }
  else if (objType == "Box") {
    // In this method, box corners are exposed near joint when both azimuth and slope of
    // the segments of both sides are different. Also, some unnecessary faces are created.
    var faces = [], vi;
    vi = [[0, 5, 4], [4, 5, 1],   // left turn - top, side, bottom
          [3, 0, 7], [7, 0, 4],
          [6, 3, 2], [2, 3, 7],
          [4, 1, 0], [0, 1, 5],   // right turn - top, side, bottom
          [1, 2, 5], [5, 2, 6],
          [2, 7, 6], [6, 7, 3]];

    for (var j = 0; j < 12; j++) {
      faces.push(new THREE.Face3(vi[j][0], vi[j][1], vi[j][2]));
    }

    return function (f, points) {
      var geometry = new THREE.Geometry();

      var geom, dist, rx, rz, wh4, vb4, vf4;
      var pt0 = new THREE.Vector3(), pt1 = new THREE.Vector3(), sub = new THREE.Vector3(),
          pt = new THREE.Vector3(), ptM = new THREE.Vector3(), scale1 = new THREE.Vector3(1, 1, 1),
          matrix = new THREE.Matrix4(), quat = new THREE.Quaternion();

      pt0.fromArray(points[0]);
      for (var i = 1, l = points.length; i < l; i++) {
        pt1.fromArray(points[i]);
        dist = pt0.distanceTo(pt1);
        sub.subVectors(pt1, pt0);
        rx = Math.atan2(sub.z, Math.sqrt(sub.x * sub.x + sub.y * sub.y));
        rz = Math.atan2(sub.y, sub.x) - Math.PI / 2;
        ptM.set((pt0.x + pt1.x) / 2, (pt0.y + pt1.y) / 2, (pt0.z + pt1.z) / 2);   // midpoint
        quat.setFromEuler(new THREE.Euler(rx, 0, rz, "ZXY"));
        matrix.compose(ptM, quat, scale1);

        // place a box to the segment
        geom = new THREE.BoxGeometry(f.geom.w, dist, f.geom.h);
        geom.applyMatrix(matrix);
        geometry.merge(geom);

        // joint
        // 4 vertices of backward side of current segment
        wh4 = [[-f.geom.w / 2, f.geom.h / 2],
              [f.geom.w / 2, f.geom.h / 2],
              [f.geom.w / 2, -f.geom.h / 2],
              [-f.geom.w / 2, -f.geom.h / 2]];
        vb4 = [];
        for (j = 0; j < 4; j++) {
          pt.set(wh4[j][0], -dist / 2, wh4[j][1]);
          pt.applyMatrix4(matrix);
          vb4.push(pt.clone());
        }

        if (vf4) {
          geom = new THREE.Geometry();
          geom.vertices = vf4.concat(vb4);
          geom.faces = faces;
          geometry.merge(geom);
        }

        // 4 vertices of forward side
        vf4 = [];
        for (j = 0; j < 4; j++) {
          pt.set(wh4[j][0], dist / 2, wh4[j][1]);
          pt.applyMatrix4(matrix);
          vf4.push(new THREE.Vector3(pt.x, pt.y, pt.z));
        }

        pt0.copy(pt1);
      }

      geometry.faceVertexUvs = [[]];
      geometry.mergeVertices();
      geometry.computeFaceNormals();
      return new THREE.Mesh(geometry, materials.mtl(f.mtl));
    };
  }
  else if (objType == "Wall") {
    return function (f, vertices) {
      var bzFunc = function (x, y) { return f.geom.bh; };
      return new THREE.Mesh(Q3D.Utils.createWallGeometry(vertices, bzFunc),
                            materials.mtl(f.mtl));
    };
  }
};

Q3D.LineLayer.prototype.buildLabels = function (features) {
  // Line layer doesn't support label
  // Q3D.VectorLayer.prototype.buildLabels.call(this, features);
};

// prepare for growing line animation
Q3D.LineLayer.prototype.prepareAnimation = function (sequential) {

  if (this.origMtls !== undefined) return;

  function computeLineDistances(obj) {
    if (!obj.material.isLineDashedMaterial) return;

    obj.computeLineDistances();

    var dists = obj.geometry.attributes.lineDistance.array;
    obj.lineLength = dists[dists.length - 1];

    for (var i = 0; i < dists.length; i++) {
      dists[i] /= obj.lineLength;
    }
  }

  this.origMtls = new Q3D.Materials();
  this.origMtls.array = this.materials.array;

  this.materials.array = [];

  if (sequential) {
    var f, m, mtl, j;
    for (var i = 0; i < this.features.length; i++) {
      f = this.features[i];
      m = f.objs[0].material;

      if (m.isMeshLineMaterial) {
        mtl = new MeshLineMaterial();
        mtl.color = m.color;
        mtl.opacity = m.opacity;
        mtl.lineWidth = m.lineWidth;
        mtl.dashArray = 2;
        mtl.transparent = true;
      }
      else {
        if (m.isLineDashedMaterial) {
          mtl = m.clone();
        }
        else {
          mtl = new THREE.LineDashedMaterial({color: m.color, opacity: m.opacity});
        }
        mtl.gapSize = 1;
      }

      for (j = 0; j < f.objs.length; j++) {
        f.objs[j].material = mtl;
        computeLineDistances(f.objs[j]);
      }
      this.materials.add(mtl);
    }
  }
  else {
    var mtl, mtls = this.origMtls.array;

    for (var i = 0; i < mtls.length; i++) {
      mtl = mtls[i].mtl;

      if (mtl.isLineDashedMaterial) {
        mtl.gapSize = 1;
      }
      else if (mtl.isMeshLineMaterial) {
        mtl.dashArray = 2;
        mtl.transparent = true;
      }
      else if (mtl.isLineBasicMaterial) {
        mtl = new THREE.LineDashedMaterial({color: mtl.color, opacity: mtl.opacity});
      }

      this.materials.add(mtl);
    }

    var _this = this;
    this.objectGroup.traverse(function (obj) {

      if (obj.userData.mtl !== undefined) {
        obj.material = _this.materials.mtl(obj.userData.mtl);
        computeLineDistances(obj);
      }

    });
  }
};

// length: number [0 - 1]
Q3D.LineLayer.prototype.setLineLength = function (length, featureIdx) {

  if (this.origMtls === undefined) return;

  var mtl;
  if (featureIdx === undefined) {
    var mtls = this.materials.array;
    for (var i = 0; i < mtls.length; i++) {
      mtl = mtls[i].mtl;
      if (mtl.isLineDashedMaterial) {
        mtl.dashSize = length;
      }
      else if (mtl.isMeshLineMaterial) {
        mtl.uniforms.dashOffset.value = -length;
      }
    }
  }
  else {
    mtl = this.features[featureIdx].objs[0].material;
    if (mtl.isLineDashedMaterial) {
      mtl.dashSize = length;
    }
    else if (mtl.isMeshLineMaterial) {
      mtl.uniforms.dashOffset.value = -length;
    }
  }
};


/*
Q3D.PolygonLayer --> Q3D.VectorLayer
*/
Q3D.PolygonLayer = function () {
  Q3D.VectorLayer.call(this);
  this.type = Q3D.LayerType.Polygon;

  // for overlay
  this.borderVisible = true;
  this.sideVisible = true;
};

Q3D.PolygonLayer.prototype = Object.create(Q3D.VectorLayer.prototype);
Q3D.PolygonLayer.prototype.constructor = Q3D.PolygonLayer;

Q3D.PolygonLayer.prototype.loadJSONObject = function (jsonObject, scene) {
  Q3D.VectorLayer.prototype.loadJSONObject.call(this, jsonObject, scene);
};

Q3D.PolygonLayer.prototype.build = function (features, startIndex) {

  if (this.properties.objType !== this._lastObjType) this._createObject = null;

  var createObject = this._createObject || this.createObjFunc(this.properties.objType);

  var f, obj;
  for (var fidx = 0; fidx < features.length; fidx++) {
    f = features[fidx];
    obj = createObject(f);
    obj.userData.properties = f.prop;

    this.addFeature(fidx + startIndex, f, [obj]);
  }

  this._lastObjType = this.properties.objType;
  this._createObject = createObject;
};

Q3D.PolygonLayer.prototype.createObjFunc = function (objType) {

  var materials = this.materials;

  if (objType == "Polygon") {
    return function (f) {
      var geom = new THREE.BufferGeometry();
      geom.setAttribute("position", new THREE.Float32BufferAttribute(f.geom.triangles.v, 3));
      geom.setIndex(f.geom.triangles.f);
      geom = new THREE.Geometry().fromBufferGeometry(geom); // Flat shading doesn't work with combination of
                                                            // BufferGeometry and Lambert/Toon material.
      return new THREE.Mesh(geom, materials.mtl(f.mtl));
    };
  }
  else if (objType == "Extruded") {
    var createSubObject = function (f, polygon, z) {
      var i, l, j, m;

      var shape = new THREE.Shape(Q3D.Utils.arrayToVec2Array(polygon[0]));
      for (i = 1, l = polygon.length; i < l; i++) {
        shape.holes.push(new THREE.Path(Q3D.Utils.arrayToVec2Array(polygon[i])));
      }

      // extruded geometry
      var geom = new THREE.ExtrudeBufferGeometry(shape, {bevelEnabled: false, depth: f.geom.h});
      var mesh = new THREE.Mesh(geom, materials.mtl(f.mtl.face));
      mesh.position.z = z;

      if (f.mtl.edge !== undefined) {
        // edge
        var edge, bnd, v,
            h = f.geom.h,
            mtl = materials.mtl(f.mtl.edge);

        for (i = 0, l = polygon.length; i < l; i++) {
          bnd = polygon[i];

          v = [];
          for (j = 0, m = bnd.length; j < m; j++) {
            v.push(bnd[j][0], bnd[j][1], 0);
          }

          geom = new THREE.BufferGeometry().setAttribute("position", new THREE.Float32BufferAttribute(v, 3));

          edge = new THREE.Line(geom, mtl);
          mesh.add(edge);

          edge = new THREE.Line(geom, mtl);
          edge.position.z = h;
          mesh.add(edge);

          // vertical lines
          for (j = 0, m = bnd.length - 1; j < m; j++) {
            v = [bnd[j][0], bnd[j][1], 0,
                 bnd[j][0], bnd[j][1], h];

            geom = new THREE.BufferGeometry().setAttribute("position", new THREE.Float32BufferAttribute(v, 3));

            edge = new THREE.Line(geom, mtl);
            mesh.add(edge);
          }
        }
      }
      return mesh;
    };

    var polygons, centroids;

    return function (f) {
      polygons = f.geom.polygons;
      centroids = f.geom.centroids;

      if (polygons.length == 1) return createSubObject(f, polygons[0], centroids[0][2]);

      var group = new THREE.Group();
      for (var i = 0, l = polygons.length; i < l; i++) {
        group.add(createSubObject(f, polygons[i], centroids[i][2]));
      }
      return group;
    };
  }
  else if (objType == "Overlay") {

    var _this = this;

    return function (f) {

      var geom = new THREE.BufferGeometry();
      geom.setIndex(f.geom.triangles.f);
      geom.setAttribute("position", new THREE.Float32BufferAttribute(f.geom.triangles.v, 3));
      geom.computeVertexNormals();

      var mesh = new THREE.Mesh(geom, materials.mtl(f.mtl.face));

      var rotation = _this.sceneData.baseExtent.rotation;
      if (rotation) {
        // rotate around center of base extent
        mesh.position.copy(_this.sceneData.pivot).negate();
        mesh.position.applyAxisAngle(Q3D.uv.k, rotation * Q3D.deg2rad);
        mesh.position.add(_this.sceneData.pivot);
        mesh.rotateOnAxis(Q3D.uv.k, rotation * Q3D.deg2rad);
      }

      // borders
      if (f.geom.brdr !== undefined) {
        var bnds, i, l, j, m;
        for (i = 0, l = f.geom.brdr.length; i < l; i++) {
          bnds = f.geom.brdr[i];
          for (j = 0, m = bnds.length; j < m; j++) {
            geom = new THREE.BufferGeometry().setAttribute("position", new THREE.Float32BufferAttribute(bnds[j], 3));

            mesh.add(new THREE.Line(geom, materials.mtl(f.mtl.brdr)));
          }
        }
      }
      return mesh;
    };
  }
};

Q3D.PolygonLayer.prototype.buildLabels = function (features) {
  Q3D.VectorLayer.prototype.buildLabels.call(this, features, function (f) { return f.geom.centroids; });
};

Q3D.PolygonLayer.prototype.setBorderVisible = function (visible) {
  if (this.properties.objType != "Overlay") return;

  this.objectGroup.children.forEach(function (parent) {
    for (var i = 0, l = parent.children.length; i < l; i++) {
      var obj = parent.children[i];
      if (obj instanceof THREE.Line) obj.visible = visible;
    }
  });
  this.borderVisible = visible;
};

Q3D.PolygonLayer.prototype.setSideVisible = function (visible) {
  if (this.properties.objType != "Overlay") return;

  this.objectGroup.children.forEach(function (parent) {
    for (var i = 0, l = parent.children.length; i < l; i++) {
      var obj = parent.children[i];
      if (obj instanceof THREE.Mesh) obj.visible = visible;
    }
  });
  this.sideVisible = visible;
};


/*
Q3D.Model
*/
Q3D.Model = function () {
  this.loaded = false;
};

Q3D.Model.prototype = {

  constructor: Q3D.Model,

  // callback is called when model has been completely loaded
  load: function (url, callback) {
    var _this = this;
    Q3D.application.loadModelFile(url, function (model) {
      _this.model = model;
      _this._loadCompleted(callback);
    });
  },

  loadData: function (data, ext, resourcePath, callback) {
    var _this = this;
    Q3D.application.loadModelData(data, ext, resourcePath, function (model) {
      _this.model = model;
      _this._loadCompleted(callback);
    });
  },

  loadJSONObject: function (jsonObject, callback) {
    if (jsonObject.url !== undefined) {
      this.load(jsonObject.url, callback);
    }
    else {
      var b = atob(jsonObject.base64),
          len = b.length,
          bytes = new Uint8Array(len);

      for (var i = 0; i < len; i++) {
        bytes[i] = b.charCodeAt(i);
      }

      this.loadData(bytes.buffer, jsonObject.ext, jsonObject.resourcePath, callback);
    }
  },

  _loadCompleted: function (anotherCallback) {
    this.loaded = true;

    if (this._callbacks !== undefined) {
      for (var i = 0; i < this._callbacks.length; i++) {
        this._callbacks[i](this.model);
      }
      this._callbacks = [];
    }

    if (anotherCallback) anotherCallback(this.model);
  },

  callbackOnLoad: function (callback) {
    if (this.loaded) return callback(this.model);

    if (this._callbacks === undefined) this._callbacks = [];
    this._callbacks.push(callback);
  }

};


/*
Q3D.Models
*/
Q3D.Models = function () {
  this.models = [];
  this.cache = {};
};

Q3D.Models.prototype = Object.create(THREE.EventDispatcher.prototype);
Q3D.Models.prototype.constructor = Q3D.Models;

Q3D.Models.prototype.loadJSONObject = function (jsonObject) {
  var _this = this;
  var callback = function (model) {
    _this.dispatchEvent({type: "modelLoaded", model: model});
  };

  var model, url;
  for (var i = 0, l = jsonObject.length; i < l; i++) {

    url = jsonObject[i].url;
    if (url !== undefined && this.cache[url] !== undefined) {
      model = this.cache[url];
    }
    else {
      model = new Q3D.Model();
      model.loadJSONObject(jsonObject[i], callback);

      if (url !== undefined) this.cache[url] = model;
    }
    this.models.push(model);
  }
};

Q3D.Models.prototype.get = function (index) {
  return this.models[index];
};

Q3D.Models.prototype.clear = function () {
  this.models = [];
};


// Q3D.Utils - Utilities
Q3D.Utils = {};

// Put a stick to given position (for debug)
Q3D.Utils.putStick = function (x, y, zFunc, h) {
  if (Q3D.Utils._stick_mat === undefined) Q3D.Utils._stick_mat = new THREE.LineBasicMaterial({color: 0xff0000});
  if (h === undefined) h = 0.2;
  if (zFunc === undefined) {
    zFunc = function (x, y) { return Q3D.application.scene.mapLayers[0].getZ(x, y); };
  }
  var z = zFunc(x, y);
  var geom = new THREE.Geometry();
  geom.vertices.push(new THREE.Vector3(x, y, z + h), new THREE.Vector3(x, y, z));
  var stick = new THREE.Line(geom, Q3D.Utils._stick_mat);
  Q3D.application.scene.add(stick);
};

// convert latitude and longitude in degrees to the following format
// Ndd°mm′ss.ss″, Eddd°mm′ss.ss″
Q3D.Utils.convertToDMS = function (lat, lon) {
  function toDMS(degrees) {
    var deg = Math.floor(degrees),
        m = (degrees - deg) * 60,
        min = Math.floor(m),
        sec = (m - min) * 60;
    return deg + "°" + ("0" + min).slice(-2) + "′" + ((sec < 10) ? "0" : "") + sec.toFixed(2) + "″";
  }

  return ((lat < 0) ? "S" : "N") + toDMS(Math.abs(lat)) + ", " +
         ((lon < 0) ? "W" : "E") + toDMS(Math.abs(lon));
};

Q3D.Utils.createWallGeometry = function (vert, bzFunc, buffer_geom) {
  var geom = new THREE.Geometry();
  for (var i = 0, l = vert.length; i < l; i += 3) {
    geom.vertices.push(
      new THREE.Vector3(vert[i], vert[i + 1], vert[i + 2]),
      new THREE.Vector3(vert[i], vert[i + 1], bzFunc(vert[i], vert[i + 1]))
    );
  }

  for (var i = 1, i2 = 1, l = vert.length / 3; i < l; i++, i2 += 2) {
    geom.faces.push(
      new THREE.Face3(i2 - 1, i2, i2 + 1),
      new THREE.Face3(i2 + 1, i2, i2 + 2)
    );
  }

  geom.computeFaceNormals();

  if (buffer_geom) {
    return new THREE.BufferGeometry().fromGeometry(geom);
  }
  return geom;
};

Q3D.Utils.arrayToVec2Array = function (points) {
  var pt, pts = [];
  for (var i = 0, l = points.length; i < l; i++) {
    pt = points[i];
    pts.push(new THREE.Vector2(pt[0], pt[1]));
  }
  return pts;
};

Q3D.Utils.flatArrayToVec2Array = function (vertices, itemSize) {
  itemSize = itemSize || 2;
  var pts = [];
  for (var i = 0, l = vertices.length; i < l; i += itemSize) {
    pts.push(new THREE.Vector2(vertices[i], vertices[i + 1]));
  }
  return pts;
};

Q3D.Utils.setGeometryUVs = function (geom, base_width, base_height) {
  var face, v, uvs = [];
  for (var i = 0, l = geom.vertices.length; i < l; i++) {
    v = geom.vertices[i];
    uvs.push(new THREE.Vector2(v.x / base_width + 0.5, v.y / base_height + 0.5));
  }

  geom.faceVertexUvs[0] = [];
  for (var i = 0, l = geom.faces.length; i < l; i++) {
    face = geom.faces[i];
    geom.faceVertexUvs[0].push([uvs[face.a], uvs[face.b], uvs[face.c]]);
  }
};


// Q3D.Tweens
Q3D.Tweens = {};

Q3D.Tweens.cameraMotion = {

  type: Q3D.KeyframeType.CameraMotion,

  curveFactor: 0,

  init: function (group) {

    var app = Q3D.application,
        keyframes = group.keyframes,
        prop_list = [];

    var c = this.curveFactor, p, p0, phi, theta, dist, dist_list = [];
    var vec3 = new THREE.Vector3(),
        o = app.scene.userData.origin;
    for (var i = 0; i < keyframes.length; i++) {
      p = keyframes[i].camera;
      vec3.set(p.x - p.fx, p.y - p.fy, p.z - p.fz);
      dist = vec3.length();
      theta = Math.acos(vec3.z / dist);
      phi = Math.atan2(vec3.y, vec3.x);
      p.phi = phi;
      prop_list.push({p: i, fx: p.fx - o.x, fy: p.fy - o.y, fz: p.fz - o.z, d: dist, theta: theta});  // map to 3D world

      if (i > 0) {
        dist_list.push(Math.sqrt((p.x - p0.x) * (p.x - p0.x) + (p.y - p0.y) * (p.y - p0.y)));
      }
      p0 = p;
    }
    group.prop_list = prop_list;

    var phi0, phi1, dz;
    group.onUpdate = function (obj, elapsed, is_first) {

      p = obj.p - group.currentIndex;
      phi0 = keyframes[group.currentIndex].camera.phi;
      phi1 = (is_first) ? phi0 : keyframes[group.currentIndex + 1].camera.phi;

      if (Math.abs(phi1 - phi0) > Math.PI) {  // take the shortest orbiting path
        phi1 += Math.PI * ((phi1 > phi0) ? -2 : 2);
      }

      phi = phi0 * (1 - p) + phi1 * p;

      vec3.set(Math.cos(phi) * Math.sin(obj.theta),
                Math.sin(phi) * Math.sin(obj.theta),
                Math.cos(obj.theta)).setLength(obj.d);

      dz = (c) ? (1 - Math.pow(2 * p - 1, 2)) * dist_list[group.currentIndex] * c : 0;

      app.camera.position.set(obj.fx + vec3.x, obj.fy + vec3.y, obj.fz + vec3.z + dz);
      app.camera.lookAt(obj.fx, obj.fy, obj.fz);
      app.controls.target.set(obj.fx, obj.fy, obj.fz);
    };

    // initial position
    group.onUpdate(group.prop_list[0], 1, true);
  }

};

Q3D.Tweens.opacity = {

  type: Q3D.KeyframeType.Opacity,

  init: function (group, layer) {

    var keyframes = group.keyframes;

    for (var i = 0; i < keyframes.length; i++) {
      group.prop_list.push({opacity: keyframes[i].opacity});
    }

    group.onUpdate = function (obj, elapsed) {
      layer.opacity = obj.opacity;
    };

    // initial opacity
    group.onUpdate(group.prop_list[0]);
  }

};

Q3D.Tweens.texture = {

  type: Q3D.KeyframeType.Texture,

  init: function (group, layer) {

    var keyframes = group.keyframes;

    var idx_from, from, to, effect;

    group.onStart = function () {
      idx_from = group.currentIndex;
      effect = keyframes[idx_from].effect;
      from = keyframes[idx_from].mtlIndex;
      to = keyframes[idx_from + 1].mtlIndex;

      layer.prepareTexAnimation(from, to);
      layer.setTextureAt(null, effect);
    };

    group.onUpdate = function (obj, elapsed) {
      layer.setTextureAt(obj.p - group.currentIndex, effect);
    };

    for (var i = 0; i < keyframes.length; i++) {
      group.prop_list.push({p: i});
    }
  }
};

Q3D.Tweens.lineGrowing = {

  type: Q3D.KeyframeType.GrowingLine,

  init: function (group, layer) {
    if (group._keyframes === undefined) group._keyframes = group.keyframes;

    var effectItem = group._keyframes[0];
    if (effectItem.sequential) {
      group.keyframes = [];

      for (var i = 0; i < layer.features.length; i++) {
        group.keyframes.push(layer.features[i].anim);
        group.prop_list.push({p: i});
      }
      group.keyframes.push({});
      group.prop_list.push({p: i});

      group.onUpdate = function (obj, elapsed) {
        layer.setLineLength(obj.p - group.currentIndex, group.currentIndex);
      };
    }
    else {
      group.keyframes = [effectItem, {}];
      group.prop_list = [{p: 0}, {p: 1}];

      group.onUpdate = function (obj, elapsed) {
        layer.setLineLength(obj.p);
      };
    }

    layer.prepareAnimation(effectItem.sequential);
    layer.setLineLength(0);
  }

};


// https://stackoverflow.com/a/7838871
CanvasRenderingContext2D.prototype.roundRect = function (x, y, w, h, r) {
  if (w < 2 * r) r = w / 2;
  if (h < 2 * r) r = h / 2;
  this.beginPath();
  this.moveTo(x + r, y);
  this.arcTo(x + w, y, x + w, y + h, r);
  this.arcTo(x + w, y + h, x, y + h, r);
  this.arcTo(x, y + h, x, y, r);
  this.arcTo(x, y, x + w, y, r);
  this.closePath();
  return this;
};
