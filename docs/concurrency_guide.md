# Qgis2threejs Concurrency Guide

This guide explains how the plugin separates UI responsibilities from long-running 3D scene generation work under PyQt/QGIS. It targets maintainers who need to debug, extend, or refactor the current threading model.

## Architectural Overview
- **UI shell**: The preview window (`Q3DWindow`) owns the web view and instantiates `Q3DController` with `useThread=RUN_BLDR_IN_BKGND`, so background work depends on the global flag in [conf.py](conf.py#L15) and the call site in [gui/window.py](gui/window.py#L64).
- **Controller layer**: `Q3DController` mediates between widgets, export settings, and the `ThreeJSBuilder`. It keeps a task queue and exposes slots to enqueue scene/layer work in [core/controller/controller.py](core/controller/controller.py#L90-L340).
- **Builder layer**: `ThreeJSBuilder` (and the layer/block builders it instantiates) performs CPU-intensive export logic and emits progress/data signals defined in [core/build/builder.py](core/build/builder.py#L25-L117).
- **View bridge**: `Q3DControllerInterface` translates controller requests into builder slots and relays builder output to the WebEngine/WebKit bridge in [core/controller/controller.py](core/controller/controller.py#L17-L59).

## Threads and Responsibilities
### UI Thread
- Owns all widgets (`Q3DWindow`, dialogs, tree view) and the controller.
- Maintains `ExportSettings`, handles status/progress UI, and schedules work via the controller queue [core/controller/controller.py#L90-L210](core/controller/controller.py#L90-L210).
- Runs `Q3DViewInterface` and JavaScript execution synchronously with Qt's GUI loop.

### Builder Thread
- Enabled when `RUN_BLDR_IN_BKGND` is `True` (default). `Q3DController` creates a `QThread`, moves `ThreeJSBuilder` into it, and starts the thread in [core/controller/controller.py#L103-L134](core/controller/controller.py#L103-L134).
- The builder keeps `isInUiThread` to switch between direct event processing and lock-based synchronization for its abort flag [core/build/builder.py#L38-L69](core/build/builder.py#L38-L69).
- Long-running work (scene/layer generation, block baking) happens entirely inside this worker.

## Signal/Slot Channels
`Q3DControllerInterface.setupConnections()` wires the following channels [core/controller/controller.py#L37-L50](core/controller/controller.py#L37-L50):

| From | Signal | To | Purpose |
|------|--------|----|---------|
| Controller interface | `buildSceneRequest()` | `ThreeJSBuilder.buildSceneSlot()` | Start full-scene build |
| Controller interface | `buildLayerRequest(Layer)` | `ThreeJSBuilder.buildLayerSlot(Layer)` | Build a single layer |
| Builder | `dataReady(dict)` | `Q3DViewInterface.sendData()` | Push serialized scene/layer chunks to JS |
| Builder | `taskCompleted()` / `taskAborted()` | `Q3DController.taskFinalized()` | Notify UI thread that the worker is idle |

Qt automatically queues cross-thread connections because the sender (builder) lives in the worker thread while the controller/interface live in the GUI thread.

## Task Queue Workflow
- `Q3DController` maintains `self.taskQueue` and a 1 ms single-shot `QTimer` to poll for the next task [core/controller/controller.py#L124-L210](core/controller/controller.py#L124-L210).
- Public API (`addBuildSceneTask`, `addBuildLayerTask`, `addRunScriptTask`) pushes tasks into the queue and triggers `processNextTask()` [core/controller/controller.py#L216-L370](core/controller/controller.py#L216-L370).
- `_processNextTask()` inspects the queue head, coalesces scene reloads, injects visible layers, and either fire-and-forgets JavaScript snippets or forwards work to the builder via the interface [core/controller/controller.py#L268-L348](core/controller/controller.py#L268-L348).
- `taskFinalized()` resets the busy flag, clears UI messages, and restarts the timer so the next task can begin [core/controller/controller.py#L249-L266](core/controller/controller.py#L249-L266).

This design keeps heavy work off the UI thread while still allowing synchronous UI-triggered scripts (e.g., quick `runScript` calls) to be interleaved when the worker is idle.

## Worker Execution and Cancellation
- `ThreeJSBuilder.buildSceneSlot()` and `buildLayerSlot()` reset the abort flag, call `buildScene()`/`layerBuilders()`, and emit `dataReady` payloads as soon as each chunk is ready [core/build/builder.py#L75-L117](core/build/builder.py#L75-L117).
- Cancellation relies on `ThreeJSBuilder.abort()`, which toggles a thread-safe flag checked at several points inside `_buildLayers()` and related loops [core/build/builder.py#L38-L157](core/build/builder.py#L38-L157). When the flag flips while a layer/block builder is running, the worker stops emitting data and fires `taskAborted`.
- `Q3DController.abort()` clears pending tasks (optional), shows a message, and forwards the abort request to the builder [core/controller/controller.py#L168-L214](core/controller/controller.py#L168-L214). Because only the abort flag is synchronized, callers must wait for `taskAborted`/`taskCompleted` before scheduling new work.

## Cleanup and Blocking Patterns
- When the preview window closes, it disconnects signals, stops the task queue, and calls `Q3DController.teardown()` [gui/window.py#L86-L140](gui/window.py#L86-L140). Teardown emits a custom `quitRequest`, waits for `builder.readyToQuit`, then quits and joins the worker thread via a local `QEventLoop` [core/controller/controller.py#L141-L167](core/controller/controller.py#L141-L167).
- `BridgeExporterBase.initWebPage()` (used by Processing exporters) also spins a local `QEventLoop` until the WebEngine/WebKit page emits `ready`, ensuring synchronous setup before any rendering call [core/export/export.py#L319-L355](core/export/export.py#L319-L355).
- Longer blocking exports ("Export to Web") still run on the UI thread: `ExportToWebDialog.accept()` instantiates `ThreeJSExporter` and calls `exporter.export(...)` directly [gui/exportdialog.py#L206-L244](gui/exportdialog.py#L206-L244). To keep the window responsive it periodically pumps events with `QgsApplication.processEvents(QEventLoop.ProcessEventsFlag.ExcludeUserInputEvents)` inside `progress()`/`log()` [gui/exportdialog.py#L248-L276](gui/exportdialog.py#L248-L276), but user input stays disabled while the call is in flight.

## Known Limitations and Pain Points
1. **Single worker thread and fixed policy** – Whether the builder runs in the background is controlled by a module-level constant and can only be changed by editing configuration or restarting QGIS [conf.py#L15](conf.py#L15). There is no per-operation choice, nor a way to spin up multiple workers for independent layers.
2. **Manual task queue** – `_processNextTask()` polls via a tight 1 ms timer and linear queue scans [core/controller/controller.py#L216-L348](core/controller/controller.py#L216-L348). There is no prioritization, debouncing, or deduplication beyond ad-hoc checks, so rapidly toggling layer visibility can grow the queue and rely on manual aborts to stay responsive.
3. **Shared settings without isolation** – `updateExportSettings()` replaces the controller's `ExportSettings` reference while the builder keeps the original instance [core/controller/controller.py#L333-L364](core/controller/controller.py#L333-L364). When the UI mutates settings during a long build, the worker may render inconsistent state because there is no copy-on-submit or locking around the settings object.
4. **Blocking exports on the GUI thread** – The exporter dialog still performs all file I/O and serialization synchronously, relying on `QgsApplication.processEvents()` to avoid freezing [gui/exportdialog.py#L206-L276](gui/exportdialog.py#L206-L276). Any heavy template or filesystem work therefore competes with repainting and can feel unresponsive.
5. **Custom `QEventLoop` usage** – Both teardown and exporter bridges run ad-hoc nested event loops [core/controller/controller.py#L149-L167](core/controller/controller.py#L149-L167) and [core/export/export.py#L319-L355](core/export/export.py#L319-L355). If the expected signal never fires (e.g., due to network errors when loading templates), these loops block the UI indefinitely and are hard to debug.
6. **Coarse-grained cancellation** – The abort flag is only checked between layers/blocks [core/build/builder.py#L104-L157](core/build/builder.py#L104-L157). Large blocks (dense DEM tiles, heavy point clouds) cannot be interrupted promptly, so aborting may appear to hang.

## Suggested Improvements
1. **Adopt `QgsTask` / `QThreadPool`** – Replace the manual `QThread` + queue with QGIS' task framework to get prioritization, progress reporting, and cooperative cancellation. Each layer build could be its own task, enabling parallelism on multi-core machines.
2. **Snapshot settings per job** – When enqueuing a build, clone the relevant `ExportSettings` subset and pass the snapshot to the worker. This removes unsynchronized shared state between the GUI and worker and guarantees deterministic builds.
3. **Move exporter dialogs off the UI thread** – Wrap `ThreeJSExporter.export()` in a worker task and use Qt signals to stream progress back, rather than pumping the event loop manually. This keeps buttons responsive and simplifies cancellation via a shared abort flag.
4. **Replace polling timer with queued invocations** – Instead of a 1 ms timer, push tasks into the worker through queued connections or a dedicated scheduler object that only wakes when new work arrives. This reduces idle CPU wakeups and simplifies reasoning about reentrancy.
5. **Centralize shutdown/error paths** – Factor the various `QEventLoop`-based waits into a reusable helper that includes timeouts and error propagation, minimizing the risk of deadlocks during teardown or page initialization.
6. **Finer-grained abort checks** – Extend layer/builder implementations to periodically call `self.aborted` inside inner loops (feature iteration, geometry tessellation) so cancellation is fast even for complex datasets.

Understanding these moving parts should make it easier to reason about race conditions, UI responsiveness, and future concurrency refactors within Qgis2threejs.
