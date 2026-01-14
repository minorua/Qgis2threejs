# Qgis2threejs Communication Overview

This document describes how data and signals flow between the Controller, Task Manager, ThreeJSBuilder, Layer Builder(s), Web Page, Web Bridge, and the JavaScript world in Qgis2threejs. It also includes a chronological walkthrough from web page load to scene load completion.

## Components and Roles

- **Controller (`Q3DController`)**: Orchestrates preview/export. Sends build requests, queues outgoing data, tracks progress, runs JS scripts via the web page interface.
- **Task Manager (`TaskManager`)**: Owns the task queue and drives the sequence: build scene, update scene options, build each visible layer, optional scripts/reload.
- **ThreeJSBuilder**: Constructs export payloads for scene, layers, and blocks. Reports progress and emits data incrementally.
- **Layer Builders (`LayerBuilderBase` and subclasses)**: Per-layer logic to produce `type:"layer"` and `type:"block"` payloads and common properties.
- **Web Page (`Q3DWebEnginePage`/`Q3DWebViewCommon`)**: Hosts the viewer, logs scripts, loads JS files, provides data sending and rendering requests.
- **Web Bridge (`WebBridge`)**: Qt/JS bridge signals (Python→JS script dispatch; JS→Python events like loadComplete, sceneLoaded, image/model save, test results).
- **JavaScript world (`viewer.js`, `Qgis2threejs.js`)**: Receives data via `loadData(pyData(),progress)`, applies it to `Q3D.application` / `Q3DScene`, manages loading/progress, renders, and emits events back via the bridge.

## Signals and Data Paths

### Python → Python
- Controller → Builder
  - `buildSceneRequest(ExportSettings)`
  - `buildLayerRequest(Layer, ExportSettings)`
- Builder → Controller
  - `dataReady(dict)` with `dict.type ∈ {scene, layer, block}`
  - `progressUpdated(current, total, msg)`
  - `taskCompleted()` / `taskFailed(target, traceback)` / `taskAborted()`
- Task Manager → Controller
  - `executeTask(object)` where object ∈ `Task.*`, `Layer`, `{string, data}`
  - `abortCurrentTask()` / `allTasksFinalized()`

### Python → JavaScript
- Controller/WebPage → Bridge → JS
  - `sendScriptData(script, data)` where JS evaluates `script` with `pyData()` bound to `data` (typical: `loadData(pyData(), progress)`)
  - Direct scripts via `runScript(string)` (no data), e.g. `init(...)`, `requestRendering()`, `tasksAndLoadingFinalized(...)`

### JavaScript → Python
- JS (viewer) → Bridge → Python
  - `emitInitialized()` → `initialized`
  - `emitDataLoaded()` → `dataLoaded`
  - `emitDataLoadError()` → `dataLoadError`
  - `emitSceneLoaded()` → `sceneLoaded`
  - `emitScriptReady(id)` → `scriptFileLoaded(id)`
  - Animation events: `emitTweenStarted(index)`, `emitAnimationStopped()`
  - Output: `saveBytes(data, filename)`, `saveString(text, filename)`, `saveImage(dataUrl)`, `copyToClipboard(dataUrl)`
  - `emitRequestedRenderingFinished()` (after `requestRendering()`)
  - `showStatusMessage(message, timeout)`

## Data Payloads

Builder and Layer Builders emit dictionaries consumed by JS:

- `type: "scene"` with `properties`:
  - `baseExtent`: `{cx, cy, width, height, rotation}`
  - `origin`: `{x, y, z}`
  - `zScale`: number
  - `light`: `"point" | "directional"`
  - `fog` (optional): `{color, density}`
  - `proj` (optional): PROJ string (for lat/lon display)
- `type: "layer"` with `id`, `properties`:
  - Common: `name`, `visible`, `clickable`, `type ∈ {dem, point, line, polygon, pc}`
  - Layer-specific body: geometry, materials, textures, point cloud config, etc.
- `type: "block"` with `layer` id and block-specific payload (e.g., geometries, textures). Blocks allow incremental load/render.

## Progress and Finalization

- **Progress:** `Builder.progressUpdated(current,total,msg)` → `Controller.builderProgressUpdated(...)` computes overall percentage. When sending, `WebPage.sendData(data, progress)` passes a progress value to JS, which updates the progress bar.
- **Finalization:** When all tasks are done and no more data is loading or queued, `Controller` calls `tasksAndLoadingFinalized(complete,is_scene)`. If `complete && is_scene`, JS fires `sceneLoaded`, and the bridge echoes it to Python.

## Script Loading (Dynamic Dependencies)

- Controller requests scripts based on layer type (e.g., `COLLADALOADER`, `GLTFLOADER`, `MESHLINE`, `POTREE`).
- Web Page runs `loadScriptFile(path, callback)` in JS; on load, JS invokes `pyObj.emitScriptReady(id)`; `WebBridge.scriptFileLoaded(id)` resolves any waiting callbacks.

## Error and Abort Handling

- JS load errors emit `dataLoadError` → Python can notify/status.
- Controller `abort()` clears the send queue, resets scene load status, and asks `Builder` to abort. `TaskManager.abortCurrentTask()` can preempt ongoing work.

---

## Chronology: From Web Page Load to Scene Load Complete

This section describes the step-by-step sequence from initially loading the web page to completing the scene load in preview.

1. **Web Page Setup (Python)**
   - `Q3DWebEnginePage.setup()` configures the URL for the viewer page (`web/viewer/webengine.html`) and calls `reload()`.
   - `Controller.pageLoaded(ok)` runs after the page load finishes. It:
     - Clears previous queue/state.
     - Optionally sets configuration scripts (orthographic camera, north arrow, navigation).
     - Executes `init(off_screen, debug_mode, qgis_version, is_webengine)` via `runScript()`.

2. **Viewer Initialization (JavaScript)**
   - In `viewer.js`, `init(...)`:
     - If WebEngine, establishes Qt `QWebChannel`, registers `pyObj = bridge`, and connects `pyObj.sendScriptData` so that any Python-sent script is `eval()`ed with `pyData()` bound to the data payload.
     - Calls `_init(off_screen)` to create the application, hook events, and run capability checks.
     - Emits `pyObj.emitInitialized()` (Bridge → Python `initialized`).

3. **Controller Reacts to Initialization (Python)**
   - `Controller.viewerInitialized()`:
     - Applies labels (header/footer) and warnings (e.g., geographic CRS).
     - Clears any status messages.
     - Starts the app (`runScript("app.start()")`).
     - Enqueues a build scene task: `TaskManager.addBuildSceneTask()`.

4. **Task Dispatch (Python)**
   - `TaskManager.processNextTask()` pops the next item. For `BUILD_SCENE`:
     - Marks `sceneLoadStatus.buildSceneStarted = true`.
     - Emits `executeTask(Task.BUILD_SCENE)` to the Controller.
   - `Controller.executeTask(...)` calls `buildScene()` → emits `buildSceneRequest(ExportSettings)` to the Builder.

5. **Scene Build and Data Emission (Python)**
   - `ThreeJSBuilder.buildSceneSlot(settings)`:
     - Builds `type:"scene"` data with properties.
     - Emits `dataReady(scene)`.
     - Emits `taskCompleted()`.

6. **Data Send and JS Load (Python → JS)**
   - `Controller.appendDataToSendQueue(data)` enqueues and triggers `sendQueuedData()` if idle.
   - `Controller.sendData(data, progress)` → `WebPage.sendData(...)` → `Bridge.sendScriptData("loadData(pyData(),progress)", data)`.
   - In `viewer.js`, the bridge handler `eval()`s `loadData(pyData(), progress)`, which calls `app.loadData(data)`.

7. **JavaScript Applies Scene (JS)**
   - `Q3DScene.loadData(data)` handles `type:"scene"`:
     - Applies properties, fog/light, computes pivot and camera parameters.
     - Requests camera update; loads any nested layers in `data.layers` if provided.
     - Calls `requestRender()`.
   - The loading manager wraps item start/end, and the progress bar is updated when `progress` is provided.

8. **JS Loading Complete Event (JS → Python)**
   - When the viewer’s `app.loadingManager` finishes current items, it dispatches `loadComplete`.
   - `viewer.js` handles `loadComplete`:
     - Sets `preview.isDataLoading = false`.
     - Schedules `pyObj.emitDataLoaded()` after a minimal delay.

9. **Controller Advances or Finalizes (Python)**
   - `Controller.dataLoaded()`:
     - Sets `isDataLoading = false`.
     - If there are more items in `sendQueue`, immediately sends the next.
     - If the queue is empty and `TaskManager.sceneLoadStatus.allTasksFinalized` is true, calls `_tasksAndLoadingFinalized(complete, is_scene)`, which runs `tasksAndLoadingFinalized(...)` in JS.

10. **JS Finalization and Scene Loaded (JS → Python)**
    - `viewer.js` `tasksAndLoadingFinalized(complete, is_scene)` hides the progress bar.
    - If `complete && is_scene`, it dispatches `sceneLoaded` on the app.
    - The handler calls `pyObj.emitSceneLoaded()`, which the Bridge emits as `sceneLoaded` back to Python.

11. **Subsequent Tasks (Layers, Options)**
    - After `BUILD_SCENE`, `TaskManager` typically enqueues `UPDATE_SCENE_OPTS` and each visible `Layer`.
    - Layer tasks lead to `type:"layer"` and then multiple `type:"block"` payloads. Each payload follows the same send/load/emit pattern, with `dataLoaded` gating the next send.

## Notes on Concurrency and Ordering

- The flow is **task-driven and serial**: one task at a time from `TaskManager`.
- **Data send/JS load is throttled** by `Controller.isDataLoading`: Python waits for `dataLoaded` before sending the next payload to avoid overloading the JS loader.
- **Progress computation** combines per-layer progress and overall layer counts to present a unified percentage.
- **Script dependencies** are loaded before building layer types that require them (e.g., GLTF/Collada loaders, MeshLine, Potree).

## Improvements: Data & Signal Communication

Below are concrete areas to improve robustness, performance, and maintainability of the current communication design.

- **Replace `eval`-based command dispatch with explicit RPC:** Instead of sending free-form `script` strings to `sendScriptData` and evaluating them, expose explicit methods on the JS side via QWebChannel (e.g., `bridge.loadSceneData(data, progress)`, `bridge.loadLayerData(data, progress)`, `bridge.loadBlockData(data, progress)`). Python would call these directly, avoiding `eval(script)` and improving safety and tooling support.
- **Structured payload validation:** Define JSON Schemas (see `docs/schema/qgis2threejs.schema.json`) for `scene`, `layer`, and `block` payloads and validate on both Python and JS before applying. Early validation yields more actionable errors and reduces silent failures.
- **Richer error reporting:** Extend `dataLoadError` to include `type`, `id`, and a message (e.g., `dataLoadError(type, id, msg)`). On Python, log and correlate with the originating task/layer; on JS, attach loader/texture/model errors to the appropriate item.
- **Progress accounting from manifests:** Have `Builder` emit an initial lightweight manifest per task (e.g., total blocks, expected assets) so `Controller` can compute more accurate overall progress. `LayerBuilderBase.blockCount()` can be leveraged or made more accurate per layer type.
- **Preload script dependencies in batch:** Instead of per-layer conditional loads, compute the union of all required script ids from the pending task queue and call `loadScriptFiles([...], wait=true)` once up-front. This removes interleaved pauses, reduces latency spikes, and simplifies timing.
- **Adaptive send window (credit-based backpressure):** Current gating is strictly one payload at a time (`isDataLoading`). For asset-light blocks, allow a small window (e.g., 2–3 outstanding loads) governed by loading manager credits; fall back to single-flight when textures/models are involved or when GPU/CPU is saturated. Keep `preview.noRenderDuringLoad` guard to avoid excessive re-renders.
- **Abort propagation into JS loaders:** When `Controller.abort()`/`TaskManager.abortCurrentTask()` is invoked, forward an `abortRequested` event to JS to cancel pending XHR/Texture loads (where supported) and clear queued operations (e.g., Potree workers). This makes aborts snappier and reduces wasted work.
- **Status and console integration:** Standardize levels (`debug/info/warn/error`) already reflected by `jsErrorWarning`; add an option to relay selected JS console messages back to Python logs with source file/line, and a user-facing toggle to reduce noise.
- **Security hardening for remote URLs:** `LocalContentCanAccessRemoteUrls` is necessary for remote assets; consider adding an allowlist or filtering to reduce risk when loading untrusted resources.
- **Binary/asset handling:** For large assets, prefer URLs over embedding large base64 blobs. When binary transfer is required, use `QByteArray` consistently, consider compression, and stream in chunks for point clouds.

---

## References

- Controller connections and methods: `core/controller/controller.py`
- Task sequencing: `core/controller/taskmanager.py`
- Builder and layer builders: `core/build/builder.py`, `core/build/layerbuilderbase.py` + subpackages
- Bridge and web page: `gui/webbridge.py`, `gui/webengineview.py`, `gui/webviewcommon.py`
- Viewer and application: `web/viewer/viewer.js`, `web/js/Qgis2threejs.js`
