// src/three/renderer/controls/EnvironmentControls.js
import {
  Matrix4 as Matrix42,
  Quaternion,
  Vector2 as Vector23,
  Vector3 as Vector32,
  Raycaster,
  Plane,
  EventDispatcher,
  MathUtils,
  Ray as Ray2
} from "three";

// src/three/renderer/controls/PivotPointMesh.js
import { Mesh, PlaneGeometry, ShaderMaterial, Vector2 } from "three";
var PivotPointMesh = class extends Mesh {
  constructor() {
    super(new PlaneGeometry(0, 0), new PivotMaterial());
    this.renderOrder = Infinity;
  }
  onBeforeRender(renderer) {
    const uniforms = this.material.uniforms;
    renderer.getSize(uniforms.resolution.value);
  }
  updateMatrixWorld() {
    this.matrixWorld.makeTranslation(this.position);
  }
  dispose() {
    this.geometry.dispose();
    this.material.dispose();
  }
};
var PivotMaterial = class extends ShaderMaterial {
  constructor() {
    super({
      depthWrite: false,
      depthTest: false,
      transparent: true,
      uniforms: {
        resolution: { value: new Vector2() },
        size: { value: 15 },
        thickness: { value: 2 },
        opacity: { value: 1 }
      },
      vertexShader: (
        /* glsl */
        `

				uniform float size;
				uniform float thickness;
				uniform vec2 resolution;
				varying vec2 vUv;

				void main() {

					vUv = uv;

					float aspect = resolution.x / resolution.y;
					vec2 offset = uv * 2.0 - vec2( 1.0 );
					offset.y *= aspect;

					vec4 screenPoint = projectionMatrix * modelViewMatrix * vec4( position, 1.0 );
					screenPoint.xy += offset * ( size + thickness ) * screenPoint.w / resolution.x;

					gl_Position = screenPoint;

				}
			`
      ),
      fragmentShader: (
        /* glsl */
        `

				uniform float size;
				uniform float thickness;
				uniform float opacity;

				varying vec2 vUv;
				void main() {

					float ht = 0.5 * thickness;
					float planeDim = size + thickness;
					float offset = ( planeDim - ht - 2.0 ) / planeDim;
					float texelThickness = ht / planeDim;

					vec2 vec = vUv * 2.0 - vec2( 1.0 );
					float dist = abs( length( vec ) - offset );
					float fw = fwidth( dist ) * 0.5;
					float a = smoothstep( texelThickness - fw, texelThickness + fw, dist );

					gl_FragColor = vec4( 1, 1, 1, opacity * ( 1.0 - a ) );

				}
			`
      )
    });
  }
};

// src/three/renderer/controls/PointerTracker.js
import { Vector2 as Vector22 } from "three";
var _vec = /* @__PURE__ */ new Vector22();
var _vec2 = /* @__PURE__ */ new Vector22();
var PointerTracker = class {
  constructor() {
    this.domElement = null;
    this.buttons = 0;
    this.pointerType = null;
    this.pointerOrder = [];
    this.previousPositions = {};
    this.pointerPositions = {};
    this.startPositions = {};
    this.pointerSetThisFrame = {};
    this.hoverPosition = new Vector22();
    this.hoverSet = false;
  }
  reset() {
    this.buttons = 0;
    this.pointerType = null;
    this.pointerOrder = [];
    this.previousPositions = {};
    this.pointerPositions = {};
    this.startPositions = {};
    this.pointerSetThisFrame = {};
    this.hoverPosition = new Vector22();
    this.hoverSet = false;
  }
  // The pointers can be set multiple times per frame so track whether the pointer has
  // been set this frame or not so we don't overwrite the previous position and lose information
  // about pointer movement
  updateFrame() {
    const { previousPositions, pointerPositions } = this;
    for (const id in pointerPositions) {
      previousPositions[id].copy(pointerPositions[id]);
    }
  }
  setHoverEvent(e) {
    if (e.pointerType === "mouse" || e.type === "wheel") {
      this.getAdjustedPointer(e, this.hoverPosition);
      this.hoverSet = true;
    }
  }
  getLatestPoint(target) {
    if (this.pointerType !== null) {
      this.getCenterPoint(target);
      return target;
    } else if (this.hoverSet) {
      target.copy(this.hoverPosition);
      return target;
    } else {
      return null;
    }
  }
  // get the pointer position in the coordinate system of the target element
  getAdjustedPointer(e, target) {
    const domRef = this.domElement ? this.domElement : e.target;
    const rect = domRef.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    target.set(x, y);
  }
  addPointer(e) {
    const id = e.pointerId;
    const position = new Vector22();
    this.getAdjustedPointer(e, position);
    this.pointerOrder.push(id);
    this.pointerPositions[id] = position;
    this.previousPositions[id] = position.clone();
    this.startPositions[id] = position.clone();
    if (this.getPointerCount() === 1) {
      this.pointerType = e.pointerType;
      this.buttons = e.buttons;
    }
  }
  updatePointer(e) {
    const id = e.pointerId;
    if (!(id in this.pointerPositions)) {
      return false;
    }
    this.getAdjustedPointer(e, this.pointerPositions[id]);
    return true;
  }
  deletePointer(e) {
    const id = e.pointerId;
    const pointerOrder = this.pointerOrder;
    pointerOrder.splice(pointerOrder.indexOf(id), 1);
    delete this.pointerPositions[id];
    delete this.previousPositions[id];
    delete this.startPositions[id];
    if (this.getPointerCount() === 0) {
      this.buttons = 0;
      this.pointerType = null;
    }
  }
  getPointerCount() {
    return this.pointerOrder.length;
  }
  getCenterPoint(target, pointerPositions = this.pointerPositions) {
    const pointerOrder = this.pointerOrder;
    if (this.getPointerCount() === 1 || this.getPointerType() === "mouse") {
      const id = pointerOrder[0];
      target.copy(pointerPositions[id]);
      return target;
    } else if (this.getPointerCount() === 2) {
      const id0 = this.pointerOrder[0];
      const id1 = this.pointerOrder[1];
      const p0 = pointerPositions[id0];
      const p1 = pointerPositions[id1];
      target.addVectors(p0, p1).multiplyScalar(0.5);
      return target;
    }
    return null;
  }
  getPreviousCenterPoint(target) {
    return this.getCenterPoint(target, this.previousPositions);
  }
  getStartCenterPoint(target) {
    return this.getCenterPoint(target, this.startPositions);
  }
  getMoveDistance() {
    this.getCenterPoint(_vec);
    this.getPreviousCenterPoint(_vec2);
    return _vec.sub(_vec2).length();
  }
  getTouchPointerDistance(pointerPositions = this.pointerPositions) {
    if (this.getPointerCount() <= 1 || this.getPointerType() === "mouse") {
      return 0;
    }
    const { pointerOrder } = this;
    const id0 = pointerOrder[0];
    const id1 = pointerOrder[1];
    const p0 = pointerPositions[id0];
    const p1 = pointerPositions[id1];
    return p0.distanceTo(p1);
  }
  getPreviousTouchPointerDistance() {
    return this.getTouchPointerDistance(this.previousPositions);
  }
  getStartTouchPointerDistance() {
    return this.getTouchPointerDistance(this.startPositions);
  }
  getPointerType() {
    return this.pointerType;
  }
  isPointerTouch() {
    return this.getPointerType() === "touch";
  }
  getPointerButtons() {
    return this.buttons;
  }
  isLeftClicked() {
    return Boolean(this.buttons & 1);
  }
  isRightClicked() {
    return Boolean(this.buttons & 2);
  }
};

// src/three/renderer/controls/utils.js
import { Matrix4, Ray, Vector3 } from "three";
var _matrix = /* @__PURE__ */ new Matrix4();
function makeRotateAroundPoint(point, quat, target) {
  target.makeTranslation(-point.x, -point.y, -point.z);
  _matrix.makeRotationFromQuaternion(quat);
  target.premultiply(_matrix);
  _matrix.makeTranslation(point.x, point.y, point.z);
  target.premultiply(_matrix);
  return target;
}
function adjustedPointerToCoords(pointer, element, target) {
  target.x = pointer.x / element.clientWidth * 2 - 1;
  target.y = -(pointer.y / element.clientHeight) * 2 + 1;
  if (target.isVector3) {
    target.z = 0;
  }
}
function setRaycasterFromCamera(raycaster, coords, camera) {
  const ray = raycaster instanceof Ray ? raycaster : raycaster.ray;
  const { origin, direction } = ray;
  origin.set(coords.x, coords.y, -1).unproject(camera);
  direction.set(coords.x, coords.y, 1).unproject(camera).sub(origin);
  if (!raycaster.isRay) {
    raycaster.near = 0;
    raycaster.far = direction.length();
    raycaster.camera = camera;
  }
  direction.normalize();
}

// src/three/renderer/controls/EnvironmentControls.js
var NONE = 0;
var DRAG = 1;
var ROTATE = 2;
var ZOOM = 3;
var WAITING = 4;
var FREE_ROTATE = 5;
var DRAG_PLANE_THRESHOLD = 0.05;
var DRAG_UP_THRESHOLD = 0.025;
var _rotMatrix = /* @__PURE__ */ new Matrix42();
var _invMatrix = /* @__PURE__ */ new Matrix42();
var _delta = /* @__PURE__ */ new Vector32();
var _vec3 = /* @__PURE__ */ new Vector32();
var _pos = /* @__PURE__ */ new Vector32();
var _center = /* @__PURE__ */ new Vector32();
var _forward = /* @__PURE__ */ new Vector32();
var _right = /* @__PURE__ */ new Vector32();
var _targetRight = /* @__PURE__ */ new Vector32();
var _rotationAxis = /* @__PURE__ */ new Vector32();
var _quaternion = /* @__PURE__ */ new Quaternion();
var _plane = /* @__PURE__ */ new Plane();
var _localUp = /* @__PURE__ */ new Vector32();
var _mouseBefore = /* @__PURE__ */ new Vector32();
var _mouseAfter = /* @__PURE__ */ new Vector32();
var _identityQuat = /* @__PURE__ */ new Quaternion();
var _ray = /* @__PURE__ */ new Ray2();
var _flightDir = /* @__PURE__ */ new Vector32();
var _zoomPointPointer = /* @__PURE__ */ new Vector23();
var _pointer = /* @__PURE__ */ new Vector23();
var _prevPointer = /* @__PURE__ */ new Vector23();
var _deltaPointer = /* @__PURE__ */ new Vector23();
var _centerPoint = /* @__PURE__ */ new Vector23();
var _startCenterPoint = /* @__PURE__ */ new Vector23();
var _changeEvent = { type: "change" };
var _startEvent = { type: "start" };
var _endEvent = { type: "end" };
var DOUBLE_TAP_INTERVAL = 300;
var DOUBLE_TAP_DISTANCE = 30;
var TAP_MOVE_DISTANCE = 5;
var ZOOM_DELTA_SCALAR = 25e-4;
var EnvironmentControls = class extends EventDispatcher {
  /**
   * Whether the controls are active. When set to false, all input is ignored
   * and inertia is cleared.
   * @type {boolean}
   * @default true
   */
  get enabled() {
    return this._enabled;
  }
  set enabled(v) {
    if (v !== this.enabled) {
      this._enabled = v;
      this.resetState();
      this.pointerTracker.reset();
      if (!this.enabled) {
        this.dragInertia.set(0, 0, 0);
        this.rotationInertia.set(0, 0);
      }
    }
  }
  constructor(scene = null, camera = null, domElement = null) {
    super();
    this.isEnvironmentControls = true;
    this.domElement = null;
    this.camera = null;
    this.scene = null;
    this.tilesRenderer = null;
    this._enabled = true;
    this.cameraRadius = 5;
    this.rotationSpeed = 1;
    this.minAltitude = 0;
    this.maxAltitude = 0.45 * Math.PI;
    this.minDistance = 10;
    this.maxDistance = Infinity;
    this.minZoom = 0;
    this.maxZoom = Infinity;
    this.zoomSpeed = 1;
    this.adjustHeight = true;
    this.enableDamping = false;
    this.dampingFactor = 0.15;
    this.enableDoubleTapZoom = true;
    this.doubleTapZoomScale = 2;
    this.doubleTapZoomDuration = 0.25;
    this.fallbackPlane = new Plane(new Vector32(0, 1, 0), 0);
    this.useFallbackPlane = true;
    this.enableFlight = false;
    this.flightSpeed = 10;
    this.flightSpeedMultiplier = 4;
    this.scaleZoomOrientationAtEdges = false;
    this.autoAdjustCameraRotation = true;
    this.state = NONE;
    this.pointerTracker = new PointerTracker();
    this.needsUpdate = false;
    this.actionHeightOffset = 0;
    this.pivotPoint = new Vector32();
    this.zoomDirectionSet = false;
    this.zoomPointSet = false;
    this.zoomDirection = new Vector32();
    this.zoomPoint = new Vector32();
    this.zoomDelta = 0;
    this.rotationInertiaPivot = new Vector32();
    this.rotationInertia = new Vector23();
    this.dragInertia = new Vector32();
    this.inertiaTargetDistance = Infinity;
    this.inertiaStableFrames = 0;
    this.pivotMesh = new PivotPointMesh();
    this.pivotMesh.raycast = () => {
    };
    this.pivotMesh.scale.setScalar(0.25);
    this.raycaster = new Raycaster();
    this.raycaster.firstHitOnly = true;
    this.up = new Vector32(0, 1, 0);
    this._lastTime = performance.now();
    this._keysDown = /* @__PURE__ */ new Set();
    this._detachCallback = null;
    this._upInitialized = false;
    this._lastUsedState = NONE;
    this._zoomPointWasSet = false;
    this._doubleTapZoomActive = false;
    this._doubleTapZoomElapsed = 0;
    this._doubleTapPoint = new Vector23();
    this._lastTapTime = -Infinity;
    this._lastTapPoint = new Vector23();
    this._tilesOnChangeCallback = () => this.zoomPointSet = false;
    if (domElement) this.attach(domElement);
    if (camera) this.setCamera(camera);
    if (scene) this.setScene(scene);
  }
  _getDeltaTime() {
    const curr = performance.now();
    const delta = curr - this._lastTime;
    this._lastTime = curr;
    return delta * 1e-3;
  }
  /**
   * Sets the scene to raycast against for surface-based interaction.
   * @param {Object3D} scene
   */
  setScene(scene) {
    this.scene = scene;
  }
  /**
   * Sets the camera to control.
   * @param {Camera} camera
   */
  setCamera(camera) {
    this.camera = camera;
    this._upInitialized = false;
    this.zoomDirectionSet = false;
    this.zoomPointSet = false;
    this.needsUpdate = true;
    this.raycaster.camera = camera;
    this.resetState();
  }
  /**
   * Attaches the controls to a DOM element, registering all pointer and keyboard event listeners.
   * @param {HTMLElement} domElement
   */
  attach(domElement) {
    if (this.domElement) {
      throw new Error("EnvironmentControls: Controls already attached to element");
    }
    this.domElement = domElement;
    this.pointerTracker.domElement = domElement;
    domElement.style.touchAction = "none";
    if (!domElement.hasAttribute("tabindex")) {
      domElement.tabIndex = -1;
    }
    const contextMenuCallback = (e) => {
      if (!this.enabled) {
        return;
      }
      e.preventDefault();
    };
    const pointerdownCallback = (e) => {
      const {
        camera,
        raycaster,
        domElement: domElement2,
        up,
        pivotMesh,
        pointerTracker,
        scene,
        pivotPoint,
        enabled,
        enableFlight,
        _keysDown
      } = this;
      if (!this.enabled) {
        return;
      }
      e.preventDefault();
      domElement2.focus();
      pointerTracker.addPointer(e);
      this.needsUpdate = true;
      this._cancelDoubleTapZoom();
      if (pointerTracker.isPointerTouch()) {
        pivotMesh.visible = false;
        if (pointerTracker.getPointerCount() === 0) {
          domElement2.setPointerCapture(e.pointerId);
        } else if (pointerTracker.getPointerCount() > 2) {
          this.resetState();
          return;
        }
      }
      pointerTracker.getCenterPoint(_pointer);
      adjustedPointerToCoords(_pointer, domElement2, _pointer);
      setRaycasterFromCamera(raycaster, _pointer, camera);
      const dot = Math.abs(raycaster.ray.direction.dot(up));
      if (dot < DRAG_PLANE_THRESHOLD || dot < DRAG_UP_THRESHOLD) {
        return;
      }
      const anyFlightKey = _keysDown.has("w") || _keysDown.has("s") || _keysDown.has("a") || _keysDown.has("d") || _keysDown.has("q") || _keysDown.has("e") || _keysDown.has("arrowup") || _keysDown.has("arrowdown") || _keysDown.has("arrowleft") || _keysDown.has("arrowright") || _keysDown.has("shift");
      if (enableFlight && anyFlightKey && !pointerTracker.isPointerTouch() && (pointerTracker.isRightClicked() || pointerTracker.isLeftClicked())) {
        pivotPoint.copy(camera.position);
        this.setState(FREE_ROTATE);
        return;
      }
      const hit = this._raycast(raycaster);
      if (hit) {
        if (pointerTracker.getPointerCount() === 2 || pointerTracker.isRightClicked() || pointerTracker.isLeftClicked() && e.shiftKey) {
          pivotPoint.copy(hit.point);
          pivotMesh.position.copy(hit.point);
          pivotMesh.visible = pointerTracker.isPointerTouch() ? false : enabled;
          pivotMesh.updateMatrixWorld();
          scene.add(pivotMesh);
          this.setState(pointerTracker.isPointerTouch() ? WAITING : ROTATE);
        } else if (pointerTracker.isLeftClicked()) {
          pivotPoint.copy(hit.point);
          pivotMesh.position.copy(hit.point);
          pivotMesh.updateMatrixWorld();
          scene.add(pivotMesh);
          this.setState(DRAG);
        }
      }
    };
    let _pointerMoveQueued = false;
    const pointermoveCallback = (e) => {
      const { pointerTracker } = this;
      if (!this.enabled) {
        return;
      }
      e.preventDefault();
      const {
        pivotMesh,
        enabled
      } = this;
      this.zoomDirectionSet = false;
      this.zoomPointSet = false;
      if (this.state !== NONE) {
        this.needsUpdate = true;
      }
      pointerTracker.setHoverEvent(e);
      if (!pointerTracker.updatePointer(e)) {
        return;
      }
      if (pointerTracker.isPointerTouch() && pointerTracker.getPointerCount() === 2) {
        if (!_pointerMoveQueued) {
          _pointerMoveQueued = true;
          queueMicrotask(() => {
            _pointerMoveQueued = false;
            pointerTracker.getCenterPoint(_centerPoint);
            const startDist = pointerTracker.getStartTouchPointerDistance();
            const pointerDist = pointerTracker.getTouchPointerDistance();
            const separateDelta = pointerDist - startDist;
            if (this.state === NONE || this.state === WAITING) {
              pointerTracker.getCenterPoint(_centerPoint);
              pointerTracker.getStartCenterPoint(_startCenterPoint);
              const dragThreshold = 2 * window.devicePixelRatio;
              const parallelDelta = _centerPoint.distanceTo(_startCenterPoint);
              if (Math.abs(separateDelta) > dragThreshold || parallelDelta > dragThreshold) {
                if (Math.abs(separateDelta) > parallelDelta) {
                  this.setState(ZOOM);
                  this.zoomDirectionSet = false;
                } else {
                  this.setState(ROTATE);
                }
              }
            }
            if (this.state === ZOOM) {
              const previousDist = pointerTracker.getPreviousTouchPointerDistance();
              this.zoomDelta += pointerDist - previousDist;
              pivotMesh.visible = false;
            } else if (this.state === ROTATE) {
              pivotMesh.visible = enabled;
            }
          });
        }
      }
      this.dispatchEvent(_changeEvent);
    };
    const pointerupCallback = (e) => {
      const { pointerTracker } = this;
      if (!this.enabled || pointerTracker.getPointerCount() === 0) {
        return;
      }
      if (this.enableDoubleTapZoom && e.button === 0 && pointerTracker.getPointerCount() === 1) {
        pointerTracker.getCenterPoint(_pointer);
        pointerTracker.getStartCenterPoint(_centerPoint);
        if (_pointer.distanceTo(_centerPoint) < TAP_MOVE_DISTANCE * window.devicePixelRatio) {
          const time = performance.now();
          if (time - this._lastTapTime < DOUBLE_TAP_INTERVAL && _pointer.distanceTo(this._lastTapPoint) < DOUBLE_TAP_DISTANCE * window.devicePixelRatio) {
            this._lastTapTime = -Infinity;
            this._beginDoubleTapZoom(_pointer);
          } else {
            this._lastTapTime = time;
            this._lastTapPoint.copy(_pointer);
          }
        }
      }
      pointerTracker.deletePointer(e);
      if (pointerTracker.getPointerType() === "touch" && pointerTracker.getPointerCount() === 0) {
        domElement.releasePointerCapture(e.pointerId);
      }
      this.resetState();
      this.needsUpdate = true;
    };
    const wheelCallback = (e) => {
      if (!this.enabled) {
        return;
      }
      e.preventDefault();
      this._cancelDoubleTapZoom();
      const { pointerTracker } = this;
      pointerTracker.setHoverEvent(e);
      pointerTracker.updatePointer(e);
      this.dispatchEvent(_startEvent);
      let delta;
      switch (e.deltaMode) {
        case 2:
          delta = e.deltaY * 800;
          break;
        case 1:
          delta = e.deltaY * 40;
          break;
        case 0:
          delta = e.deltaY;
          break;
      }
      const deltaSign = Math.sign(delta);
      const normalizedDelta = Math.abs(delta);
      this.zoomDelta -= 0.25 * deltaSign * normalizedDelta;
      this.needsUpdate = true;
      this._lastUsedState = ZOOM;
      this.dispatchEvent(_endEvent);
    };
    const pointerleaveCallback = (e) => {
      if (!this.enabled) {
        return;
      }
      this.resetState();
    };
    domElement.addEventListener("contextmenu", contextMenuCallback);
    domElement.addEventListener("pointerdown", pointerdownCallback);
    domElement.addEventListener("wheel", wheelCallback, { passive: false });
    const document = domElement.getRootNode();
    document.addEventListener("pointermove", pointermoveCallback);
    document.addEventListener("pointerup", pointerupCallback);
    document.addEventListener("pointerleave", pointerleaveCallback);
    const keydownCallback = (e) => {
      const { _keysDown, state } = this;
      _keysDown.add(e.key.toLowerCase());
      const anyFlightKey = _keysDown.has("w") || _keysDown.has("s") || _keysDown.has("a") || _keysDown.has("d") || _keysDown.has("q") || _keysDown.has("e") || _keysDown.has("arrowup") || _keysDown.has("arrowdown") || _keysDown.has("arrowleft") || _keysDown.has("arrowright");
      if (anyFlightKey && state !== FREE_ROTATE) {
        this.resetState();
      }
    };
    const keyupCallback = (e) => {
      this._keysDown.delete(e.key.toLowerCase());
    };
    const blurCallback = () => {
      this._keysDown.clear();
    };
    domElement.addEventListener("keydown", keydownCallback);
    window.addEventListener("keyup", keyupCallback);
    window.addEventListener("blur", blurCallback);
    this._detachCallback = () => {
      domElement.removeEventListener("contextmenu", contextMenuCallback);
      domElement.removeEventListener("pointerdown", pointerdownCallback);
      domElement.removeEventListener("wheel", wheelCallback);
      document.removeEventListener("pointermove", pointermoveCallback);
      document.removeEventListener("pointerup", pointerupCallback);
      document.removeEventListener("pointerleave", pointerleaveCallback);
      domElement.removeEventListener("keydown", keydownCallback);
      window.removeEventListener("keyup", keyupCallback);
      window.removeEventListener("blur", blurCallback);
    };
  }
  /**
   * Detaches the controls from the DOM element, removing all event listeners.
   */
  detach() {
    this.domElement = null;
    if (this._detachCallback) {
      this._detachCallback();
      this._detachCallback = null;
      this.pointerTracker.reset();
    }
  }
  /**
   * Returns the local up direction at a world-space point. Override to provide terrain-aware
   * up vectors (e.g. ellipsoid normals). Default returns the controls' `up` vector.
   * @param {Vector3} point - World-space point to query.
   * @param {Vector3} target - Target vector to write the result into.
   */
  getUpDirection(point, target) {
    target.copy(this.up);
  }
  /**
   * Returns the local up direction at the camera's current position.
   * @param {Vector3} target - Target vector to write the result into.
   */
  getCameraUpDirection(target) {
    this.getUpDirection(this.camera.position, target);
  }
  /**
   * Returns the current drag or rotation pivot point in world space.
   * @param {Vector3} target - Target vector to write the result into.
   * @returns {Vector3|null} The target vector, or null if no pivot is active.
   */
  getPivotPoint(target) {
    let result = null;
    if (this._lastUsedState === ZOOM) {
      if (this._zoomPointWasSet) {
        result = target.copy(this.zoomPoint);
      }
    } else if (this._lastUsedState === ROTATE || this._lastUsedState === DRAG) {
      result = target.copy(this.pivotPoint);
    }
    const { camera, raycaster } = this;
    if (result !== null) {
      _vec3.copy(result).project(camera);
      if (_vec3.x < -1 || _vec3.x > 1 || _vec3.y < -1 || _vec3.y > 1) {
        result = null;
      }
    }
    setRaycasterFromCamera(raycaster, { x: 0, y: 0 }, camera);
    const hit = this._raycast(raycaster);
    if (hit) {
      if (result === null || hit.distance < result.distanceTo(raycaster.ray.origin)) {
        result = target.copy(hit.point);
      }
    }
    return result;
  }
  /**
   * Clears the current interaction state, cancelling any active drag, rotate, or zoom.
   */
  resetState() {
    if (this.state !== NONE) {
      this.dispatchEvent(_endEvent);
    }
    this.state = NONE;
    this.pivotMesh.removeFromParent();
    this.pivotMesh.visible = this.enabled;
    this.actionHeightOffset = 0;
    this.pointerTracker.reset();
  }
  /**
   * Sets the current control state (e.g. `NONE`, `DRAG`, `ROTATE`, `ZOOM`).
   * @param {number} [state] - One of the exported state constants. Defaults to current state.
   * @param {boolean} [fireEvent=true] - Whether to dispatch `'start'` and `'end'` events.
   */
  setState(state = this.state, fireEvent = true) {
    if (this.state === state) {
      return;
    }
    if (this.state === NONE && fireEvent) {
      this.dispatchEvent(_startEvent);
    }
    this.pivotMesh.visible = this.enabled;
    this.dragInertia.set(0, 0, 0);
    this.rotationInertia.set(0, 0);
    this.inertiaStableFrames = 0;
    this.state = state;
    if (state !== NONE && state !== WAITING) {
      this._lastUsedState = state;
    }
  }
  /**
   * Applies pending input and inertia to the camera. Must be called each frame.
   * @param {number} [deltaTime] - Time in seconds since the last frame. Defaults to the clock delta, capped at 64ms.
   */
  update(deltaTime = Math.min(this._getDeltaTime(), 64 / 1e3)) {
    if (!this.enabled || !this.camera || deltaTime === 0) {
      return;
    }
    const {
      camera,
      cameraRadius,
      pivotPoint,
      up,
      state,
      adjustHeight,
      autoAdjustCameraRotation
    } = this;
    camera.updateMatrixWorld();
    this.getCameraUpDirection(_localUp);
    if (!this._upInitialized) {
      this._upInitialized = true;
      this.up.copy(_localUp);
    }
    this.zoomPointSet = false;
    this._updateDoubleTapZoom(deltaTime);
    const inertiaNeedsUpdate = this._inertiaNeedsUpdate();
    const adjustCameraRotation = this.needsUpdate || inertiaNeedsUpdate;
    if (this.needsUpdate || inertiaNeedsUpdate) {
      const zoomDelta = this.zoomDelta;
      this._updateZoom();
      this._updatePosition(deltaTime);
      this._updateRotation(deltaTime);
      if (state === DRAG || state === ROTATE || state === FREE_ROTATE) {
        _forward.set(0, 0, -1).transformDirection(camera.matrixWorld);
        this.inertiaTargetDistance = _vec3.copy(pivotPoint).sub(camera.position).dot(_forward);
      } else if (state === NONE) {
        this._updateInertia(deltaTime);
      }
      if (state !== NONE || zoomDelta !== 0 || inertiaNeedsUpdate) {
        this.dispatchEvent(_changeEvent);
      }
      this.needsUpdate = false;
    }
    const didFly = this._updateFlight(deltaTime);
    if (didFly) {
      this.dragInertia.set(0, 0, 0);
      this.rotationInertia.set(0, 0, 0);
      this.dispatchEvent(_changeEvent);
    }
    const hit = camera.isOrthographicCamera ? null : adjustHeight && !didFly && this._getPointBelowCamera() || null;
    this.getCameraUpDirection(_localUp);
    this._setFrame(_localUp);
    if ((this.state === DRAG || this.state === ROTATE || this.state === FREE_ROTATE) && this.actionHeightOffset !== 0) {
      const { actionHeightOffset } = this;
      camera.position.addScaledVector(up, -actionHeightOffset);
      pivotPoint.addScaledVector(up, -actionHeightOffset);
      if (hit) {
        hit.distance -= actionHeightOffset;
      }
    }
    this.actionHeightOffset = 0;
    if (hit) {
      const dist = hit.distance;
      if (dist < cameraRadius) {
        const delta = cameraRadius - dist;
        camera.position.addScaledVector(up, delta);
        pivotPoint.addScaledVector(up, delta);
        this.actionHeightOffset = delta;
      }
    }
    this.pointerTracker.updateFrame();
    if (adjustCameraRotation && autoAdjustCameraRotation || didFly) {
      this.getCameraUpDirection(_localUp);
      this._alignCameraUp(_localUp, 1);
      this.getCameraUpDirection(_localUp);
      this._clampRotation(_localUp);
    }
  }
  /**
   * Adjusts the camera to satisfy altitude and distance constraints. Called automatically by `update`.
   * Override in subclasses to add custom camera adjustment behaviour (e.g. near/far plane updates).
   * @param {Camera} camera
   */
  adjustCamera(camera) {
    const { adjustHeight, cameraRadius } = this;
    if (camera.isPerspectiveCamera) {
      this.getUpDirection(camera.position, _localUp);
      const hit = adjustHeight && this._getPointBelowCamera(camera.position, _localUp) || null;
      if (hit) {
        const dist = hit.distance;
        if (dist < cameraRadius) {
          camera.position.addScaledVector(_localUp, cameraRadius - dist);
        }
      }
    }
  }
  /**
   * Disposes of event listeners and internal resources. Calls `detach` if currently attached.
   */
  dispose() {
    this.detach();
  }
  // private
  _updateInertia(deltaTime) {
    const {
      rotationInertia,
      pivotPoint,
      dragInertia,
      enableDamping,
      dampingFactor,
      camera,
      cameraRadius,
      minDistance,
      inertiaTargetDistance
    } = this;
    if (!this.enableDamping || this.inertiaStableFrames > 1) {
      dragInertia.set(0, 0, 0);
      rotationInertia.set(0, 0, 0);
      return;
    }
    const factor = Math.pow(2, -deltaTime / dampingFactor);
    const stableDistance = Math.max(camera.near, cameraRadius, minDistance, inertiaTargetDistance);
    const resolution = 2 * 1e3;
    const pixelWidth = 2 / resolution;
    const pixelThreshold = 0.25 * pixelWidth;
    if (rotationInertia.lengthSq() > 0) {
      setRaycasterFromCamera(_ray, _vec3.set(0, 0, -1), camera);
      _ray.applyMatrix4(camera.matrixWorldInverse);
      _ray.direction.normalize();
      _ray.recast(-_ray.direction.dot(_ray.origin)).at(stableDistance / _ray.direction.z, _vec3);
      _vec3.applyMatrix4(camera.matrixWorld);
      setRaycasterFromCamera(_ray, _delta.set(pixelThreshold, pixelThreshold, -1), camera);
      _ray.applyMatrix4(camera.matrixWorldInverse);
      _ray.direction.normalize();
      _ray.recast(-_ray.direction.dot(_ray.origin)).at(stableDistance / _ray.direction.z, _delta);
      _delta.applyMatrix4(camera.matrixWorld);
      _vec3.sub(pivotPoint).normalize();
      _delta.sub(pivotPoint).normalize();
      const threshold = _vec3.angleTo(_delta) / deltaTime;
      rotationInertia.multiplyScalar(factor);
      if (rotationInertia.lengthSq() < threshold ** 2 || !enableDamping) {
        rotationInertia.set(0, 0);
      }
    }
    if (dragInertia.lengthSq() > 0) {
      setRaycasterFromCamera(_ray, _vec3.set(0, 0, -1), camera);
      _ray.applyMatrix4(camera.matrixWorldInverse);
      _ray.direction.normalize();
      _ray.recast(-_ray.direction.dot(_ray.origin)).at(stableDistance / _ray.direction.z, _vec3);
      _vec3.applyMatrix4(camera.matrixWorld);
      setRaycasterFromCamera(_ray, _delta.set(pixelThreshold, pixelThreshold, -1), camera);
      _ray.applyMatrix4(camera.matrixWorldInverse);
      _ray.direction.normalize();
      _ray.recast(-_ray.direction.dot(_ray.origin)).at(stableDistance / _ray.direction.z, _delta);
      _delta.applyMatrix4(camera.matrixWorld);
      const threshold = _vec3.distanceTo(_delta) / deltaTime;
      dragInertia.multiplyScalar(factor);
      if (dragInertia.lengthSq() < threshold ** 2 || !enableDamping) {
        dragInertia.set(0, 0, 0);
      }
    }
    if (rotationInertia.lengthSq() > 0) {
      this._applyRotation(rotationInertia.x * deltaTime, rotationInertia.y * deltaTime, pivotPoint);
    }
    if (dragInertia.lengthSq() > 0) {
      camera.position.addScaledVector(dragInertia, deltaTime);
      camera.updateMatrixWorld();
    }
  }
  _inertiaNeedsUpdate() {
    const { rotationInertia, dragInertia } = this;
    return rotationInertia.lengthSq() !== 0 || dragInertia.lengthSq() !== 0;
  }
  _getFlightSpeedScale() {
    return 1;
  }
  _updateFlight(deltaTime) {
    const {
      camera,
      enableFlight,
      flightSpeed,
      flightSpeedMultiplier,
      _keysDown
    } = this;
    if (!enableFlight || camera.isOrthographicCamera) {
      return false;
    }
    const forward = _keysDown.has("w") || _keysDown.has("arrowup");
    const back = _keysDown.has("s") || _keysDown.has("arrowdown");
    const left = _keysDown.has("a") || _keysDown.has("arrowleft");
    const right = _keysDown.has("d") || _keysDown.has("arrowright");
    const up = _keysDown.has("q");
    const down = _keysDown.has("e");
    const mult = _keysDown.has("shift") ? flightSpeedMultiplier : 1;
    const speed = mult * flightSpeed * this._getFlightSpeedScale() * deltaTime;
    _flightDir.set(
      (right ? 1 : 0) - (left ? 1 : 0),
      (up ? 1 : 0) - (down ? 1 : 0),
      (back ? 1 : 0) - (forward ? 1 : 0)
    );
    if (_flightDir.lengthSq() === 0) {
      return false;
    }
    _flightDir.normalize().transformDirection(camera.matrixWorld);
    camera.position.addScaledVector(_flightDir, speed);
    camera.updateMatrixWorld();
    return true;
  }
  _updateZoom() {
    const {
      zoomPoint,
      zoomDirection,
      camera,
      minDistance,
      maxDistance,
      pointerTracker,
      domElement,
      minZoom,
      maxZoom,
      zoomSpeed,
      state
    } = this;
    let scale = this.zoomDelta;
    this.zoomDelta = 0;
    if (!pointerTracker.getLatestPoint(_pointer) || scale === 0 && state !== ZOOM) {
      return;
    }
    this.rotationInertia.set(0, 0);
    this.dragInertia.set(0, 0, 0);
    if (camera.isOrthographicCamera) {
      this._updateZoomDirection();
      const zoomIntoPoint = this.zoomPointSet || this._updateZoomPoint();
      adjustedPointerToCoords(_pointer, domElement, _mouseBefore);
      _mouseBefore.unproject(camera);
      let scaleFactor = Math.pow(0.95, -zoomSpeed * scale * 0.05);
      if (scaleFactor > 1) {
        if (maxZoom < camera.zoom * scaleFactor) {
          scaleFactor = 1;
        }
      } else {
        if (minZoom > camera.zoom * scaleFactor) {
          scaleFactor = 1;
        }
      }
      camera.zoom *= scaleFactor;
      camera.updateProjectionMatrix();
      if (zoomIntoPoint) {
        adjustedPointerToCoords(_pointer, domElement, _mouseAfter);
        _mouseAfter.unproject(camera);
        camera.position.sub(_mouseAfter).add(_mouseBefore);
        camera.updateMatrixWorld();
      }
    } else {
      this._updateZoomDirection();
      const finalZoomDirection = _vec3.copy(zoomDirection);
      if (this.zoomPointSet || this._updateZoomPoint()) {
        const dist = zoomPoint.distanceTo(camera.position);
        if (scale < 0) {
          const remainingDistance = Math.min(0, dist - maxDistance);
          scale = scale * dist * zoomSpeed * ZOOM_DELTA_SCALAR;
          scale = Math.max(scale, remainingDistance);
        } else {
          const remainingDistance = Math.max(0, dist - minDistance);
          scale = scale * Math.max(dist - minDistance, 0) * zoomSpeed * ZOOM_DELTA_SCALAR;
          scale = Math.min(scale, remainingDistance);
        }
        camera.position.addScaledVector(zoomDirection, scale);
        camera.updateMatrixWorld();
      } else {
        const hit = this._getPointBelowCamera();
        if (hit) {
          const dist = hit.distance;
          finalZoomDirection.set(0, 0, -1).transformDirection(camera.matrixWorld);
          camera.position.addScaledVector(finalZoomDirection, scale * dist * 0.01);
          camera.updateMatrixWorld();
        } else {
          camera.position.addScaledVector(zoomDirection, scale);
          camera.updateMatrixWorld();
        }
      }
    }
  }
  // starts the double tap zoom animation toward the given pixel point
  _beginDoubleTapZoom(point) {
    const { camera, raycaster, domElement } = this;
    adjustedPointerToCoords(point, domElement, _centerPoint);
    setRaycasterFromCamera(raycaster, _centerPoint, camera);
    const hit = this._raycast(raycaster);
    if (hit === null) {
      return;
    }
    this.zoomPoint.copy(hit.point);
    this.zoomPointSet = true;
    this.zoomDirection.copy(raycaster.ray.direction).normalize();
    this.zoomDirectionSet = true;
    this._doubleTapPoint.copy(point);
    this._doubleTapZoomActive = true;
    this._doubleTapZoomElapsed = 0;
    this.needsUpdate = true;
    this.dispatchEvent(_startEvent);
  }
  // distributes the animated zoom over the frames as zoom deltas so the standard zoom logic applies
  _updateDoubleTapZoom(deltaTime) {
    if (!this._doubleTapZoomActive) {
      return;
    }
    const { doubleTapZoomDuration, doubleTapZoomScale, zoomSpeed, pointerTracker } = this;
    if (pointerTracker.getLatestPoint(_pointer) === null) {
      pointerTracker.hoverPosition.copy(this._doubleTapPoint);
      pointerTracker.hoverSet = true;
    }
    const totalDelta = Math.log(doubleTapZoomScale) / (ZOOM_DELTA_SCALAR * zoomSpeed);
    const easeOut = (t) => 1 - (1 - MathUtils.clamp(t, 0, 1)) ** 3;
    const prevAlpha = easeOut(this._doubleTapZoomElapsed / doubleTapZoomDuration);
    this._doubleTapZoomElapsed += deltaTime;
    const alpha = easeOut(this._doubleTapZoomElapsed / doubleTapZoomDuration);
    this.zoomDelta += totalDelta * (alpha - prevAlpha);
    this.needsUpdate = true;
    if (this._doubleTapZoomElapsed >= doubleTapZoomDuration) {
      this._doubleTapZoomActive = false;
      this.dispatchEvent(_endEvent);
    }
  }
  // interrupts the double tap zoom animation
  _cancelDoubleTapZoom() {
    if (this._doubleTapZoomActive) {
      this._doubleTapZoomActive = false;
      this.dispatchEvent(_endEvent);
    }
  }
  _updateZoomDirection() {
    if (this.zoomDirectionSet) {
      return;
    }
    const { domElement, raycaster, camera, zoomDirection, pointerTracker } = this;
    pointerTracker.getLatestPoint(_pointer);
    adjustedPointerToCoords(_pointer, domElement, _mouseBefore);
    setRaycasterFromCamera(raycaster, _mouseBefore, camera);
    zoomDirection.copy(raycaster.ray.direction).normalize();
    this.zoomDirectionSet = true;
  }
  // update the point being zoomed in to based on the zoom direction
  _updateZoomPoint() {
    const {
      camera,
      zoomDirectionSet,
      zoomDirection,
      raycaster,
      zoomPoint,
      pointerTracker,
      domElement
    } = this;
    this._zoomPointWasSet = false;
    if (!zoomDirectionSet) {
      return false;
    }
    if (camera.isOrthographicCamera && pointerTracker.getLatestPoint(_zoomPointPointer)) {
      adjustedPointerToCoords(_zoomPointPointer, domElement, _zoomPointPointer);
      setRaycasterFromCamera(raycaster, _zoomPointPointer, camera);
    } else {
      raycaster.ray.origin.copy(camera.position);
      raycaster.ray.direction.copy(zoomDirection);
      raycaster.near = 0;
      raycaster.far = Infinity;
    }
    const hit = this._raycast(raycaster);
    if (hit) {
      zoomPoint.copy(hit.point);
      this.zoomPointSet = true;
      this._zoomPointWasSet = true;
      return true;
    }
    return false;
  }
  // returns the point below the camera
  _getPointBelowCamera(point = this.camera.position, up = this.up) {
    const { raycaster } = this;
    raycaster.ray.direction.copy(up).multiplyScalar(-1);
    raycaster.ray.origin.copy(point).addScaledVector(up, 1e5);
    raycaster.near = 0;
    raycaster.far = Infinity;
    const hit = this._raycast(raycaster);
    if (hit) {
      hit.distance -= 1e5;
    }
    return hit;
  }
  // update the drag action
  _updatePosition(deltaTime) {
    const {
      raycaster,
      camera,
      pivotPoint,
      up,
      pointerTracker,
      domElement,
      state,
      dragInertia
    } = this;
    if (state === DRAG) {
      pointerTracker.getCenterPoint(_pointer);
      adjustedPointerToCoords(_pointer, domElement, _pointer);
      _plane.setFromNormalAndCoplanarPoint(up, pivotPoint);
      setRaycasterFromCamera(raycaster, _pointer, camera);
      if (Math.abs(raycaster.ray.direction.dot(up)) < DRAG_PLANE_THRESHOLD) {
        const angle = Math.acos(DRAG_PLANE_THRESHOLD);
        _rotationAxis.crossVectors(raycaster.ray.direction, up).normalize();
        raycaster.ray.direction.copy(up).applyAxisAngle(_rotationAxis, angle).multiplyScalar(-1);
      }
      this.getUpDirection(pivotPoint, _localUp);
      if (Math.abs(raycaster.ray.direction.dot(_localUp)) < DRAG_UP_THRESHOLD) {
        const angle = Math.acos(DRAG_UP_THRESHOLD);
        _rotationAxis.crossVectors(raycaster.ray.direction, _localUp).normalize();
        raycaster.ray.direction.copy(_localUp).applyAxisAngle(_rotationAxis, angle).multiplyScalar(-1);
      }
      if (raycaster.ray.intersectPlane(_plane, _vec3)) {
        _delta.subVectors(pivotPoint, _vec3);
        camera.position.add(_delta);
        camera.updateMatrixWorld();
        _delta.multiplyScalar(1 / deltaTime);
        if (pointerTracker.getMoveDistance() / deltaTime < 2 * window.devicePixelRatio) {
          this.inertiaStableFrames++;
        } else {
          dragInertia.copy(_delta);
          this.inertiaStableFrames = 0;
        }
      }
    }
  }
  _updateRotation(deltaTime) {
    const {
      pivotPoint,
      pointerTracker,
      domElement,
      state,
      rotationInertia
    } = this;
    if (state === ROTATE || state === FREE_ROTATE) {
      if (state === FREE_ROTATE) {
        pivotPoint.copy(this.camera.position);
      }
      pointerTracker.getCenterPoint(_pointer);
      pointerTracker.getPreviousCenterPoint(_prevPointer);
      _deltaPointer.subVectors(_pointer, _prevPointer).multiplyScalar(2 * Math.PI / domElement.clientHeight);
      this._applyRotation(_deltaPointer.x, _deltaPointer.y, pivotPoint);
      _deltaPointer.multiplyScalar(1 / deltaTime);
      if (pointerTracker.getMoveDistance() / deltaTime < 2 * window.devicePixelRatio) {
        this.inertiaStableFrames++;
      } else {
        rotationInertia.copy(_deltaPointer);
        this.inertiaStableFrames = 0;
      }
    }
  }
  _applyRotation(x, y, pivotPoint) {
    if (x === 0 && y === 0) {
      return;
    }
    const {
      camera,
      minAltitude,
      maxAltitude,
      rotationSpeed
    } = this;
    const azimuth = -x * rotationSpeed;
    let altitude = y * rotationSpeed;
    _forward.set(0, 0, 1).transformDirection(camera.matrixWorld);
    _right.set(1, 0, 0).transformDirection(camera.matrixWorld);
    this.getUpDirection(pivotPoint, _localUp);
    let angle;
    if (_localUp.dot(_forward) > 1 - 1e-10) {
      angle = 0;
    } else {
      _vec3.crossVectors(_localUp, _forward).normalize();
      const sign = Math.sign(_vec3.dot(_right));
      angle = sign * _localUp.angleTo(_forward);
    }
    if (altitude > 0) {
      altitude = Math.min(angle - minAltitude, altitude);
      altitude = Math.max(0, altitude);
    } else {
      altitude = Math.max(angle - maxAltitude, altitude);
      altitude = Math.min(0, altitude);
    }
    _quaternion.setFromAxisAngle(_localUp, azimuth);
    makeRotateAroundPoint(pivotPoint, _quaternion, _rotMatrix);
    camera.matrixWorld.premultiply(_rotMatrix);
    _right.set(1, 0, 0).transformDirection(camera.matrixWorld);
    _quaternion.setFromAxisAngle(_right, -altitude);
    makeRotateAroundPoint(pivotPoint, _quaternion, _rotMatrix);
    camera.matrixWorld.premultiply(_rotMatrix);
    camera.matrixWorld.decompose(camera.position, camera.quaternion, _vec3);
  }
  // sets the "up" axis for the current surface of the tileset
  _setFrame(newUp) {
    const {
      up,
      camera,
      zoomPoint,
      zoomDirectionSet,
      zoomPointSet,
      scaleZoomOrientationAtEdges
    } = this;
    if (zoomDirectionSet && (zoomPointSet || this._updateZoomPoint())) {
      _quaternion.setFromUnitVectors(up, newUp);
      if (scaleZoomOrientationAtEdges) {
        this.getUpDirection(zoomPoint, _vec3);
        let amt = Math.max(_vec3.dot(up) - 0.6, 0) / 0.4;
        amt = MathUtils.mapLinear(amt, 0, 0.5, 0, 1);
        amt = Math.min(amt, 1);
        if (camera.isOrthographicCamera) {
          amt *= 0.1;
        }
        _quaternion.slerp(_identityQuat, 1 - amt);
      }
      makeRotateAroundPoint(zoomPoint, _quaternion, _rotMatrix);
      camera.updateMatrixWorld();
      camera.matrixWorld.premultiply(_rotMatrix);
      camera.matrixWorld.decompose(camera.position, camera.quaternion, _vec3);
      this.zoomDirectionSet = false;
      this._updateZoomDirection();
    }
    up.copy(newUp);
    camera.updateMatrixWorld();
  }
  _raycast(raycaster) {
    const { scene, useFallbackPlane, fallbackPlane } = this;
    const result = raycaster.intersectObject(scene)[0] || null;
    if (result) {
      return result;
    } else if (useFallbackPlane) {
      const plane = fallbackPlane;
      if (raycaster.ray.intersectPlane(plane, _vec3)) {
        const planeHit = {
          point: _vec3.clone(),
          distance: raycaster.ray.origin.distanceTo(_vec3)
        };
        return planeHit;
      }
    }
    return null;
  }
  // tilt the camera to align with the provided "up" value
  _alignCameraUp(up, alpha = 1) {
    const { camera, state, pivotPoint, zoomPoint, zoomPointSet } = this;
    camera.updateMatrixWorld();
    _forward.set(0, 0, -1).transformDirection(camera.matrixWorld);
    _right.set(-1, 0, 0).transformDirection(camera.matrixWorld);
    let multiplier = MathUtils.mapLinear(1 - Math.abs(_forward.dot(up)), 0, 0.2, 0, 1);
    multiplier = MathUtils.clamp(multiplier, 0, 1);
    alpha *= multiplier;
    _targetRight.crossVectors(up, _forward);
    _targetRight.lerp(_right, 1 - alpha).normalize();
    _quaternion.setFromUnitVectors(_right, _targetRight);
    camera.quaternion.premultiply(_quaternion);
    let fixedPoint = null;
    if (state === DRAG || state === ROTATE || state === FREE_ROTATE) {
      fixedPoint = _pos.copy(pivotPoint);
    } else if (zoomPointSet) {
      fixedPoint = _pos.copy(zoomPoint);
    }
    if (fixedPoint) {
      _invMatrix.copy(camera.matrixWorld).invert();
      _vec3.copy(fixedPoint).applyMatrix4(_invMatrix);
      camera.updateMatrixWorld();
      _vec3.applyMatrix4(camera.matrixWorld);
      _center.subVectors(fixedPoint, _vec3);
      camera.position.add(_center);
    }
    camera.updateMatrixWorld();
  }
  // clamp rotation to the given "up" vector
  _clampRotation(up) {
    const { camera, minAltitude, maxAltitude, state, pivotPoint, zoomPoint, zoomPointSet } = this;
    camera.updateMatrixWorld();
    _forward.set(0, 0, 1).transformDirection(camera.matrixWorld);
    _right.set(1, 0, 0).transformDirection(camera.matrixWorld);
    let angle;
    if (up.dot(_forward) > 1 - 1e-10) {
      angle = 0;
    } else {
      _vec3.crossVectors(up, _forward);
      const sign = Math.sign(_vec3.dot(_right));
      angle = sign * up.angleTo(_forward);
    }
    let targetAngle;
    if (angle > maxAltitude) {
      targetAngle = maxAltitude;
    } else if (angle < minAltitude) {
      targetAngle = minAltitude;
    } else {
      return;
    }
    _forward.copy(up);
    _quaternion.setFromAxisAngle(_right, targetAngle);
    _forward.applyQuaternion(_quaternion).normalize();
    _vec3.crossVectors(_forward, _right).normalize();
    _rotMatrix.makeBasis(_right, _vec3, _forward);
    camera.quaternion.setFromRotationMatrix(_rotMatrix);
    let fixedPoint = null;
    if (state === DRAG || state === ROTATE || state === FREE_ROTATE) {
      fixedPoint = _pos.copy(pivotPoint);
    } else if (zoomPointSet) {
      fixedPoint = _pos.copy(zoomPoint);
    }
    if (fixedPoint) {
      _invMatrix.copy(camera.matrixWorld).invert();
      _vec3.copy(fixedPoint).applyMatrix4(_invMatrix);
      camera.updateMatrixWorld();
      _vec3.applyMatrix4(camera.matrixWorld);
      _center.subVectors(fixedPoint, _vec3);
      camera.position.add(_center);
    }
    camera.updateMatrixWorld();
  }
};
export {
  DRAG,
  EnvironmentControls,
  FREE_ROTATE,
  NONE,
  ROTATE,
  WAITING,
  ZOOM,
  ZOOM_DELTA_SCALAR
};
