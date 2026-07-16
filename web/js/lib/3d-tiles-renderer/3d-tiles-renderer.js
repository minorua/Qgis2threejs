var __defProp = Object.defineProperty;
var __export = (target, all) => {
  for (var name in all)
    __defProp(target, name, { get: all[name], enumerable: true });
};

// build/core/renderer/utilities/TraversalUtils.js
function traverseSet(tile, beforeCb = null, afterCb = null) {
  const stack = [];
  stack.push(tile);
  stack.push(null);
  stack.push(0);
  while (stack.length > 0) {
    const depth = stack.pop();
    const parent = stack.pop();
    const tile2 = stack.pop();
    if (beforeCb && beforeCb(tile2, parent, depth)) {
      if (afterCb) {
        afterCb(tile2, parent, depth);
      }
      return;
    }
    const children = tile2.children;
    if (children) {
      for (let i = children.length - 1; i >= 0; i--) {
        stack.push(children[i]);
        stack.push(tile2);
        stack.push(depth + 1);
      }
    }
    if (afterCb) {
      afterCb(tile2, parent, depth);
    }
  }
}

// build/core/renderer/utilities/LoaderUtils.js
var LoaderUtils_exports = {};
__export(LoaderUtils_exports, {
  arrayToString: () => arrayToString,
  getWorkingPath: () => getWorkingPath,
  readMagicBytes: () => readMagicBytes
});
function readMagicBytes(bufferOrDataView) {
  if (bufferOrDataView === null || bufferOrDataView.byteLength < 4) {
    return "";
  }
  let view;
  if (bufferOrDataView instanceof DataView) {
    view = bufferOrDataView;
  } else {
    view = new DataView(bufferOrDataView);
  }
  if (String.fromCharCode(view.getUint8(0)) === "{") {
    return null;
  }
  let magicBytes = "";
  for (let i = 0; i < 4; i++) {
    magicBytes += String.fromCharCode(view.getUint8(i));
  }
  return magicBytes;
}
var utf8decoder = new TextDecoder();
function arrayToString(array) {
  return utf8decoder.decode(array);
}
function getWorkingPath(url) {
  return url.replace(/[\\/][^\\/]+$/, "") + "/";
}

// build/core/renderer/utilities/urlExtension.js
function getUrlExtension(url) {
  if (!url) {
    return null;
  }
  let endIndex = url.length;
  const queryIndex = url.indexOf("?");
  const fragmentIndex = url.indexOf("#");
  if (queryIndex !== -1) {
    endIndex = Math.min(endIndex, queryIndex);
  }
  if (fragmentIndex !== -1) {
    endIndex = Math.min(endIndex, fragmentIndex);
  }
  const lastPeriodIndex = url.lastIndexOf(".", endIndex);
  const lastSlashIndex = url.lastIndexOf("/", endIndex);
  const protocolIndex = url.indexOf("://");
  const isHostOnly = protocolIndex !== -1 && protocolIndex + 2 === lastSlashIndex;
  if (isHostOnly || lastPeriodIndex === -1 || lastPeriodIndex < lastSlashIndex) {
    return null;
  }
  return url.substring(lastPeriodIndex + 1, endIndex) || null;
}

// build/core/renderer/utilities/Scheduler.js
var Scheduler = class {
  static pending = /* @__PURE__ */ new Map();
  static session = null;
  /**
   * Sets the active "XRSession" value to use to scheduling rAF callbacks.
   * @param {XRSession} session
   */
  static setXRSession(session) {
    if (session !== this.session) {
      this.flushPending();
      this.session = session;
    }
  }
  /**
   * Request animation frame (defer to XR session if set)
   * @param {Function} cb
   * @returns {number}
   */
  static requestAnimationFrame(cb) {
    const { session, pending } = this;
    let handle;
    const func = () => {
      pending.delete(handle);
      cb();
    };
    if (!session) {
      handle = requestAnimationFrame(func);
    } else {
      handle = session.requestAnimationFrame(func);
    }
    pending.set(handle, cb);
    return handle;
  }
  /**
   * Cancel animation frame via handle (defer to XR session if set)
   * @param {number} handle
   */
  static cancelAnimationFrame(handle) {
    const { pending, session } = this;
    pending.delete(handle);
    if (!session) {
      cancelAnimationFrame(handle);
    } else {
      session.cancelAnimationFrame(handle);
    }
  }
  /**
   * Flush and complete pending AFs (defer to XR session if set)
   */
  static flushPending() {
    this.pending.forEach((cb, handle) => {
      cb();
      this.cancelAnimationFrame(handle);
    });
  }
};

// build/core/renderer/utilities/LRUCache.js
var GIGABYTE_BYTES = 2 ** 30;
var LRUCache = class {
  /**
   * Comparator used to determine eviction order. Items that sort last are evicted first.
   * When `null`, eviction order is by last-used time.
   * @type {UnloadPriorityCallback|null}
   * @default null
   */
  get unloadPriorityCallback() {
    return this._unloadPriorityCallback;
  }
  set unloadPriorityCallback(cb) {
    if (cb.length === 1) {
      console.warn('LRUCache: "unloadPriorityCallback" function has been changed to take two arguments.');
      this._unloadPriorityCallback = (a, b) => {
        const valA = cb(a);
        const valB = cb(b);
        if (valA < valB) return -1;
        if (valA > valB) return 1;
        return 0;
      };
    } else {
      this._unloadPriorityCallback = cb;
    }
  }
  constructor() {
    this.minSize = 6e3;
    this.maxSize = 8e3;
    this.minBytesSize = 0.3 * GIGABYTE_BYTES;
    this.maxBytesSize = 0.4 * GIGABYTE_BYTES;
    this.unloadPercent = 0.05;
    this.autoMarkUnused = true;
    this.itemSet = /* @__PURE__ */ new Map();
    this.itemList = [];
    this.usedSet = /* @__PURE__ */ new Set();
    this.callbacks = /* @__PURE__ */ new Map();
    this.unloadingHandle = -1;
    this.cachedBytes = 0;
    this.bytesMap = /* @__PURE__ */ new Map();
    this.loadedSet = /* @__PURE__ */ new Set();
    this._unloadPriorityCallback = null;
    const itemSet = this.itemSet;
    this.defaultPriorityCallback = (item) => itemSet.get(item);
  }
  /**
   * Returns whether the cache has reached its maximum item count or byte size.
   * @returns {boolean}
   */
  isFull() {
    return this.itemSet.size >= this.maxSize || this.cachedBytes >= this.maxBytesSize;
  }
  /**
   * Returns the byte size registered for the given item, or 0 if not tracked.
   * @param {any} item
   * @returns {number}
   */
  getMemoryUsage(item) {
    return this.bytesMap.get(item) || 0;
  }
  /**
   * Sets the byte size for the given item, updating the total `cachedBytes` count.
   * @param {any} item
   * @param {number} bytes
   */
  setMemoryUsage(item, bytes) {
    const { bytesMap, itemSet } = this;
    if (!itemSet.has(item)) {
      return;
    }
    this.cachedBytes -= bytesMap.get(item) || 0;
    bytesMap.set(item, bytes);
    this.cachedBytes += bytes;
  }
  /**
   * Adds an item to the cache. Returns false if the item already exists or the cache is full.
   * @param {any} item
   * @param {RemoveCallback} removeCb - Called with the item when it is evicted
   * @returns {boolean}
   */
  add(item, removeCb) {
    const itemSet = this.itemSet;
    if (itemSet.has(item)) {
      return false;
    }
    if (this.isFull()) {
      return false;
    }
    const usedSet = this.usedSet;
    const itemList = this.itemList;
    const callbacks = this.callbacks;
    itemList.push(item);
    usedSet.add(item);
    itemSet.set(item, Date.now());
    callbacks.set(item, removeCb);
    return true;
  }
  /**
   * Returns whether the given item is in the cache.
   * @param {any} item
   * @returns {boolean}
   */
  has(item) {
    return this.itemSet.has(item);
  }
  /**
   * Removes an item from the cache immediately, invoking its removal callback.
   * Returns false if the item was not in the cache.
   * @param {any} item
   * @returns {boolean}
   */
  remove(item) {
    const usedSet = this.usedSet;
    const itemSet = this.itemSet;
    const itemList = this.itemList;
    const bytesMap = this.bytesMap;
    const callbacks = this.callbacks;
    const loadedSet = this.loadedSet;
    if (itemSet.has(item)) {
      this.cachedBytes -= bytesMap.get(item) || 0;
      bytesMap.delete(item);
      callbacks.get(item)(item);
      const index = itemList.indexOf(item);
      itemList.splice(index, 1);
      usedSet.delete(item);
      itemSet.delete(item);
      callbacks.delete(item);
      loadedSet.delete(item);
      return true;
    }
    return false;
  }
  /**
   * Marks whether an item has finished loading. Unloaded items may be evicted early
   * when the cache is over its max size limits, even if they are marked as used.
   * @param {any} item
   * @param {boolean} value
   */
  setLoaded(item, value) {
    const { itemSet, loadedSet } = this;
    if (itemSet.has(item)) {
      if (value === true) {
        loadedSet.add(item);
      } else {
        loadedSet.delete(item);
      }
    }
  }
  /**
   * Marks an item as used in the current frame, preventing it from being evicted.
   * @param {any} item
   */
  markUsed(item) {
    const itemSet = this.itemSet;
    const usedSet = this.usedSet;
    if (itemSet.has(item) && !usedSet.has(item)) {
      itemSet.set(item, Date.now());
      usedSet.add(item);
    }
  }
  /**
   * Marks an item as unused, making it eligible for eviction.
   * @param {any} item
   */
  markUnused(item) {
    this.usedSet.delete(item);
  }
  /**
   * Marks all items in the cache as unused.
   */
  markAllUnused() {
    this.usedSet.clear();
  }
  /**
   * Returns whether the given item is currently marked as used.
   * @param {any} item
   * @returns {boolean}
   */
  isUsed(item) {
    return this.usedSet.has(item);
  }
  /**
   * Evicts unused items until the cache is within its min size and byte limits.
   * Items are sorted by `unloadPriorityCallback` before eviction.
   */
  // TODO: this should be renamed because it's not necessarily unloading all unused content
  // Maybe call it "cleanup" or "unloadToMinSize"
  unloadUnusedContent() {
    const {
      unloadPercent,
      minSize,
      maxSize,
      itemList,
      itemSet,
      usedSet,
      loadedSet,
      callbacks,
      bytesMap,
      minBytesSize,
      maxBytesSize
    } = this;
    const unused = itemList.length - usedSet.size;
    const unloaded = itemList.length - loadedSet.size;
    const excessNodes = Math.max(Math.min(itemList.length - minSize, unused), 0);
    const excessBytes = this.cachedBytes - minBytesSize;
    const unloadPriorityCallback = this.unloadPriorityCallback || this.defaultPriorityCallback;
    let needsRerun = false;
    const hasNodesToUnload = excessNodes > 0 && unused > 0 || unloaded && itemList.length > maxSize;
    const hasBytesToUnload = unused && this.cachedBytes > minBytesSize || unloaded && this.cachedBytes > maxBytesSize;
    if (hasBytesToUnload || hasNodesToUnload) {
      itemList.sort((a, b) => {
        const usedA = usedSet.has(a);
        const usedB = usedSet.has(b);
        if (usedA === usedB) {
          const loadedA = loadedSet.has(a);
          const loadedB = loadedSet.has(b);
          if (loadedA === loadedB) {
            return -unloadPriorityCallback(a, b);
          } else {
            return loadedA ? 1 : -1;
          }
        } else {
          return usedA ? 1 : -1;
        }
      });
      const maxUnload = Math.max(minSize * unloadPercent, excessNodes * unloadPercent);
      const nodesToUnload = Math.ceil(Math.min(maxUnload, unused, excessNodes));
      const maxBytesUnload = Math.max(unloadPercent * excessBytes, unloadPercent * minBytesSize);
      const bytesToUnload = Math.min(maxBytesUnload, excessBytes);
      let removedNodes = 0;
      let removedBytes = 0;
      while (this.cachedBytes - removedBytes > maxBytesSize || itemList.length - removedNodes > maxSize) {
        const item = itemList[removedNodes];
        const bytes = bytesMap.get(item) || 0;
        if (usedSet.has(item) && loadedSet.has(item) || this.cachedBytes - removedBytes - bytes < maxBytesSize && itemList.length - removedNodes <= maxSize) {
          break;
        }
        removedBytes += bytes;
        removedNodes++;
      }
      while (removedBytes < bytesToUnload || removedNodes < nodesToUnload) {
        const item = itemList[removedNodes];
        const bytes = bytesMap.get(item) || 0;
        if (usedSet.has(item) || this.cachedBytes - removedBytes - bytes < minBytesSize && removedNodes >= nodesToUnload) {
          break;
        }
        removedBytes += bytes;
        removedNodes++;
      }
      itemList.splice(0, removedNodes).forEach((item) => {
        this.cachedBytes -= bytesMap.get(item) || 0;
        callbacks.get(item)(item);
        bytesMap.delete(item);
        itemSet.delete(item);
        callbacks.delete(item);
        loadedSet.delete(item);
        usedSet.delete(item);
      });
      needsRerun = removedNodes < excessNodes || removedBytes < excessBytes && removedNodes < unused;
      needsRerun = needsRerun && removedNodes > 0;
    }
    if (needsRerun) {
      this.unloadingHandle = Scheduler.requestAnimationFrame(() => this.scheduleUnload());
    }
  }
  /**
   * Schedules `unloadUnusedContent` to run asynchronously via microtask.
   */
  scheduleUnload() {
    Scheduler.cancelAnimationFrame(this.unloadingHandle);
    if (!this.scheduled) {
      this.scheduled = true;
      queueMicrotask(() => {
        this.scheduled = false;
        this.unloadUnusedContent();
      });
    }
  }
};

// build/core/renderer/utilities/PriorityQueue.js
var PriorityQueueItemRemovedError = class extends DOMException {
  constructor() {
    super("PriorityQueue: Item removed", "AbortError");
  }
};
var PriorityQueue = class {
  /**
   * returns whether tasks are queued or actively running
   * @readonly
   * @type {boolean}
   */
  get running() {
    return this.items.length !== 0 || this.currJobs !== 0;
  }
  constructor() {
    this.maxJobs = 6;
    this.items = [];
    this.callbacks = /* @__PURE__ */ new Map();
    this.currJobs = 0;
    this.scheduled = false;
    this.autoUpdate = true;
    this.priorityCallback = null;
    this._schedulingCallback = (func) => {
      Scheduler.requestAnimationFrame(func);
    };
    this._runjobs = () => {
      this.scheduled = false;
      this.tryRunJobs();
    };
  }
  /**
   * Sorts the pending item list using `priorityCallback`, if set.
   */
  sort() {
    const priorityCallback = this.priorityCallback;
    const items = this.items;
    if (priorityCallback !== null) {
      items.sort(priorityCallback);
    }
  }
  /**
   * Returns whether the given item is currently queued.
   * @param {any} item
   * @returns {boolean}
   */
  has(item) {
    return this.callbacks.has(item);
  }
  /**
   * Adds an item to the queue and returns a Promise that resolves when the item's
   * callback completes, or rejects if the item is removed before running.
   * @param {any} item
   * @param {ItemCallback} callback - Invoked with `item` when it is dequeued; may return a Promise
   * @returns {Promise<any>}
   */
  add(item, callback) {
    const data = {
      callback,
      reject: null,
      resolve: null,
      promise: null
    };
    data.promise = new Promise((resolve, reject) => {
      const items = this.items;
      const callbacks = this.callbacks;
      data.resolve = resolve;
      data.reject = reject;
      items.unshift(item);
      callbacks.set(item, data);
      if (this.autoUpdate) {
        this.scheduleJobRun();
      }
    });
    return data.promise;
  }
  /**
   * Removes an item from the queue, rejecting its promise with an `AbortError` DOMException.
   * @param {any} item
   */
  remove(item) {
    const items = this.items;
    const callbacks = this.callbacks;
    const index = items.indexOf(item);
    if (index !== -1) {
      const info = callbacks.get(item);
      info.promise.catch((err) => {
        if (err.name !== "AbortError") {
          throw err;
        }
      });
      info.reject(new PriorityQueueItemRemovedError());
      items.splice(index, 1);
      callbacks.delete(item);
    }
  }
  /**
   * Removes all queued items for which `filter` returns true.
   * @param {FilterCallback} filter - Called with each item; return true to remove
   */
  removeByFilter(filter) {
    const { items } = this;
    for (let i = 0; i < items.length; i++) {
      const item = items[i];
      if (filter(item)) {
        this.remove(item);
        i--;
      }
    }
  }
  /**
   * Immediately attempts to dequeue and run pending jobs up to `maxJobs` concurrency.
   */
  tryRunJobs() {
    this.sort();
    const items = this.items;
    const callbacks = this.callbacks;
    const maxJobs = this.maxJobs;
    let iterated = 0;
    const completedCallback = () => {
      this.currJobs--;
      if (this.autoUpdate) {
        this.scheduleJobRun();
      }
    };
    while (maxJobs > this.currJobs && items.length > 0 && iterated < maxJobs) {
      this.currJobs++;
      iterated++;
      const item = items.pop();
      const { callback, resolve, reject } = callbacks.get(item);
      callbacks.delete(item);
      let result;
      try {
        result = callback(item);
      } catch (err) {
        reject(err);
        completedCallback();
      }
      if (result instanceof Promise) {
        result.then(resolve).catch(reject).finally(completedCallback);
      } else {
        resolve(result);
        completedCallback();
      }
    }
  }
  /**
   * Immediately runs the callback for the given item, removing it from the queue.
   * Does nothing if the item is not queued.
   * @param {any} item
   * @returns {Promise<any>|any}
   */
  flush(item) {
    const { items, callbacks } = this;
    const index = items.indexOf(item);
    if (!callbacks.has(item)) {
      return;
    }
    const { callback, resolve, reject } = callbacks.get(item);
    callbacks.delete(item);
    items.splice(index, 1);
    let result;
    try {
      result = callback(item);
    } catch (err) {
      reject(err);
      return;
    }
    if (result instanceof Promise) {
      result.then(resolve).catch(reject);
    } else {
      resolve(result);
    }
    return result;
  }
  /**
   * Schedules a deferred call to `tryRunJobs` via `schedulingCallback`.
   */
  scheduleJobRun() {
    if (!this.scheduled) {
      this._schedulingCallback(this._runjobs);
      this.scheduled = true;
    }
  }
};

// build/core/renderer/constants.js
var FAILED = -1;
var UNLOADED = 0;
var QUEUED = 1;
var LOADING = 2;
var PARSING = 3;
var LOADED = 4;
var WGS84_RADIUS = 6378137;
var WGS84_FLATTENING = 1 / 298.257223563;
var WGS84_HEIGHT = -(WGS84_FLATTENING * WGS84_RADIUS - WGS84_RADIUS);

// build/core/renderer/tiles/traverseFunctions.js
var viewErrorTarget = {
  inView: false,
  error: Infinity,
  distanceFromCamera: Infinity
};
function isDownloadFinished(value) {
  return value === LOADED || value === FAILED;
}
function isUsedThisFrame(tile, frameCount) {
  return isProcessed(tile) && tile.traversal.lastFrameVisited === frameCount && tile.traversal.used;
}
function isProcessed(tile) {
  return Boolean(tile.traversal);
}
function areChildrenProcessed(tile) {
  const { children } = tile;
  const childrenReady = children.length === 0 || isProcessed(children[children.length - 1]);
  const contentReady = !tile.internal.hasUnrenderableContent || isDownloadFinished(tile.internal.loadingState);
  return childrenReady && contentReady;
}
function canUnconditionallyRefine(tile) {
  return tile.traversal.unconditionallyRefine;
}
function resetFrameState(tile, renderer) {
  if (!isProcessed(tile)) {
    return;
  }
  renderer.ensureChildrenArePreprocessed(tile);
  if (tile.traversal.lastFrameVisited !== renderer.frameCount) {
    tile.traversal.wasInFrustum = tile.traversal.inFrustum;
    tile.traversal.wasSetActive = tile.traversal.active;
    tile.traversal.wasSetVisible = tile.traversal.visible;
    tile.traversal.usedLastFrame = tile.traversal.used;
    tile.traversal.lastFrameVisited = renderer.frameCount;
    tile.traversal.used = false;
    tile.traversal.inFrustum = false;
    tile.traversal.isLeaf = false;
    tile.traversal.visible = false;
    tile.traversal.active = false;
    tile.traversal.error = Infinity;
    tile.traversal.distanceFromCamera = Infinity;
    tile.traversal.allChildrenReady = false;
    tile.traversal.allChildrenLoaded = false;
    tile.traversal.kicked = false;
    tile.traversal.allUsedChildrenProcessed = false;
    renderer.calculateTileViewErrorWithPlugin(tile, viewErrorTarget);
    tile.traversal.inFrustum = viewErrorTarget.inView;
    tile.traversal.error = viewErrorTarget.error;
    tile.traversal.distanceFromCamera = viewErrorTarget.distanceFromCamera;
    tile.traversal.unconditionallyRefine = tile.internal.hasUnrenderableContent;
    if (!tile.traversal.unconditionallyRefine) {
      let nearestConditionalParent = tile.parent;
      while (nearestConditionalParent && nearestConditionalParent.traversal.unconditionallyRefine) {
        nearestConditionalParent = nearestConditionalParent.parent;
      }
      if (nearestConditionalParent && nearestConditionalParent.geometricError <= tile.geometricError) {
        tile.traversal.unconditionallyRefine = true;
      }
    }
  }
}
function recursivelyMarkUsed(tile, renderer, cacheOnly = false) {
  resetFrameState(tile, renderer);
  if (cacheOnly) {
    renderer.markTileUsed(tile);
  } else {
    markUsed(tile);
  }
  if (canUnconditionallyRefine(tile) && areChildrenProcessed(tile)) {
    const children = tile.children;
    for (let i = 0, l = children.length; i < l; i++) {
      recursivelyMarkUsed(children[i], renderer, cacheOnly);
    }
  }
}
function recursivelyMarkPreviouslyUsed(tile, renderer) {
  resetFrameState(tile, renderer);
  if (tile.traversal.usedLastFrame) {
    markUsed(tile);
    if (tile.traversal.wasSetActive) {
      tile.traversal.active = true;
    }
    if (!tile.traversal.active || canUnconditionallyRefine(tile)) {
      if (areChildrenProcessed(tile)) {
        const children = tile.children;
        for (let i = 0, l = children.length; i < l; i++) {
          recursivelyMarkPreviouslyUsed(children[i], renderer);
        }
      }
    }
  }
}
function markUsed(tile) {
  tile.traversal.used = true;
}
function canTraverse(tile, renderer) {
  if (tile.traversal.error <= renderer.errorTarget && !canUnconditionallyRefine(tile)) {
    return false;
  }
  if (renderer.maxDepth > 0 && tile.internal.depth + 1 >= renderer.maxDepth) {
    return false;
  }
  if (!areChildrenProcessed(tile)) {
    return false;
  }
  return true;
}
function kickActiveChildren(tile, renderer) {
  const { frameCount } = renderer;
  const { children } = tile;
  for (let i = 0, l = children.length; i < l; i++) {
    const c = children[i];
    if (isUsedThisFrame(c, frameCount)) {
      if (c.traversal.active) {
        c.traversal.kicked = true;
        c.traversal.active = false;
      }
      kickActiveChildren(c, renderer);
    }
  }
}
function isChildReady(tile) {
  return !canUnconditionallyRefine(tile) && (!tile.internal.hasContent || isDownloadFinished(tile.internal.loadingState));
}
function markUsedTiles(tile, renderer) {
  resetFrameState(tile, renderer);
  if (!tile.traversal.inFrustum) {
    return;
  }
  if (!canTraverse(tile, renderer)) {
    markUsed(tile);
    return;
  }
  let anyChildrenUsed = false;
  let anyChildrenInFrustum = false;
  const children = tile.children;
  for (let i = 0, l = children.length; i < l; i++) {
    const c = children[i];
    markUsedTiles(c, renderer);
    anyChildrenUsed = anyChildrenUsed || isUsedThisFrame(c, renderer.frameCount);
    anyChildrenInFrustum = anyChildrenInFrustum || c.traversal.inFrustum;
  }
  if (tile.refine === "REPLACE" && !anyChildrenInFrustum && children.length !== 0) {
    tile.traversal.inFrustum = false;
    renderer.markTileUsed(tile);
    for (let i = 0, l = children.length; i < l; i++) {
      recursivelyMarkUsed(children[i], renderer, true);
    }
    return;
  }
  markUsed(tile);
  if (tile.refine === "REPLACE" && anyChildrenUsed && (renderer.loadSiblings || renderer.loadAncestors)) {
    for (let i = 0, l = children.length; i < l; i++) {
      recursivelyMarkUsed(children[i], renderer);
    }
  }
}
function markUsedSetLeaves(tile, renderer) {
  const frameCount = renderer.frameCount;
  if (!isUsedThisFrame(tile, frameCount)) {
    return;
  }
  const children = tile.children;
  let anyChildrenUsed = false;
  for (let i = 0, l = children.length; i < l; i++) {
    const c = children[i];
    anyChildrenUsed = anyChildrenUsed || isUsedThisFrame(c, frameCount);
  }
  if (!anyChildrenUsed) {
    tile.traversal.isLeaf = true;
  } else {
    for (let i = 0, l = children.length; i < l; i++) {
      markUsedSetLeaves(children[i], renderer);
    }
    let allChildrenLoaded = true;
    for (let i = 0, l = children.length; i < l; i++) {
      const c = children[i];
      if (isUsedThisFrame(c, frameCount)) {
        const childCanDisplay = !canUnconditionallyRefine(c);
        const childContentReady = !c.internal.hasContent || isDownloadFinished(c.internal.loadingState);
        const childIsReady = childCanDisplay && childContentReady || c.traversal.allChildrenLoaded;
        if (!childIsReady) {
          allChildrenLoaded = false;
        }
      }
    }
    tile.traversal.allChildrenLoaded = allChildrenLoaded;
  }
  let allUsedChildrenProcessed = true;
  for (let i = 0, l = children.length; i < l; i++) {
    const c = children[i];
    if (isUsedThisFrame(c, renderer.frameCount) && !c.traversal.allUsedChildrenProcessed) {
      allUsedChildrenProcessed = false;
    }
  }
  tile.traversal.allUsedChildrenProcessed = allUsedChildrenProcessed && areChildrenProcessed(tile);
}
function markVisibleTiles(tile, renderer) {
  if (!isUsedThisFrame(tile, renderer.frameCount)) {
    return;
  }
  const children = tile.children;
  if (renderer.loadAncestors && !tile.traversal.allChildrenLoaded && !canUnconditionallyRefine(tile)) {
    tile.traversal.isLeaf = true;
  }
  if (tile.traversal.isLeaf) {
    if (!canUnconditionallyRefine(tile)) {
      tile.traversal.active = true;
      if (areChildrenProcessed(tile) && tile.internal.hasContent && !isDownloadFinished(tile.internal.loadingState)) {
        for (let i = 0, l = children.length; i < l; i++) {
          recursivelyMarkPreviouslyUsed(children[i], renderer);
        }
      }
    }
    return;
  }
  let allChildrenReady = children.length > 0;
  for (let i = 0, l = children.length; i < l; i++) {
    const c = children[i];
    markVisibleTiles(c, renderer);
    if (isUsedThisFrame(c, renderer.frameCount)) {
      const childIsReady = c.traversal.active && isChildReady(c);
      if (!childIsReady && !c.traversal.allChildrenReady) {
        allChildrenReady = false;
      }
    }
  }
  tile.traversal.allChildrenReady = allChildrenReady;
  if (!allChildrenReady && tile.traversal.wasSetActive && isChildReady(tile)) {
    tile.traversal.active = true;
    kickActiveChildren(tile, renderer);
  }
}
function toggleTiles(tile, renderer) {
  resetFrameState(tile, renderer);
  const isUsed = isUsedThisFrame(tile, renderer.frameCount);
  if (isUsed) {
    if (tile.internal.hasUnrenderableContent) {
      renderer.markTileUsed(tile);
      renderer.queueTileForDownload(tile);
    }
    if (tile.internal.hasRenderableContent && tile.refine === "ADD") {
      tile.traversal.active = true;
    }
    if ((tile.traversal.active || tile.traversal.kicked) && tile.internal.hasContent) {
      renderer.markTileUsed(tile);
      if (tile.traversal.allUsedChildrenProcessed) {
        renderer.queueTileForDownload(tile);
      }
      if (tile.internal.loadingState !== LOADED) {
        tile.traversal.active = false;
      }
    }
    if (renderer.loadAncestors && tile.internal.hasContent) {
      renderer.markTileUsed(tile);
      renderer.queueTileForDownload(tile);
    }
    if (tile.internal.virtualChildCount > 0 && tile.internal.hasContent) {
      renderer.markTileUsed(tile);
    }
    tile.traversal.visible = tile.internal.hasRenderableContent && tile.traversal.active && tile.traversal.inFrustum && tile.internal.loadingState === LOADED;
    renderer.stats.used++;
    if (tile.traversal.inFrustum) {
      renderer.stats.inFrustum++;
    }
  }
  if (isUsed || isProcessed(tile) && tile.traversal.usedLastFrame) {
    let setActive = false;
    let setVisible = false;
    if (isUsed) {
      setActive = tile.traversal.active;
      if (renderer.displayActiveTiles) {
        setVisible = tile.traversal.active || tile.traversal.visible;
      } else {
        setVisible = tile.traversal.visible;
      }
    } else {
      resetFrameState(tile, renderer);
    }
    if (tile.internal.hasRenderableContent && tile.internal.loadingState === LOADED) {
      if (setActive) {
        renderer.stats.active++;
      }
      if (setVisible) {
        renderer.stats.visible++;
      }
      if (tile.traversal.wasSetActive !== setActive) {
        renderer.invokeOnePlugin((plugin) => plugin.setTileActive && plugin.setTileActive(tile, setActive));
      }
      if (tile.traversal.wasSetVisible !== setVisible) {
        renderer.invokeOnePlugin((plugin) => plugin.setTileVisible && plugin.setTileVisible(tile, setVisible));
      }
    } else if (!tile.internal.hasRenderableContent) {
      setVisible = tile.traversal.isLeaf;
      if (tile.traversal.wasSetVisible !== setVisible) {
        renderer.invokeOnePlugin((plugin) => plugin.setEmptyTileVisible && plugin.setEmptyTileVisible(tile, setVisible));
      }
    }
    tile.traversal.visible = setVisible;
    tile.traversal.active = setActive;
    const children = tile.children;
    for (let i = 0, l = children.length; i < l; i++) {
      const c = children[i];
      toggleTiles(c, renderer);
    }
  }
}
function runTraversal(tile, renderer) {
  markUsedTiles(tile, renderer);
  markUsedSetLeaves(tile, renderer);
  markVisibleTiles(tile, renderer);
  toggleTiles(tile, renderer);
}

// build/core/renderer/utilities/throttle.js
function throttle(callback) {
  let handle = null;
  return () => {
    if (handle === null) {
      handle = Scheduler.requestAnimationFrame(() => {
        handle = null;
        callback();
      });
    }
  };
}

// build/core/renderer/tiles/TilesRendererBase.js
var PLUGIN_REGISTERED = /* @__PURE__ */ Symbol("PLUGIN_REGISTERED");
var regionErrorTarget = {
  inView: true,
  error: 0,
  distance: Infinity
};
var errorPriorityCallback = (a, b) => {
  const aPriority = a.priority || 0;
  const bPriority = b.priority || 0;
  if (aPriority !== bPriority) {
    return aPriority > bPriority ? 1 : -1;
  } else if (!a.traversal || !b.traversal) {
    return 0;
  } else if (a.traversal.used !== b.traversal.used) {
    return a.traversal.used ? 1 : -1;
  } else if (a.traversal.error !== b.traversal.error) {
    return a.traversal.error > b.traversal.error ? 1 : -1;
  } else if (a.traversal.distanceFromCamera !== b.traversal.distanceFromCamera) {
    return a.traversal.distanceFromCamera > b.traversal.distanceFromCamera ? -1 : 1;
  } else if (a.internal.depthFromRenderedParent !== b.internal.depthFromRenderedParent) {
    return a.internal.depthFromRenderedParent > b.internal.depthFromRenderedParent ? -1 : 1;
  }
  return 0;
};
var distancePriorityCallback = (a, b) => {
  if (a.traversal.used !== b.traversal.used) {
    return a.traversal.used ? 1 : -1;
  } else if (a.traversal.inFrustum !== b.traversal.inFrustum) {
    return a.traversal.inFrustum ? 1 : -1;
  } else if (a.internal.hasUnrenderableContent !== b.internal.hasUnrenderableContent) {
    return a.internal.hasUnrenderableContent ? 1 : -1;
  } else if (a.traversal.distanceFromCamera !== b.traversal.distanceFromCamera) {
    return a.traversal.distanceFromCamera > b.traversal.distanceFromCamera ? -1 : 1;
  } else if (a.internal.depthFromRenderedParent !== b.internal.depthFromRenderedParent) {
    return a.internal.depthFromRenderedParent > b.internal.depthFromRenderedParent ? -1 : 1;
  }
  return 0;
};
var lruPriorityCallback = (a, b) => {
  if (a.traversal.lastFrameVisited !== b.traversal.lastFrameVisited) {
    return a.traversal.lastFrameVisited > b.traversal.lastFrameVisited ? -1 : 1;
  } else if (a.internal.depthFromRenderedParent !== b.internal.depthFromRenderedParent) {
    return a.internal.depthFromRenderedParent > b.internal.depthFromRenderedParent ? 1 : -1;
  } else if (a.internal.loadingState !== b.internal.loadingState) {
    return a.internal.loadingState > b.internal.loadingState ? -1 : 1;
  } else if (a.internal.hasUnrenderableContent !== b.internal.hasUnrenderableContent) {
    return a.internal.hasUnrenderableContent ? -1 : 1;
  } else if (a.traversal.error !== b.traversal.error) {
    return a.traversal.error > b.traversal.error ? -1 : 1;
  }
  return 0;
};
var unifiedPriorityCallback = (a, b) => {
  const aPriority = a.priority ?? Infinity;
  const bPriority = b.priority ?? Infinity;
  if (aPriority !== bPriority) {
    return aPriority > bPriority ? 1 : -1;
  } else if (!a.internal || !b.internal) {
    return 0;
  }
  const aRenderer = a.internal.renderer;
  const bRenderer = b.internal.renderer;
  const aOptimized = !aRenderer.loadAncestors;
  const bOptimized = !bRenderer.loadAncestors;
  if (aOptimized && bOptimized) {
    return distancePriorityCallback(a, b);
  } else {
    return errorPriorityCallback(a, b);
  }
};
var DEFAULT_LRU_CACHE = new LRUCache();
DEFAULT_LRU_CACHE.unloadPriorityCallback = lruPriorityCallback;
var DEFAULT_DOWNLOAD_QUEUE = new PriorityQueue();
DEFAULT_DOWNLOAD_QUEUE.maxJobs = 25;
DEFAULT_DOWNLOAD_QUEUE.priorityCallback = unifiedPriorityCallback;
var DEFAULT_PARSE_QUEUE = new PriorityQueue();
DEFAULT_PARSE_QUEUE.maxJobs = 5;
DEFAULT_PARSE_QUEUE.priorityCallback = unifiedPriorityCallback;
var DEFAULT_NODE_QUEUE = new PriorityQueue();
DEFAULT_NODE_QUEUE.maxJobs = 25;
DEFAULT_NODE_QUEUE.priorityCallback = (a, b) => {
  const aParent = a.parent;
  const bParent = b.parent;
  if (aParent === bParent) {
    return 0;
  } else if (!aParent) {
    return 1;
  } else if (!bParent) {
    return -1;
  } else {
    return unifiedPriorityCallback(aParent, bParent);
  }
};
var TilesRendererBase = class {
  /**
   * Root tile of the loaded root tileset, or null if not yet loaded.
   * @type {Tile|null}
   * @readonly
   */
  get root() {
    const tileset = this.rootTileset;
    return tileset ? tileset.root : null;
  }
  /**
   * Fraction of tiles loaded since the last idle state, from 0 (nothing loaded) to 1 (all loaded).
   * @type {number}
   * @readonly
   */
  get loadProgress() {
    const { stats, isLoading } = this;
    const loading = stats.queued + stats.downloading + stats.parsing;
    const total = stats.inCacheSinceLoad + (isLoading ? 1 : 0);
    return total === 0 ? 1 : 1 - loading / total;
  }
  /**
   * @param {string} [url] - URL of the root tileset JSON to load.
   */
  constructor(url = null) {
    this.rootLoadingState = UNLOADED;
    this.rootTileset = null;
    this.rootURL = url;
    this.fetchOptions = {};
    this.plugins = [];
    this.queuedTiles = [];
    this.cachedSinceLoadComplete = /* @__PURE__ */ new Set();
    this.isLoading = false;
    this.processedTiles = /* @__PURE__ */ new WeakSet();
    this.visibleTiles = /* @__PURE__ */ new Set();
    this.activeTiles = /* @__PURE__ */ new Set();
    this.usedSet = /* @__PURE__ */ new Set();
    this.loadingTiles = /* @__PURE__ */ new Set();
    this.lruCache = DEFAULT_LRU_CACHE;
    this.downloadQueue = DEFAULT_DOWNLOAD_QUEUE;
    this.parseQueue = DEFAULT_PARSE_QUEUE;
    this.processNodeQueue = DEFAULT_NODE_QUEUE;
    this.stats = {
      inCacheSinceLoad: 0,
      inCache: 0,
      queued: 0,
      downloading: 0,
      parsing: 0,
      loaded: 0,
      failed: 0,
      inFrustum: 0,
      used: 0,
      active: 0,
      visible: 0,
      tilesProcessed: 0
    };
    this.frameCount = 0;
    this._dispatchNeedsUpdateEvent = throttle(() => {
      this.dispatchEvent({ type: "needs-update" });
    });
    this.errorTarget = 16;
    this.displayActiveTiles = false;
    this.maxDepth = Infinity;
    this.loadSiblings = true;
    this.loadAncestors = true;
    this.maxTilesProcessed = 250;
  }
  // Plugins
  /**
   * Registers a plugin with this renderer. Plugins are inserted in priority order and
   * receive lifecycle callbacks throughout the tile loading and rendering process.
   * A plugin instance may only be registered to one renderer at a time.
   * @param {Object} plugin
   */
  registerPlugin(plugin) {
    if (plugin[PLUGIN_REGISTERED] === true) {
      throw new Error("TilesRendererBase: A plugin can only be registered to a single tileset");
    }
    const plugins = this.plugins;
    const priority = plugin.priority || 0;
    let insertionPoint = plugins.length;
    for (let i = 0; i < plugins.length; i++) {
      const otherPriority = plugins[i].priority || 0;
      if (otherPriority > priority) {
        insertionPoint = i;
        break;
      }
    }
    plugins.splice(insertionPoint, 0, plugin);
    plugin[PLUGIN_REGISTERED] = true;
    if (plugin.init) {
      plugin.init(this);
    }
  }
  /**
   * Removes a registered plugin. Calls `plugin.dispose()` if defined.
   * Accepts either the plugin instance or its string name.
   * Returns true if the plugin was found and removed.
   * @param {Object|string} plugin
   * @returns {boolean}
   */
  unregisterPlugin(plugin) {
    const plugins = this.plugins;
    if (typeof plugin === "string") {
      plugin = this.getPluginByName(plugin);
    }
    if (plugins.includes(plugin)) {
      const index = plugins.indexOf(plugin);
      plugins.splice(index, 1);
      if (plugin.dispose) {
        plugin.dispose();
      }
      return true;
    }
    return false;
  }
  /**
   * Returns the first registered plugin whose `name` property matches, or null.
   * @param {string} name
   * @returns {Object|null}
   */
  getPluginByName(name) {
    return this.plugins.find((p) => p.name === name) || null;
  }
  invokeOnePlugin(func) {
    const plugins = [...this.plugins, this];
    for (let i = 0; i < plugins.length; i++) {
      const result = func(plugins[i]);
      if (result) {
        return result;
      }
    }
    return null;
  }
  invokeAllPlugins(func) {
    const plugins = [...this.plugins, this];
    const pending = [];
    for (let i = 0; i < plugins.length; i++) {
      const result = func(plugins[i]);
      if (result) {
        pending.push(result);
      }
    }
    return pending.length === 0 ? null : Promise.all(pending);
  }
  // Public API
  /**
   * Iterates over all tiles in the loaded hierarchy. `beforecb` is called before
   * descending into a tile's children; returning true from it skips the subtree.
   * `aftercb` is called after all children have been visited.
   * @param {TileBeforeCallback|null} [beforecb]
   * @param {TileAfterCallback|null} [aftercb]
   */
  traverse(beforecb, aftercb, ensureFullyProcessed = true) {
    if (!this.root) return;
    traverseSet(this.root, (tile, ...args) => {
      if (ensureFullyProcessed) {
        this.ensureChildrenArePreprocessed(tile, true);
      }
      return beforecb ? beforecb(tile, ...args) : false;
    }, aftercb);
  }
  /**
   * Collects attribution data from all registered plugins into `target` and returns it.
   * @param {Array<{type: string, value: any}>} [target]
   * @returns {Array<{type: string, value: any}>}
   */
  getAttributions(target = []) {
    this.invokeAllPlugins((plugin) => plugin !== this && plugin.getAttributions && plugin.getAttributions(target));
    return target;
  }
  /**
   * Runs the tile traversal and update loop. Should be called once per frame after
   * camera matrices have been updated. Triggers tile loading, visibility updates,
   * and LRU cache eviction.
   */
  update() {
    const { lruCache, usedSet, stats, root, downloadQueue, parseQueue, processNodeQueue } = this;
    if (this.rootLoadingState === UNLOADED) {
      this.rootLoadingState = LOADING;
      this.invokeOnePlugin((plugin) => plugin.loadRootTileset && plugin.loadRootTileset()).then((root2) => {
        let processedUrl = this.rootURL;
        if (processedUrl !== null) {
          this.invokeAllPlugins((plugin) => processedUrl = plugin.preprocessURL ? plugin.preprocessURL(processedUrl, null) : processedUrl);
        }
        this.rootLoadingState = LOADED;
        this.rootTileset = root2;
        this.dispatchEvent({ type: "needs-update" });
        this.dispatchEvent({
          type: "load-tileset",
          tileset: root2,
          url: processedUrl
        });
        this.dispatchEvent({
          type: "load-root-tileset",
          tileset: root2,
          url: processedUrl
        });
      }).catch((error) => {
        this.rootLoadingState = FAILED;
        console.error(error);
        this.rootTileset = null;
        this.dispatchEvent({
          type: "load-error",
          tile: null,
          error,
          url: this.rootURL
        });
      });
    }
    if (!root) {
      return;
    }
    let needsUpdate = null;
    this.invokeAllPlugins((plugin) => {
      if (plugin.doTilesNeedUpdate) {
        const res = plugin.doTilesNeedUpdate();
        if (needsUpdate === null) {
          needsUpdate = res;
        } else {
          needsUpdate = Boolean(needsUpdate || res);
        }
      }
    });
    if (needsUpdate === false) {
      this.dispatchEvent({ type: "update-before" });
      this.dispatchEvent({ type: "update-after" });
      return;
    }
    this.dispatchEvent({ type: "update-before" });
    stats.inFrustum = 0;
    stats.used = 0;
    stats.active = 0;
    stats.visible = 0;
    stats.tilesProcessed = 0;
    this.frameCount++;
    usedSet.forEach((tile) => lruCache.markUnused(tile));
    usedSet.clear();
    this.prepareForTraversal();
    runTraversal(root, this);
    this.removeUnusedPendingTiles();
    const queuedTiles = this.queuedTiles;
    queuedTiles.sort(lruCache.unloadPriorityCallback);
    for (let i = 0, l = queuedTiles.length; i < l && !lruCache.isFull(); i++) {
      this.requestTileContents(queuedTiles[i]);
    }
    queuedTiles.length = 0;
    lruCache.scheduleUnload();
    const runningTasks = downloadQueue.running || parseQueue.running || processNodeQueue.running;
    if (runningTasks === false && this.isLoading === true) {
      this.cachedSinceLoadComplete.clear();
      stats.inCacheSinceLoad = 0;
      this.dispatchEvent({ type: "tiles-load-end" });
      this.isLoading = false;
    }
    this.dispatchEvent({ type: "update-after" });
  }
  /**
   * Resets any tiles that previously failed to load so they will be retried on the next `update`.
   */
  resetFailedTiles() {
    if (this.rootLoadingState === FAILED) {
      this.rootLoadingState = UNLOADED;
    }
    const stats = this.stats;
    if (stats.failed === 0) {
      return;
    }
    this.traverse((tile) => {
      if (tile.internal.loadingState === FAILED) {
        tile.internal.loadingState = UNLOADED;
      }
    }, null, false);
    stats.failed = 0;
  }
  calculateTileViewErrorWithPlugin(tile, target) {
    this.calculateTileViewError(tile, target);
    let inRegion = null;
    let inRegionError = 0;
    let inRegionDistance = Infinity;
    this.invokeAllPlugins((plugin) => {
      if (plugin !== this && plugin.calculateTileViewError) {
        regionErrorTarget.inView = true;
        regionErrorTarget.error = 0;
        regionErrorTarget.distance = Infinity;
        if (plugin.calculateTileViewError(tile, regionErrorTarget)) {
          if (inRegion === null) {
            inRegion = true;
          }
          inRegion = inRegion && regionErrorTarget.inView;
          if (regionErrorTarget.inView) {
            inRegionDistance = Math.min(inRegionDistance, regionErrorTarget.distance);
            inRegionError = Math.max(inRegionError, regionErrorTarget.error);
          }
        }
      }
    });
    if (target.inView && inRegion !== false) {
      target.error = Math.max(target.error, inRegionError);
      target.distanceFromCamera = Math.min(target.distanceFromCamera, inRegionDistance);
    } else if (inRegion) {
      target.inView = true;
      target.error = inRegionError;
      target.distanceFromCamera = inRegionDistance;
    } else {
      target.inView = false;
    }
  }
  /**
   * Disposes all loaded tiles and unregisters all plugins. The renderer should not
   * be used after calling this.
   */
  dispose() {
    const plugins = [...this.plugins];
    plugins.forEach((plugin) => {
      this.unregisterPlugin(plugin);
    });
    const lruCache = this.lruCache;
    const toRemove = [];
    this.traverse((t) => {
      toRemove.push(t);
      return false;
    }, null, false);
    for (let i = 0, l = toRemove.length; i < l; i++) {
      lruCache.remove(toRemove[i]);
    }
    this.stats = {
      queued: 0,
      parsing: 0,
      downloading: 0,
      failed: 0,
      inFrustum: 0,
      traversed: 0,
      used: 0,
      active: 0,
      visible: 0
    };
    this.frameCount = 0;
    this.loadingTiles.clear();
  }
  // Overrideable
  calculateBytesUsed(scene, tile) {
    return 0;
  }
  /**
   * Dispatches an event to all registered listeners for the given event type.
   * @param {{ type: string }} e
   */
  dispatchEvent(e) {
  }
  /**
   * Registers a listener for the given event type.
   * @param {string} name
   * @param {EventCallback} callback
   */
  addEventListener(name, callback) {
  }
  /**
   * Removes a previously registered event listener.
   * @param {string} name
   * @param {EventCallback} callback
   */
  removeEventListener(name, callback) {
  }
  parseTile(buffer, tile, extension) {
    return null;
  }
  prepareForTraversal() {
  }
  disposeTile(tile) {
    if (tile.traversal.visible) {
      if (tile.internal.hasRenderableContent) {
        this.invokeOnePlugin((plugin) => plugin.setTileVisible && plugin.setTileVisible(tile, false));
      } else {
        this.invokeOnePlugin((plugin) => plugin.setEmptyTileVisible && plugin.setEmptyTileVisible(tile, false));
      }
      tile.traversal.visible = false;
    }
    if (tile.traversal.active && tile.internal.hasRenderableContent) {
      this.invokeOnePlugin((plugin) => plugin.setTileActive && plugin.setTileActive(tile, false));
    }
    tile.traversal.active = false;
    const { scene } = tile.engineData;
    if (scene) {
      this.dispatchEvent({
        type: "dispose-model",
        scene,
        tile
      });
    }
  }
  preprocessNode(tile, tilesetDir, parentTile = null) {
    this.processedTiles.add(tile);
    this.stats.tilesProcessed++;
    if (tile.content) {
      if (!("uri" in tile.content) && "url" in tile.content) {
        tile.content.uri = tile.content.url;
        delete tile.content.url;
      }
      if (tile.content.boundingVolume && !("box" in tile.content.boundingVolume || "sphere" in tile.content.boundingVolume || "region" in tile.content.boundingVolume)) {
        delete tile.content.boundingVolume;
      }
    }
    tile.parent = parentTile;
    tile.children = tile.children || [];
    tile.internal = {
      hasContent: false,
      hasRenderableContent: false,
      hasUnrenderableContent: false,
      loadingState: UNLOADED,
      basePath: tilesetDir,
      depth: -1,
      depthFromRenderedParent: -1,
      isVirtual: false,
      virtualChildCount: 0,
      renderer: this,
      // preserve any pre-seeded fields
      ...tile.internal
    };
    if (tile.content?.uri) {
      const extension = getUrlExtension(tile.content.uri);
      const hasUnrenderableContent = Boolean(extension && /json$/.test(extension));
      tile.internal.hasContent = true;
      tile.internal.hasUnrenderableContent = hasUnrenderableContent;
      tile.internal.hasRenderableContent = !hasUnrenderableContent;
    } else {
      tile.internal.hasContent = false;
      tile.internal.hasUnrenderableContent = false;
      tile.internal.hasRenderableContent = false;
    }
    if (parentTile) {
      tile.internal.depth = parentTile.internal.depth + 1;
      tile.internal.depthFromRenderedParent = parentTile.internal.depthFromRenderedParent + (tile.internal.hasRenderableContent ? 1 : 0);
    } else {
      tile.internal.depth = 0;
      tile.internal.depthFromRenderedParent = tile.internal.hasRenderableContent ? 1 : 0;
    }
    tile.traversal = {
      distanceFromCamera: Infinity,
      error: Infinity,
      inFrustum: false,
      wasInFrustum: false,
      isLeaf: false,
      used: false,
      usedLastFrame: false,
      visible: false,
      wasSetVisible: false,
      active: false,
      wasSetActive: false,
      allChildrenReady: false,
      allChildrenLoaded: false,
      kicked: false,
      allUsedChildrenProcessed: false,
      lastFrameVisited: -1
    };
    if (parentTile === null) {
      tile.refine = tile.refine || "REPLACE";
    } else {
      tile.refine = tile.refine || parentTile.refine;
    }
    tile.engineData = {
      scene: null,
      metadata: null,
      boundingVolume: null
    };
    Object.defineProperty(tile, "cached", {
      get() {
        console.warn('TilesRenderer: "tile.cached" field has been renamed to "tile.engineData".');
        return this.engineData;
      },
      enumerable: false,
      configurable: true
    });
    this.invokeAllPlugins((plugin) => {
      plugin !== this && plugin.preprocessNode && plugin.preprocessNode(tile, tilesetDir, parentTile);
    });
  }
  setTileActive(tile, active) {
    active ? this.activeTiles.add(tile) : this.activeTiles.delete(tile);
  }
  setTileVisible(tile, visible) {
    visible ? this.visibleTiles.add(tile) : this.visibleTiles.delete(tile);
    this.dispatchEvent({
      type: "tile-visibility-change",
      scene: tile.engineData.scene,
      tile,
      visible
    });
  }
  calculateTileViewError(tile, target) {
  }
  removeUnusedPendingTiles() {
    const { lruCache, loadingTiles } = this;
    const toRemove = [];
    for (const tile of loadingTiles) {
      if (!lruCache.isUsed(tile) && tile.internal.loadingState === QUEUED) {
        toRemove.push(tile);
      }
    }
    for (let i = 0; i < toRemove.length; i++) {
      lruCache.remove(toRemove[i]);
    }
  }
  // Private Functions
  queueTileForDownload(tile) {
    if (tile.internal.loadingState !== UNLOADED || this.lruCache.isFull()) {
      return;
    }
    this.queuedTiles.push(tile);
  }
  markTileUsed(tile) {
    this.usedSet.add(tile);
    this.lruCache.markUsed(tile);
  }
  fetchData(url, options) {
    return fetch(url, options);
  }
  ensureChildrenArePreprocessed(tile, forceImmediate = this.stats.tilesProcessed < this.maxTilesProcessed) {
    const children = tile.children;
    if (children.length === 0 || children[children.length - 1].traversal) {
      return;
    }
    const processChildren = (children2) => {
      for (let i = 0, l = children2.length; i < l; i++) {
        const child = children2[i];
        if (child && !child.traversal) {
          this.preprocessNode(child, tile.internal.basePath, tile);
        }
      }
    };
    if (forceImmediate) {
      this.processNodeQueue.remove(tile);
      processChildren(children);
    } else {
      if (!this.processNodeQueue.has(tile)) {
        this.processNodeQueue.add(tile, (tile2) => {
          processChildren(tile2.children);
          this._dispatchNeedsUpdateEvent();
        });
      }
    }
  }
  // returns the total bytes used for by the given tile as reported by all plugins
  getBytesUsed(tile) {
    let bytes = 0;
    this.invokeAllPlugins((plugin) => {
      if (plugin.calculateBytesUsed) {
        bytes += plugin.calculateBytesUsed(tile, tile.engineData.scene) || 0;
      }
    });
    return bytes;
  }
  // force a recalculation of the tile or all tiles if no tile is provided
  recalculateBytesUsed(tile = null) {
    const { lruCache, processedTiles } = this;
    if (tile === null) {
      lruCache.itemSet.forEach((item) => {
        if (processedTiles.has(item)) {
          lruCache.setMemoryUsage(item, this.getBytesUsed(item));
        }
      });
    } else {
      lruCache.setMemoryUsage(tile, this.getBytesUsed(tile));
    }
  }
  preprocessTileset(json, url, parent = null) {
    const version = json.asset.version;
    const [major, minor] = version.split(".").map((v) => parseInt(v));
    console.assert(
      major <= 1,
      "TilesRenderer: asset.version is expected to be a 1.x or a compatible version."
    );
    if (major === 1 && minor > 0) {
      console.warn("TilesRenderer: tiles versions at 1.1 or higher have limited support. Some new extensions and features may not be supported.");
    }
    let basePath = url.replace(/\/[^/]*$/, "");
    basePath = new URL(basePath, window.location.href).toString();
    this.preprocessNode(json.root, basePath, parent);
  }
  loadRootTileset() {
    let processedUrl = this.rootURL;
    this.invokeAllPlugins((plugin) => processedUrl = plugin.preprocessURL ? plugin.preprocessURL(processedUrl, null) : processedUrl);
    const pr = this.invokeOnePlugin((plugin) => plugin.fetchData && plugin.fetchData(processedUrl, this.fetchOptions)).then((res) => {
      if (!(res instanceof Response)) {
        return res;
      } else if (res.ok) {
        return res.json();
      } else {
        throw new Error(`TilesRenderer: Failed to load tileset "${processedUrl}" with status ${res.status} : ${res.statusText}`);
      }
    }).then((root) => {
      this.preprocessTileset(root, processedUrl);
      return root;
    });
    return pr;
  }
  requestTileContents(tile) {
    if (tile.internal.loadingState !== UNLOADED) {
      return;
    }
    let isExternalTileset = false;
    let externalTileset = null;
    let url = new URL(tile.content.uri, tile.internal.basePath + "/").toString();
    this.invokeAllPlugins((plugin) => url = plugin.preprocessURL ? plugin.preprocessURL(url, tile) : url);
    const stats = this.stats;
    const lruCache = this.lruCache;
    const downloadQueue = this.downloadQueue;
    const parseQueue = this.parseQueue;
    const loadingTiles = this.loadingTiles;
    const extension = getUrlExtension(url);
    const controller = new AbortController();
    const signal = controller.signal;
    const addedSuccessfully = lruCache.add(tile, (t) => {
      controller.abort();
      if (isExternalTileset) {
        t.children.length = 0;
      } else {
        this.invokeAllPlugins((plugin) => {
          plugin.disposeTile && plugin.disposeTile(t);
        });
      }
      stats.inCache--;
      if (this.cachedSinceLoadComplete.has(tile)) {
        this.cachedSinceLoadComplete.delete(tile);
        stats.inCacheSinceLoad--;
      }
      if (t.internal.loadingState === QUEUED) {
        stats.queued--;
      } else if (t.internal.loadingState === LOADING) {
        stats.downloading--;
      } else if (t.internal.loadingState === PARSING) {
        stats.parsing--;
      } else if (t.internal.loadingState === LOADED) {
        stats.loaded--;
      }
      t.internal.loadingState = UNLOADED;
      parseQueue.remove(t);
      downloadQueue.remove(t);
      loadingTiles.delete(t);
    });
    if (!addedSuccessfully) {
      return;
    }
    if (!this.isLoading) {
      this.isLoading = true;
      this.dispatchEvent({ type: "tiles-load-start" });
    }
    lruCache.setMemoryUsage(tile, this.getBytesUsed(tile));
    this.cachedSinceLoadComplete.add(tile);
    stats.inCacheSinceLoad++;
    stats.inCache++;
    stats.queued++;
    tile.internal.loadingState = QUEUED;
    loadingTiles.add(tile);
    return downloadQueue.add(tile, (downloadTile) => {
      if (signal.aborted) {
        return Promise.resolve();
      }
      tile.internal.loadingState = LOADING;
      stats.downloading++;
      stats.queued--;
      const res = this.invokeOnePlugin((plugin) => plugin.fetchData && plugin.fetchData(url, { ...this.fetchOptions, signal }));
      this.dispatchEvent({
        type: "tile-download-start",
        tile,
        url,
        get uri() {
          console.warn('tile-download-start event: "uri" has been renamed to "url".');
          return this.url;
        }
      });
      return res;
    }).then((res) => {
      if (signal.aborted) {
        return;
      }
      if (!(res instanceof Response)) {
        return res;
      } else if (res.ok) {
        return extension === "json" ? res.json() : res.arrayBuffer();
      } else {
        throw new Error(`Failed to load model with error code ${res.status}`);
      }
    }).then((content) => {
      if (signal.aborted) {
        return;
      }
      stats.downloading--;
      stats.parsing++;
      tile.internal.loadingState = PARSING;
      return parseQueue.add(tile, (parseTile) => {
        if (signal.aborted) {
          return Promise.resolve();
        }
        if (extension === "json" && content.root) {
          this.preprocessTileset(content, url, tile);
          tile.children.push(content.root);
          externalTileset = content;
          isExternalTileset = true;
          return Promise.resolve();
        } else {
          return this.invokeOnePlugin((plugin) => plugin.parseTile && plugin.parseTile(content, parseTile, extension, url, signal));
        }
      });
    }).then(() => {
      if (signal.aborted) {
        return;
      }
      stats.parsing--;
      stats.loaded++;
      tile.internal.loadingState = LOADED;
      loadingTiles.delete(tile);
      lruCache.setLoaded(tile, true);
      const bytesUsed = this.getBytesUsed(tile);
      if (lruCache.getMemoryUsage(tile) === 0 && bytesUsed > 0 && lruCache.isFull()) {
        lruCache.remove(tile);
        return;
      }
      lruCache.setMemoryUsage(tile, bytesUsed);
      this.dispatchEvent({ type: "needs-update" });
      if (isExternalTileset) {
        this.dispatchEvent({
          type: "load-tileset",
          tileset: externalTileset,
          url
        });
      }
      if (tile.engineData.scene) {
        this.dispatchEvent({
          type: "load-model",
          scene: tile.engineData.scene,
          tile,
          url
        });
      }
    }).catch((error) => {
      if (signal.aborted) {
        return;
      }
      if (error.name !== "AbortError") {
        parseQueue.remove(tile);
        downloadQueue.remove(tile);
        if (tile.internal.loadingState === QUEUED) {
          stats.queued--;
        } else if (tile.internal.loadingState === LOADING) {
          stats.downloading--;
        } else if (tile.internal.loadingState === PARSING) {
          stats.parsing--;
        } else if (tile.internal.loadingState === LOADED) {
          stats.loaded--;
        }
        stats.failed++;
        console.error(`TilesRenderer : Failed to load tile at url "${tile.content.uri}".`);
        console.error(error);
        tile.internal.loadingState = FAILED;
        loadingTiles.delete(tile);
        lruCache.setLoaded(tile, true);
        this.dispatchEvent({
          type: "load-error",
          tile,
          error,
          url
        });
      } else {
        lruCache.remove(tile);
      }
    });
  }
};

// build/core/renderer/loaders/LoaderBase.js
var LoaderBase = class {
  constructor() {
    this.fetchOptions = {};
    this.workingPath = "";
  }
  /**
   * Fetches and parses content from the given URL.
   * @param {string} url
   * @returns {Promise<any>}
   */
  loadAsync(url) {
    return fetch(url, this.fetchOptions).then((res) => {
      if (!res.ok) {
        throw new Error(`Failed to load file "${url}" with status ${res.status} : ${res.statusText}`);
      }
      return res.arrayBuffer();
    }).then((buffer) => {
      if (this.workingPath === "") {
        this.workingPath = getWorkingPath(url);
      }
      return this.parse(buffer);
    });
  }
  /**
   * Resolves a relative URL against `workingPath`.
   * @param {string} url
   * @returns {string}
   */
  resolveExternalURL(url) {
    return new URL(url, this.workingPath).href;
  }
  /**
   * Parses a raw buffer into a tile result object. Must be implemented by subclasses.
   * @param {ArrayBuffer} buffer
   * @returns {any}
   */
  parse(buffer) {
    throw new Error("LoaderBase: Parse not implemented.");
  }
};

// build/core/renderer/utilities/FeatureTable.js
function parseBinArray(buffer, arrayStart, count, type, componentType, propertyName) {
  let stride;
  switch (type) {
    case "SCALAR":
      stride = 1;
      break;
    case "VEC2":
      stride = 2;
      break;
    case "VEC3":
      stride = 3;
      break;
    case "VEC4":
      stride = 4;
      break;
    default:
      throw new Error(`FeatureTable : Feature type not provided for "${propertyName}".`);
  }
  let data;
  const arrayLength = count * stride;
  switch (componentType) {
    case "BYTE":
      data = new Int8Array(buffer, arrayStart, arrayLength);
      break;
    case "UNSIGNED_BYTE":
      data = new Uint8Array(buffer, arrayStart, arrayLength);
      break;
    case "SHORT":
      data = new Int16Array(buffer, arrayStart, arrayLength);
      break;
    case "UNSIGNED_SHORT":
      data = new Uint16Array(buffer, arrayStart, arrayLength);
      break;
    case "INT":
      data = new Int32Array(buffer, arrayStart, arrayLength);
      break;
    case "UNSIGNED_INT":
      data = new Uint32Array(buffer, arrayStart, arrayLength);
      break;
    case "FLOAT":
      data = new Float32Array(buffer, arrayStart, arrayLength);
      break;
    case "DOUBLE":
      data = new Float64Array(buffer, arrayStart, arrayLength);
      break;
    default:
      throw new Error(`FeatureTable : Feature component type not provided for "${propertyName}".`);
  }
  return data;
}
var FeatureTable = class {
  /**
   * @param {ArrayBuffer} buffer
   * @param {number} start - Byte offset of the feature table within the buffer
   * @param {number} headerLength - Byte length of the JSON header
   * @param {number} binLength - Byte length of the binary body
   */
  constructor(buffer, start, headerLength, binLength) {
    this.buffer = buffer;
    this.binOffset = start + headerLength;
    this.binLength = binLength;
    let header = null;
    if (headerLength !== 0) {
      const headerData = new Uint8Array(buffer, start, headerLength);
      header = JSON.parse(arrayToString(headerData));
    } else {
      header = {};
    }
    this.header = header;
  }
  /**
   * Returns all property key names defined in the feature table header, excluding `extensions`.
   * @returns {Array<string>}
   */
  getKeys() {
    return Object.keys(this.header).filter((key) => key !== "extensions");
  }
  /**
   * Returns the value for the given property key. For binary properties, reads typed array data
   * from the binary body using the provided count, component type, and vector type.
   * @param {string} key
   * @param {number} count - Number of elements to read for binary properties
   * @param {string | null} [defaultComponentType] - Fallback component type (e.g. `'FLOAT'`, `'UNSIGNED_SHORT'`)
   * @param {string | null} [defaultType] - Fallback vector type (e.g. `'SCALAR'`, `'VEC3'`)
   * @returns {number | string | ArrayBufferView | null}
   */
  getData(key, count, defaultComponentType = null, defaultType = null) {
    const header = this.header;
    if (!(key in header)) {
      return null;
    }
    const feature = header[key];
    if (!(feature instanceof Object)) {
      return feature;
    } else if (Array.isArray(feature)) {
      return feature;
    } else {
      const { buffer, binOffset, binLength } = this;
      const byteOffset = feature.byteOffset || 0;
      const featureType = feature.type || defaultType;
      const featureComponentType = feature.componentType || defaultComponentType;
      if ("type" in feature && defaultType && feature.type !== defaultType) {
        throw new Error("FeatureTable: Specified type does not match expected type.");
      }
      const arrayStart = binOffset + byteOffset;
      const data = parseBinArray(buffer, arrayStart, count, featureType, featureComponentType, key);
      const dataEnd = arrayStart + data.byteLength;
      if (dataEnd > binOffset + binLength) {
        throw new Error("FeatureTable: Feature data read outside binary body length.");
      }
      return data;
    }
  }
  /**
   * Returns a slice of the binary body at the given offset and length.
   * @param {number} byteOffset
   * @param {number} byteLength
   * @returns {ArrayBuffer}
   */
  getBuffer(byteOffset, byteLength) {
    const { buffer, binOffset } = this;
    return buffer.slice(binOffset + byteOffset, binOffset + byteOffset + byteLength);
  }
};

// build/core/renderer/utilities/BatchTableHierarchyExtension.js
var BatchTableHierarchyExtension = class {
  constructor(batchTable) {
    this.batchTable = batchTable;
    const extensionHeader = batchTable.header.extensions["3DTILES_batch_table_hierarchy"];
    this.classes = extensionHeader.classes;
    for (const classDef of this.classes) {
      const instances = classDef.instances;
      for (const property in instances) {
        classDef.instances[property] = this._parseProperty(instances[property], classDef.length, property);
      }
    }
    this.instancesLength = extensionHeader.instancesLength;
    this.classIds = this._parseProperty(extensionHeader.classIds, this.instancesLength, "classIds");
    if (extensionHeader.parentCounts) {
      this.parentCounts = this._parseProperty(extensionHeader.parentCounts, this.instancesLength, "parentCounts");
    } else {
      this.parentCounts = new Array(this.instancesLength).fill(1);
    }
    if (extensionHeader.parentIds) {
      const parentIdsLength = this.parentCounts.reduce((a, b) => a + b, 0);
      this.parentIds = this._parseProperty(extensionHeader.parentIds, parentIdsLength, "parentIds");
    } else {
      this.parentIds = null;
    }
    this.instancesIds = [];
    const classCounter = {};
    for (const classId of this.classIds) {
      classCounter[classId] = classCounter[classId] ?? 0;
      this.instancesIds.push(classCounter[classId]);
      classCounter[classId]++;
    }
  }
  _parseProperty(property, propertyLength, propertyName) {
    if (Array.isArray(property)) {
      return property;
    } else {
      const { buffer, binOffset } = this.batchTable;
      const byteOffset = property.byteOffset;
      const componentType = property.componentType || "UNSIGNED_SHORT";
      const arrayStart = binOffset + byteOffset;
      return parseBinArray(buffer, arrayStart, propertyLength, "SCALAR", componentType, propertyName);
    }
  }
  getDataFromId(id, target = {}) {
    const parentCount = this.parentCounts[id];
    if (this.parentIds && parentCount > 0) {
      let parentIdsOffset = 0;
      for (let i = 0; i < id; i++) {
        parentIdsOffset += this.parentCounts[i];
      }
      for (let i = 0; i < parentCount; i++) {
        const parentId = this.parentIds[parentIdsOffset + i];
        if (parentId !== id) {
          this.getDataFromId(parentId, target);
        }
      }
    }
    const classId = this.classIds[id];
    const instances = this.classes[classId].instances;
    const className = this.classes[classId].name;
    const instanceId = this.instancesIds[id];
    for (const key in instances) {
      target[className] = target[className] || {};
      target[className][key] = instances[key][instanceId];
    }
    return target;
  }
};

// build/core/renderer/utilities/BatchTable.js
var BatchTable = class extends FeatureTable {
  /**
   * @param {ArrayBuffer} buffer
   * @param {number} count - Number of features in the batch
   * @param {number} start - Byte offset of the batch table within the buffer
   * @param {number} headerLength - Byte length of the JSON header
   * @param {number} binLength - Byte length of the binary body
   */
  constructor(buffer, count, start, headerLength, binLength) {
    super(buffer, start, headerLength, binLength);
    this.count = count;
    this.extensions = {};
    const extensions = this.header.extensions;
    if (extensions) {
      if (extensions["3DTILES_batch_table_hierarchy"]) {
        this.extensions["3DTILES_batch_table_hierarchy"] = new BatchTableHierarchyExtension(this);
      }
    }
  }
  /**
   * Returns an object with all properties of the batch table and its extensions for the
   * given feature id. A `target` object can be specified to store the result. Throws if
   * `id` is out of bounds.
   * @param {number} id - Feature index (0 to count - 1)
   * @param {Object} [target={}] - Optional object to write properties into
   * @returns {Object}
   */
  getDataFromId(id, target = {}) {
    if (id < 0 || id >= this.count) {
      throw new Error(`BatchTable: id value "${id}" out of bounds for "${this.count}" features number.`);
    }
    for (const key of this.getKeys()) {
      target[key] = super.getData(key, this.count)[id];
    }
    for (const extensionName in this.extensions) {
      const extension = this.extensions[extensionName];
      if (extension.getDataFromId instanceof Function) {
        target[extensionName] = target[extensionName] || {};
        extension.getDataFromId(id, target[extensionName]);
      }
    }
    return target;
  }
  /**
   * Returns the array of values for the given property key across all features. Returns
   * `null` if the key is not in the table.
   * @param {string} key
   * @returns {Array | TypedArray | null}
   */
  getPropertyArray(key) {
    return super.getData(key, this.count);
  }
};

// build/core/renderer/loaders/B3DMLoaderBase.js
var B3DMLoaderBase = class extends LoaderBase {
  /**
   * Parses a B3DM buffer and returns the raw tile data.
   * @param {ArrayBuffer} buffer
   * @returns {{ version: string, featureTable: FeatureTable, batchTable: BatchTable, glbBytes: Uint8Array }}
   */
  parse(buffer) {
    const dataView = new DataView(buffer);
    const magic = readMagicBytes(dataView);
    console.assert(magic === "b3dm");
    const version = dataView.getUint32(4, true);
    console.assert(version === 1);
    const byteLength = dataView.getUint32(8, true);
    console.assert(byteLength === buffer.byteLength);
    const featureTableJSONByteLength = dataView.getUint32(12, true);
    const featureTableBinaryByteLength = dataView.getUint32(16, true);
    const batchTableJSONByteLength = dataView.getUint32(20, true);
    const batchTableBinaryByteLength = dataView.getUint32(24, true);
    const featureTableStart = 28;
    const featureTableBuffer = buffer.slice(
      featureTableStart,
      featureTableStart + featureTableJSONByteLength + featureTableBinaryByteLength
    );
    const featureTable = new FeatureTable(
      featureTableBuffer,
      0,
      featureTableJSONByteLength,
      featureTableBinaryByteLength
    );
    const batchTableStart = featureTableStart + featureTableJSONByteLength + featureTableBinaryByteLength;
    const batchTableBuffer = buffer.slice(
      batchTableStart,
      batchTableStart + batchTableJSONByteLength + batchTableBinaryByteLength
    );
    const batchTable = new BatchTable(
      batchTableBuffer,
      featureTable.getData("BATCH_LENGTH"),
      0,
      batchTableJSONByteLength,
      batchTableBinaryByteLength
    );
    const glbStart = batchTableStart + batchTableJSONByteLength + batchTableBinaryByteLength;
    const glbBytes = new Uint8Array(buffer, glbStart, byteLength - glbStart);
    return {
      version,
      featureTable,
      batchTable,
      glbBytes
    };
  }
};

// build/core/renderer/loaders/I3DMLoaderBase.js
var I3DMLoaderBase = class extends LoaderBase {
  /**
   * Parses an I3DM buffer and returns the raw tile data.
   * @param {ArrayBuffer} buffer
   * @returns {Promise<{ version: string, featureTable: FeatureTable, batchTable: BatchTable, glbBytes: Uint8Array, gltfWorkingPath: string }>}
   */
  parse(buffer) {
    const dataView = new DataView(buffer);
    const magic = readMagicBytes(dataView);
    console.assert(magic === "i3dm");
    const version = dataView.getUint32(4, true);
    console.assert(version === 1);
    const byteLength = dataView.getUint32(8, true);
    console.assert(byteLength === buffer.byteLength);
    const featureTableJSONByteLength = dataView.getUint32(12, true);
    const featureTableBinaryByteLength = dataView.getUint32(16, true);
    const batchTableJSONByteLength = dataView.getUint32(20, true);
    const batchTableBinaryByteLength = dataView.getUint32(24, true);
    const gltfFormat = dataView.getUint32(28, true);
    const featureTableStart = 32;
    const featureTableBuffer = buffer.slice(
      featureTableStart,
      featureTableStart + featureTableJSONByteLength + featureTableBinaryByteLength
    );
    const featureTable = new FeatureTable(
      featureTableBuffer,
      0,
      featureTableJSONByteLength,
      featureTableBinaryByteLength
    );
    const batchTableStart = featureTableStart + featureTableJSONByteLength + featureTableBinaryByteLength;
    const batchTableBuffer = buffer.slice(
      batchTableStart,
      batchTableStart + batchTableJSONByteLength + batchTableBinaryByteLength
    );
    const batchTable = new BatchTable(
      batchTableBuffer,
      featureTable.getData("INSTANCES_LENGTH"),
      0,
      batchTableJSONByteLength,
      batchTableBinaryByteLength
    );
    const glbStart = batchTableStart + batchTableJSONByteLength + batchTableBinaryByteLength;
    const bodyBytes = new Uint8Array(buffer, glbStart, byteLength - glbStart);
    let glbBytes = null;
    let promise = null;
    let gltfWorkingPath = null;
    if (gltfFormat) {
      glbBytes = bodyBytes;
      promise = Promise.resolve();
    } else {
      const externalUrl = this.resolveExternalURL(arrayToString(bodyBytes));
      gltfWorkingPath = getWorkingPath(externalUrl);
      promise = fetch(externalUrl, this.fetchOptions).then((res) => {
        if (!res.ok) {
          throw new Error(`I3DMLoaderBase : Failed to load file "${externalUrl}" with status ${res.status} : ${res.statusText}`);
        }
        return res.arrayBuffer();
      }).then((buffer2) => {
        glbBytes = new Uint8Array(buffer2);
      });
    }
    return promise.then(() => {
      return {
        version,
        featureTable,
        batchTable,
        glbBytes,
        gltfWorkingPath
      };
    });
  }
};

// build/core/renderer/loaders/PNTSLoaderBase.js
var PNTSLoaderBase = class extends LoaderBase {
  /**
   * Parses a PNTS buffer and returns the raw tile data.
   * @param {ArrayBuffer} buffer
   * @returns {Promise<{ version: string, featureTable: FeatureTable, batchTable: BatchTable }>}
   */
  parse(buffer) {
    const dataView = new DataView(buffer);
    const magic = readMagicBytes(dataView);
    console.assert(magic === "pnts");
    const version = dataView.getUint32(4, true);
    console.assert(version === 1);
    const byteLength = dataView.getUint32(8, true);
    console.assert(byteLength === buffer.byteLength);
    const featureTableJSONByteLength = dataView.getUint32(12, true);
    const featureTableBinaryByteLength = dataView.getUint32(16, true);
    const batchTableJSONByteLength = dataView.getUint32(20, true);
    const batchTableBinaryByteLength = dataView.getUint32(24, true);
    const featureTableStart = 28;
    const featureTableBuffer = buffer.slice(
      featureTableStart,
      featureTableStart + featureTableJSONByteLength + featureTableBinaryByteLength
    );
    const featureTable = new FeatureTable(
      featureTableBuffer,
      0,
      featureTableJSONByteLength,
      featureTableBinaryByteLength
    );
    const batchTableStart = featureTableStart + featureTableJSONByteLength + featureTableBinaryByteLength;
    const batchTableBuffer = buffer.slice(
      batchTableStart,
      batchTableStart + batchTableJSONByteLength + batchTableBinaryByteLength
    );
    const batchTable = new BatchTable(
      batchTableBuffer,
      featureTable.getData("BATCH_LENGTH") || featureTable.getData("POINTS_LENGTH"),
      0,
      batchTableJSONByteLength,
      batchTableBinaryByteLength
    );
    return Promise.resolve({
      version,
      featureTable,
      batchTable
    });
  }
};

// build/core/renderer/loaders/CMPTLoaderBase.js
var CMPTLoaderBase = class extends LoaderBase {
  /**
   * Parses a CMPT buffer and returns an object containing each inner tile's type and raw buffer.
   * @param {ArrayBuffer} buffer
   * @returns {{ version: string, tiles: Array<{ type: string, buffer: Uint8Array, version: number }> }}
   */
  parse(buffer) {
    const dataView = new DataView(buffer);
    const magic = readMagicBytes(dataView);
    console.assert(magic === "cmpt", 'CMPTLoader: The magic bytes equal "cmpt".');
    const version = dataView.getUint32(4, true);
    console.assert(version === 1, 'CMPTLoader: The version listed in the header is "1".');
    const byteLength = dataView.getUint32(8, true);
    console.assert(byteLength === buffer.byteLength, "CMPTLoader: The contents buffer length listed in the header matches the file.");
    const tilesLength = dataView.getUint32(12, true);
    const tiles = [];
    let offset = 16;
    for (let i = 0; i < tilesLength; i++) {
      const tileView = new DataView(buffer, offset, 12);
      const tileMagic = readMagicBytes(tileView);
      const tileVersion = tileView.getUint32(4, true);
      const byteLength2 = tileView.getUint32(8, true);
      const tileBuffer = new Uint8Array(buffer, offset, byteLength2);
      tiles.push({
        type: tileMagic,
        buffer: tileBuffer,
        version: tileVersion
      });
      offset += byteLength2;
    }
    return {
      version,
      tiles
    };
  }
};

// build/three/renderer/loaders/B3DMLoader.js
import { DefaultLoadingManager, Matrix4 } from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
var B3DMLoader = class extends B3DMLoaderBase {
  constructor(manager = DefaultLoadingManager) {
    super();
    this.manager = manager;
    this.adjustmentTransform = new Matrix4();
  }
  /**
   * Parses a b3dm buffer and resolves to a GLTF result object extended with legacy
   * tile metadata. Both `model` and `model.scene` receive the extra fields.
   * @param {ArrayBuffer} buffer
   * @returns {Promise<{ scene: Group, scenes: Array, batchTable: BatchTable, featureTable: FeatureTable }>}
   */
  parse(buffer) {
    const b3dm = super.parse(buffer);
    const gltfBuffer = b3dm.glbBytes.slice().buffer;
    return new Promise((resolve, reject) => {
      const manager = this.manager;
      const fetchOptions = this.fetchOptions;
      const loader = manager.getHandler("path.gltf") || new GLTFLoader(manager);
      if (fetchOptions.credentials === "include" && fetchOptions.mode === "cors") {
        loader.setCrossOrigin("use-credentials");
      }
      if ("credentials" in fetchOptions) {
        loader.setWithCredentials(fetchOptions.credentials === "include");
      }
      if (fetchOptions.headers) {
        loader.setRequestHeader(fetchOptions.headers);
      }
      let workingPath = this.workingPath;
      if (!/[\\/]$/.test(workingPath) && workingPath.length) {
        workingPath += "/";
      }
      const adjustmentTransform = this.adjustmentTransform;
      loader.parse(gltfBuffer, workingPath, (model) => {
        const { batchTable, featureTable } = b3dm;
        const { scene } = model;
        const rtcCenter = featureTable.getData("RTC_CENTER", 1, "FLOAT", "VEC3");
        if (rtcCenter) {
          scene.position.x += rtcCenter[0];
          scene.position.y += rtcCenter[1];
          scene.position.z += rtcCenter[2];
        }
        model.scene.updateMatrix();
        model.scene.matrix.multiply(adjustmentTransform);
        model.scene.matrix.decompose(model.scene.position, model.scene.quaternion, model.scene.scale);
        model.batchTable = batchTable;
        model.featureTable = featureTable;
        scene.batchTable = batchTable;
        scene.featureTable = featureTable;
        resolve(model);
      }, reject);
    });
  }
};

// build/three/renderer/loaders/PNTSLoader.js
import {
  Points,
  PointsMaterial,
  BufferGeometry,
  BufferAttribute,
  DefaultLoadingManager as DefaultLoadingManager2,
  Vector3 as Vector32,
  Color
} from "three";

// build/three/renderer/loaders/rgb565torgb.js
function rgb565torgb(rgb565) {
  const red5 = rgb565 >> 11;
  const green6 = rgb565 >> 5 & 63;
  const blue5 = rgb565 & 31;
  const red8 = Math.round(red5 / 31 * 255);
  const green8 = Math.round(green6 / 63 * 255);
  const blue8 = Math.round(blue5 / 31 * 255);
  return [red8, green8, blue8];
}

// build/three/renderer/loaders/decodeOctNormal.js
import { Vector2, MathUtils, Vector3 } from "three";
var f = /* @__PURE__ */ new Vector2();
function decodeOctNormal(x, y, target = new Vector3()) {
  f.set(x, y).divideScalar(256).multiplyScalar(2).subScalar(1);
  target.set(f.x, f.y, 1 - Math.abs(f.x) - Math.abs(f.y));
  const t = MathUtils.clamp(-target.z, 0, 1);
  if (target.x >= 0) {
    target.setX(target.x - t);
  } else {
    target.setX(target.x + t);
  }
  if (target.y >= 0) {
    target.setY(target.y - t);
  } else {
    target.setY(target.y + t);
  }
  target.normalize();
  return target;
}

// build/three/renderer/loaders/PNTSLoader.js
var DRACO_ATTRIBUTE_MAP = {
  RGB: "color",
  POSITION: "position"
};
var PNTSLoader = class extends PNTSLoaderBase {
  constructor(manager = DefaultLoadingManager2) {
    super();
    this.manager = manager;
  }
  /**
   * Parses a pnts buffer and resolves to a result object containing a constructed
   * three.js `Points` scene with metadata attached.
   * @param {ArrayBuffer} buffer
   * @returns {Promise<{ scene: Points, batchTable: BatchTable, featureTable: FeatureTable }>}
   */
  parse(buffer) {
    return super.parse(buffer).then(async (result) => {
      const { featureTable, batchTable } = result;
      const material = new PointsMaterial();
      const extensions = featureTable.header.extensions;
      const translationOffset = new Vector32();
      let geometry;
      if (extensions && extensions["3DTILES_draco_point_compression"]) {
        const { byteOffset, byteLength, properties } = extensions["3DTILES_draco_point_compression"];
        const dracoLoader = this.manager.getHandler("draco.drc");
        if (dracoLoader == null) {
          throw new Error("PNTSLoader: dracoLoader not available.");
        }
        const attributeIDs = {};
        for (const key in properties) {
          if (key in DRACO_ATTRIBUTE_MAP && key in properties) {
            const mappedKey = DRACO_ATTRIBUTE_MAP[key];
            attributeIDs[mappedKey] = properties[key];
          }
        }
        const taskConfig = {
          attributeIDs,
          attributeTypes: {
            position: "Float32Array",
            color: "Uint8Array"
          },
          useUniqueIDs: true
        };
        const buffer2 = featureTable.getBuffer(byteOffset, byteLength);
        geometry = await dracoLoader.decodeGeometry(buffer2, taskConfig);
        if (geometry.attributes.color) {
          material.vertexColors = true;
        }
      } else {
        const POINTS_LENGTH = featureTable.getData("POINTS_LENGTH");
        const POSITION = featureTable.getData("POSITION", POINTS_LENGTH, "FLOAT", "VEC3");
        const NORMAL = featureTable.getData("NORMAL", POINTS_LENGTH, "FLOAT", "VEC3");
        const NORMAL_OCT16P = featureTable.getData("NORMAL", POINTS_LENGTH, "UNSIGNED_BYTE", "VEC2");
        const RGB = featureTable.getData("RGB", POINTS_LENGTH, "UNSIGNED_BYTE", "VEC3");
        const RGBA = featureTable.getData("RGBA", POINTS_LENGTH, "UNSIGNED_BYTE", "VEC4");
        const RGB565 = featureTable.getData("RGB565", POINTS_LENGTH, "UNSIGNED_SHORT", "SCALAR");
        const CONSTANT_RGBA = featureTable.getData("CONSTANT_RGBA", POINTS_LENGTH, "UNSIGNED_BYTE", "VEC4");
        const POSITION_QUANTIZED = featureTable.getData("POSITION_QUANTIZED", POINTS_LENGTH, "UNSIGNED_SHORT", "VEC3");
        const QUANTIZED_VOLUME_SCALE = featureTable.getData("QUANTIZED_VOLUME_SCALE", POINTS_LENGTH, "FLOAT", "VEC3");
        const QUANTIZED_VOLUME_OFFSET = featureTable.getData("QUANTIZED_VOLUME_OFFSET", POINTS_LENGTH, "FLOAT", "VEC3");
        geometry = new BufferGeometry();
        if (POSITION_QUANTIZED) {
          const decodedPositions = new Float32Array(POINTS_LENGTH * 3);
          for (let i = 0; i < POINTS_LENGTH; i++) {
            for (let j = 0; j < 3; j++) {
              const index = 3 * i + j;
              decodedPositions[index] = POSITION_QUANTIZED[index] / 65535 * QUANTIZED_VOLUME_SCALE[j];
            }
          }
          translationOffset.x = QUANTIZED_VOLUME_OFFSET[0];
          translationOffset.y = QUANTIZED_VOLUME_OFFSET[1];
          translationOffset.z = QUANTIZED_VOLUME_OFFSET[2];
          geometry.setAttribute("position", new BufferAttribute(decodedPositions, 3, false));
        } else {
          geometry.setAttribute("position", new BufferAttribute(POSITION, 3, false));
        }
        if (NORMAL !== null) {
          geometry.setAttribute("normal", new BufferAttribute(NORMAL, 3, false));
        } else if (NORMAL_OCT16P !== null) {
          const decodedNormals = new Float32Array(POINTS_LENGTH * 3);
          const n = new Vector32();
          for (let i = 0; i < POINTS_LENGTH; i++) {
            const x = NORMAL_OCT16P[i * 2];
            const y = NORMAL_OCT16P[i * 2 + 1];
            const normal = decodeOctNormal(x, y, n);
            decodedNormals[i * 3] = normal.x;
            decodedNormals[i * 3 + 1] = normal.y;
            decodedNormals[i * 3 + 2] = normal.z;
          }
          geometry.setAttribute("normal", new BufferAttribute(decodedNormals, 3, false));
        }
        if (RGBA !== null) {
          geometry.setAttribute("color", new BufferAttribute(RGBA, 4, true));
          material.vertexColors = true;
          material.transparent = true;
          material.depthWrite = false;
        } else if (RGB !== null) {
          geometry.setAttribute("color", new BufferAttribute(RGB, 3, true));
          material.vertexColors = true;
        } else if (RGB565 !== null) {
          const color = new Uint8Array(POINTS_LENGTH * 3);
          for (let i = 0; i < POINTS_LENGTH; i++) {
            const rgbColor = rgb565torgb(RGB565[i]);
            for (let j = 0; j < 3; j++) {
              const index = 3 * i + j;
              color[index] = rgbColor[j];
            }
          }
          geometry.setAttribute("color", new BufferAttribute(color, 3, true));
          material.vertexColors = true;
        } else if (CONSTANT_RGBA !== null) {
          const color = new Color(CONSTANT_RGBA[0], CONSTANT_RGBA[1], CONSTANT_RGBA[2]);
          material.color = color;
          const opacity = CONSTANT_RGBA[3] / 255;
          if (opacity < 1) {
            material.opacity = opacity;
            material.transparent = true;
            material.depthWrite = false;
          }
        }
      }
      const object = new Points(geometry, material);
      object.position.copy(translationOffset);
      result.scene = object;
      result.scene.featureTable = featureTable;
      result.scene.batchTable = batchTable;
      const rtcCenter = featureTable.getData("RTC_CENTER", 1, "FLOAT", "VEC3");
      if (rtcCenter) {
        result.scene.position.x += rtcCenter[0];
        result.scene.position.y += rtcCenter[1];
        result.scene.position.z += rtcCenter[2];
      }
      return result;
    });
  }
};

// build/three/renderer/loaders/I3DMLoader.js
import { DefaultLoadingManager as DefaultLoadingManager3, Matrix4 as Matrix43, InstancedMesh, Vector3 as Vector35, Quaternion } from "three";
import { GLTFLoader as GLTFLoader2 } from "three/addons/loaders/GLTFLoader.js";

// build/three/renderer/math/Ellipsoid.js
import { Vector3 as Vector34, Spherical as Spherical2, MathUtils as MathUtils3, Ray, Matrix4 as Matrix42, Sphere, Euler } from "three";

// build/three/renderer/math/GeoUtils.js
var GeoUtils_exports = {};
__export(GeoUtils_exports, {
  latitudeToSphericalPhi: () => latitudeToSphericalPhi,
  sphericalPhiToLatitude: () => sphericalPhiToLatitude,
  swapToGeoFrame: () => swapToGeoFrame,
  swapToThreeFrame: () => swapToThreeFrame,
  toLatLonString: () => toLatLonString
});
import { Spherical, Vector3 as Vector33, MathUtils as MathUtils2 } from "three";
var _spherical = /* @__PURE__ */ new Spherical();
var _vec = /* @__PURE__ */ new Vector33();
var _geoResults = {};
function swapToGeoFrame(target) {
  const { x, y, z } = target;
  target.x = z;
  target.y = x;
  target.z = y;
}
function swapToThreeFrame(target) {
  const { x, y, z } = target;
  target.z = x;
  target.x = y;
  target.y = z;
}
function sphericalPhiToLatitude(phi) {
  return -(phi - Math.PI / 2);
}
function latitudeToSphericalPhi(latitude) {
  return -latitude + Math.PI / 2;
}
function correctGeoCoordWrap(lat, lon, target = {}) {
  _spherical.theta = lon;
  _spherical.phi = latitudeToSphericalPhi(lat);
  _vec.setFromSpherical(_spherical);
  _spherical.setFromVector3(_vec);
  target.lat = sphericalPhiToLatitude(_spherical.phi);
  target.lon = _spherical.theta;
  return target;
}
function toHoursMinutesSecondsString(value, pos = "E", neg = "W") {
  const direction = value < 0 ? neg : pos;
  value = Math.abs(value);
  const hours = ~~value;
  const minDec = (value - hours) * 60;
  const minutes = ~~minDec;
  const secDec = (minDec - minutes) * 60;
  const seconds = ~~secDec;
  return `${hours}\xB0 ${minutes}' ${seconds}" ${direction}`;
}
function toLatLonString(lat, lon, decimalFormat = false) {
  const result = correctGeoCoordWrap(lat, lon, _geoResults);
  let latString, lonString;
  if (decimalFormat) {
    latString = `${(MathUtils2.RAD2DEG * result.lat).toFixed(4)}\xB0`;
    lonString = `${(MathUtils2.RAD2DEG * result.lon).toFixed(4)}\xB0`;
  } else {
    latString = toHoursMinutesSecondsString(MathUtils2.RAD2DEG * result.lat, "N", "S");
    lonString = toHoursMinutesSecondsString(MathUtils2.RAD2DEG * result.lon, "E", "W");
  }
  return `${latString} ${lonString}`;
}

// build/three/renderer/math/Ellipsoid.js
var _spherical2 = /* @__PURE__ */ new Spherical2();
var _norm = /* @__PURE__ */ new Vector34();
var _vec2 = /* @__PURE__ */ new Vector34();
var _vec22 = /* @__PURE__ */ new Vector34();
var _matrix = /* @__PURE__ */ new Matrix42();
var _matrix2 = /* @__PURE__ */ new Matrix42();
var _sphere = /* @__PURE__ */ new Sphere();
var _euler = /* @__PURE__ */ new Euler();
var _vecX = /* @__PURE__ */ new Vector34();
var _vecY = /* @__PURE__ */ new Vector34();
var _vecZ = /* @__PURE__ */ new Vector34();
var _pos = /* @__PURE__ */ new Vector34();
var _ray = /* @__PURE__ */ new Ray();
var EPSILON12 = 1e-12;
var CENTER_EPS = 0.1;
var ENU_FRAME = 0;
var CAMERA_FRAME = 1;
var OBJECT_FRAME = 2;
var Ellipsoid = class {
  constructor(x = 1, y = 1, z = 1) {
    this.name = "";
    this.radius = new Vector34(x, y, z);
  }
  /**
   * Returns the point where the given ray intersects the ellipsoid surface, or null if no
   * intersection exists. Writes the result into `target`.
   * @param {Ray} ray
   * @param {Vector3} target
   * @returns {Vector3|null}
   */
  intersectRay(ray, target) {
    _matrix.makeScale(...this.radius).invert();
    _sphere.center.set(0, 0, 0);
    _sphere.radius = 1;
    _ray.copy(ray).applyMatrix4(_matrix);
    if (_ray.intersectSphere(_sphere, target)) {
      _matrix.makeScale(...this.radius);
      target.applyMatrix4(_matrix);
      return target;
    } else {
      return null;
    }
  }
  /**
   * Returns a Matrix4 representing the East-North-Up (ENU) frame at the given geographic
   * position: X points east, Y points north, Z points up. Writes the result into `target`.
   * @param {number} lat Latitude in radians.
   * @param {number} lon Longitude in radians.
   * @param {number} height Height above the ellipsoid surface in meters.
   * @param {Matrix4} target
   * @returns {Matrix4}
   */
  getEastNorthUpFrame(lat, lon, height, target) {
    if (height.isMatrix4) {
      target = height;
      height = 0;
      console.warn('Ellipsoid: The signature for "getEastNorthUpFrame" has changed.');
    }
    this.getEastNorthUpAxes(lat, lon, _vecX, _vecY, _vecZ);
    this.getCartographicToPosition(lat, lon, height, _pos);
    return target.makeBasis(_vecX, _vecY, _vecZ).setPosition(_pos);
  }
  /**
   * Returns a Matrix4 representing the ENU frame at the given position, rotated by the given
   * azimuth, elevation, and roll. Equivalent to `getObjectFrame` with `ENU_FRAME`.
   * @param {number} lat Latitude in radians.
   * @param {number} lon Longitude in radians.
   * @param {number} height Height above the ellipsoid surface in meters.
   * @param {number} az Azimuth in radians, measured from true north towards east.
   * @param {number} el Elevation in radians, measured from the horizon upward.
   * @param {number} roll Roll in radians around the north axis.
   * @param {Matrix4} target
   * @returns {Matrix4}
   */
  getOrientedEastNorthUpFrame(lat, lon, height, az, el, roll, target) {
    return this.getObjectFrame(lat, lon, height, az, el, roll, target, ENU_FRAME);
  }
  /**
   * Returns a Matrix4 representing a frame at the given geographic position, rotated by the
   * given azimuth, elevation, and roll, and adjusted to match the three.js `frame` convention.
   * `OBJECT_FRAME` orients with "+Y" up and "+Z" forward; `CAMERA_FRAME` orients with "+Y" up
   * and "-Z" forward; `ENU_FRAME` returns the raw ENU-relative rotation.
   * @param {number} lat Latitude in radians.
   * @param {number} lon Longitude in radians.
   * @param {number} height Height above the ellipsoid surface in meters.
   * @param {number} az Azimuth in radians, measured from true north towards east.
   * @param {number} el Elevation in radians, measured from the horizon upward.
   * @param {number} roll Roll in radians around the north axis.
   * @param {Matrix4} target
   * @param {Frames} [frame=OBJECT_FRAME]
   * @returns {Matrix4}
   */
  getObjectFrame(lat, lon, height, az, el, roll, target, frame = OBJECT_FRAME) {
    this.getEastNorthUpFrame(lat, lon, height, _matrix);
    _euler.set(el, roll, -az, "ZXY");
    target.makeRotationFromEuler(_euler).premultiply(_matrix);
    if (frame === CAMERA_FRAME) {
      _euler.set(Math.PI / 2, 0, 0, "XYZ");
      _matrix2.makeRotationFromEuler(_euler);
      target.multiply(_matrix2);
    } else if (frame === OBJECT_FRAME) {
      _euler.set(-Math.PI / 2, 0, Math.PI, "XYZ");
      _matrix2.makeRotationFromEuler(_euler);
      target.multiply(_matrix2);
    }
    return target;
  }
  /**
   * Extracts geographic position and orientation (lat, lon, height, azimuth, elevation, roll)
   * from the given object/camera frame matrix. The inverse of `getObjectFrame`. Writes the
   * result into `target` and returns it.
   * @param {Matrix4} matrix
   * @param {Object} target
   * @param {Frames} [frame=OBJECT_FRAME]
   * @returns {{ lat: number, lon: number, height: number, azimuth: number, elevation: number, roll: number }}
   */
  getCartographicFromObjectFrame(matrix, target, frame = OBJECT_FRAME) {
    if (frame === CAMERA_FRAME) {
      _euler.set(-Math.PI / 2, 0, 0, "XYZ");
      _matrix2.makeRotationFromEuler(_euler).premultiply(matrix);
    } else if (frame === OBJECT_FRAME) {
      _euler.set(-Math.PI / 2, 0, Math.PI, "XYZ");
      _matrix2.makeRotationFromEuler(_euler).premultiply(matrix);
    } else {
      _matrix2.copy(matrix);
    }
    _pos.setFromMatrixPosition(_matrix2);
    this.getPositionToCartographic(_pos, target);
    this.getEastNorthUpFrame(target.lat, target.lon, 0, _matrix).invert();
    _matrix2.premultiply(_matrix);
    _euler.setFromRotationMatrix(_matrix2, "ZXY");
    target.azimuth = -_euler.z;
    target.elevation = _euler.x;
    target.roll = _euler.y;
    return target;
  }
  /**
   * Fills in the east, north, and up unit vectors for the ENU frame at the given latitude and
   * longitude. Optionally writes the surface position into `point`.
   * @param {number} lat Latitude in radians.
   * @param {number} lon Longitude in radians.
   * @param {Vector3} vecEast
   * @param {Vector3} vecNorth
   * @param {Vector3} vecUp
   * @param {Vector3} [point]
   */
  getEastNorthUpAxes(lat, lon, vecEast, vecNorth, vecUp, point = _pos) {
    this.getCartographicToPosition(lat, lon, 0, point);
    this.getCartographicToNormal(lat, lon, vecUp);
    vecEast.set(-point.y, point.x, 0).normalize();
    vecNorth.crossVectors(vecUp, vecEast).normalize();
  }
  /**
   * Converts geographic coordinates to a 3D Cartesian position on the ellipsoid surface
   * (plus the given height offset). Writes the result into `target` and returns it.
   * @param {number} lat Latitude in radians.
   * @param {number} lon Longitude in radians.
   * @param {number} height Height above the ellipsoid surface in meters.
   * @param {Vector3} target
   * @returns {Vector3}
   */
  getCartographicToPosition(lat, lon, height, target) {
    this.getCartographicToNormal(lat, lon, _norm);
    const radius = this.radius;
    _vec2.copy(_norm);
    _vec2.x *= radius.x ** 2;
    _vec2.y *= radius.y ** 2;
    _vec2.z *= radius.z ** 2;
    const gamma = Math.sqrt(_norm.dot(_vec2));
    _vec2.divideScalar(gamma);
    return target.copy(_vec2).addScaledVector(_norm, height);
  }
  /**
   * Converts a 3D Cartesian position to geographic coordinates (lat, lon, height). Writes the
   * result into `target` and returns it.
   * @param {Vector3} pos
   * @param {Object} target
   * @returns {{ lat: number, lon: number, height: number }}
   */
  getPositionToCartographic(pos, target) {
    this.getPositionToSurfacePoint(pos, _vec2);
    this.getPositionToNormal(_vec2, _norm);
    const heightDelta = _vec22.subVectors(pos, _vec2);
    target.lon = Math.atan2(_norm.y, _norm.x);
    target.lat = Math.asin(_norm.z);
    target.height = Math.sign(heightDelta.dot(pos)) * heightDelta.length();
    return target;
  }
  /**
   * Returns the surface normal of the ellipsoid at the given latitude and longitude. Writes the
   * result into `target` and returns it.
   * @param {number} lat Latitude in radians.
   * @param {number} lon Longitude in radians.
   * @param {Vector3} target
   * @returns {Vector3}
   */
  getCartographicToNormal(lat, lon, target) {
    _spherical2.set(1, latitudeToSphericalPhi(lat), lon);
    target.setFromSpherical(_spherical2).normalize();
    swapToGeoFrame(target);
    return target;
  }
  /**
   * Returns the surface normal of the ellipsoid at the given 3D Cartesian position. Writes the
   * result into `target` and returns it.
   * @param {Vector3} pos
   * @param {Vector3} target
   * @returns {Vector3}
   */
  getPositionToNormal(pos, target) {
    const radius = this.radius;
    target.copy(pos);
    target.x /= radius.x ** 2;
    target.y /= radius.y ** 2;
    target.z /= radius.z ** 2;
    target.normalize();
    return target;
  }
  /**
   * Projects the given 3D position onto the ellipsoid surface along the geodetic normal.
   * Returns null if the position is at or near the center. Writes the result into `target`.
   * @param {Vector3} pos
   * @param {Vector3} target
   * @returns {Vector3|null}
   */
  getPositionToSurfacePoint(pos, target) {
    const radius = this.radius;
    const invRadiusSqX = 1 / radius.x ** 2;
    const invRadiusSqY = 1 / radius.y ** 2;
    const invRadiusSqZ = 1 / radius.z ** 2;
    const x2 = pos.x * pos.x * invRadiusSqX;
    const y2 = pos.y * pos.y * invRadiusSqY;
    const z2 = pos.z * pos.z * invRadiusSqZ;
    const squaredNorm = x2 + y2 + z2;
    const ratio = Math.sqrt(1 / squaredNorm);
    const intersection = _vec2.copy(pos).multiplyScalar(ratio);
    if (squaredNorm < CENTER_EPS) {
      return !isFinite(ratio) ? null : target.copy(intersection);
    }
    const gradient = _vec22.set(
      intersection.x * invRadiusSqX * 2,
      intersection.y * invRadiusSqY * 2,
      intersection.z * invRadiusSqZ * 2
    );
    let lambda = (1 - ratio) * pos.length() / (0.5 * gradient.length());
    let correction = 0;
    let func, denominator;
    let xMultiplier, yMultiplier, zMultiplier;
    let xMultiplier2, yMultiplier2, zMultiplier2;
    let xMultiplier3, yMultiplier3, zMultiplier3;
    do {
      lambda -= correction;
      xMultiplier = 1 / (1 + lambda * invRadiusSqX);
      yMultiplier = 1 / (1 + lambda * invRadiusSqY);
      zMultiplier = 1 / (1 + lambda * invRadiusSqZ);
      xMultiplier2 = xMultiplier * xMultiplier;
      yMultiplier2 = yMultiplier * yMultiplier;
      zMultiplier2 = zMultiplier * zMultiplier;
      xMultiplier3 = xMultiplier2 * xMultiplier;
      yMultiplier3 = yMultiplier2 * yMultiplier;
      zMultiplier3 = zMultiplier2 * zMultiplier;
      func = x2 * xMultiplier2 + y2 * yMultiplier2 + z2 * zMultiplier2 - 1;
      denominator = x2 * xMultiplier3 * invRadiusSqX + y2 * yMultiplier3 * invRadiusSqY + z2 * zMultiplier3 * invRadiusSqZ;
      const derivative = -2 * denominator;
      correction = func / derivative;
    } while (Math.abs(func) > EPSILON12);
    return target.set(
      pos.x * xMultiplier,
      pos.y * yMultiplier,
      pos.z * zMultiplier
    );
  }
  /**
   * Returns the geometric distance to the horizon from the given latitude and elevation above
   * the ellipsoid surface.
   * @param {number} latitude Latitude in degrees.
   * @param {number} elevation Height above the ellipsoid surface in meters.
   * @returns {number}
   */
  calculateHorizonDistance(latitude, elevation) {
    const effectiveRadius = this.calculateEffectiveRadius(latitude);
    return Math.sqrt(2 * effectiveRadius * elevation + elevation ** 2);
  }
  /**
   * Returns the prime vertical radius of curvature (distance from the center of the ellipsoid
   * to the surface along the normal) at the given latitude.
   * @param {number} latitude Latitude in degrees.
   * @returns {number}
   */
  calculateEffectiveRadius(latitude) {
    const semiMajorAxis = this.radius.x;
    const semiMinorAxis = this.radius.z;
    const eSquared = 1 - semiMinorAxis ** 2 / semiMajorAxis ** 2;
    const phi = latitude * MathUtils3.DEG2RAD;
    const sinPhiSquared = Math.sin(phi) ** 2;
    const N = semiMajorAxis / Math.sqrt(1 - eSquared * sinPhiSquared);
    return N;
  }
  /**
   * Returns the height of the given 3D position above (or below) the ellipsoid surface.
   * @param {Vector3} pos
   * @returns {number}
   */
  getPositionElevation(pos) {
    this.getPositionToSurfacePoint(pos, _vec2);
    const heightDelta = _vec22.subVectors(pos, _vec2);
    return Math.sign(heightDelta.dot(pos)) * heightDelta.length();
  }
  /**
   * Returns an estimate of the closest point on the ellipsoid surface to the given ray.
   * Returns the exact surface intersection point if the ray intersects the ellipsoid.
   * @param {Ray} ray
   * @param {Vector3} target
   * @returns {Vector3}
   */
  closestPointToRayEstimate(ray, target) {
    if (this.intersectRay(ray, target)) {
      return target;
    } else {
      _matrix.makeScale(...this.radius).invert();
      _ray.copy(ray).applyMatrix4(_matrix);
      _vec2.set(0, 0, 0);
      _ray.closestPointToPoint(_vec2, target).normalize();
      _matrix.makeScale(...this.radius);
      return target.applyMatrix4(_matrix);
    }
  }
  /**
   * Copies the radius from the given ellipsoid into this one.
   * @param {Ellipsoid} source
   * @returns {this}
   */
  copy(source) {
    this.radius.copy(source.radius);
    return this;
  }
  /**
   * Returns a new Ellipsoid with the same radius as this one.
   * @returns {Ellipsoid}
   */
  clone() {
    return new this.constructor().copy(this);
  }
};

// build/three/renderer/math/GeoConstants.js
var WGS84_ELLIPSOID = new Ellipsoid(WGS84_RADIUS, WGS84_RADIUS, WGS84_HEIGHT);
WGS84_ELLIPSOID.name = "WGS84 Earth";

// build/three/renderer/loaders/I3DMLoader.js
var tempFwd = /* @__PURE__ */ new Vector35();
var tempUp = /* @__PURE__ */ new Vector35();
var tempRight = /* @__PURE__ */ new Vector35();
var tempPos = /* @__PURE__ */ new Vector35();
var tempQuat = /* @__PURE__ */ new Quaternion();
var tempSca = /* @__PURE__ */ new Vector35();
var tempMat = /* @__PURE__ */ new Matrix43();
var tempMat2 = /* @__PURE__ */ new Matrix43();
var tempGlobePos = /* @__PURE__ */ new Vector35();
var tempEnuFrame = /* @__PURE__ */ new Matrix43();
var tempLocalQuat = /* @__PURE__ */ new Quaternion();
var tempLatLon = {};
function octDecodeInRange(x, y, rangeMax, result) {
  x = x / rangeMax * 2 - 1;
  y = y / rangeMax * 2 - 1;
  result.x = x;
  result.y = y;
  result.z = 1 - Math.abs(x) - Math.abs(y);
  if (result.z < 0) {
    const oldX = result.x;
    result.x = (1 - Math.abs(result.y)) * (oldX >= 0 ? 1 : -1);
    result.y = (1 - Math.abs(oldX)) * (result.y >= 0 ? 1 : -1);
  }
  result.normalize();
  return result;
}
var I3DMLoader = class extends I3DMLoaderBase {
  constructor(manager = DefaultLoadingManager3) {
    super();
    this.manager = manager;
    this.adjustmentTransform = new Matrix43();
    this.ellipsoid = WGS84_ELLIPSOID.clone();
  }
  resolveExternalURL(url) {
    return this.manager.resolveURL(super.resolveExternalURL(url));
  }
  /**
   * Parses an i3dm buffer and resolves to a GLTF result object where the scene's
   * meshes have been replaced with `InstancedMesh` objects (one per GLTF mesh), with
   * metadata attached to both `model` and `model.scene`.
   * @param {ArrayBuffer} buffer
   * @returns {Promise<{ scene: Group, batchTable: BatchTable, featureTable: FeatureTable }>}
   */
  parse(buffer) {
    return super.parse(buffer).then((i3dm) => {
      const { featureTable, batchTable } = i3dm;
      const gltfBuffer = i3dm.glbBytes.slice().buffer;
      return new Promise((resolve, reject) => {
        const fetchOptions = this.fetchOptions;
        const manager = this.manager;
        const loader = manager.getHandler("path.gltf") || new GLTFLoader2(manager);
        if (fetchOptions.credentials === "include" && fetchOptions.mode === "cors") {
          loader.setCrossOrigin("use-credentials");
        }
        if ("credentials" in fetchOptions) {
          loader.setWithCredentials(fetchOptions.credentials === "include");
        }
        if (fetchOptions.headers) {
          loader.setRequestHeader(fetchOptions.headers);
        }
        let workingPath = i3dm.gltfWorkingPath ?? this.workingPath;
        if (!/[\\/]$/.test(workingPath)) {
          workingPath += "/";
        }
        const adjustmentTransform = this.adjustmentTransform;
        loader.parse(gltfBuffer, workingPath, (model) => {
          const INSTANCES_LENGTH = featureTable.getData("INSTANCES_LENGTH");
          let POSITION = featureTable.getData("POSITION", INSTANCES_LENGTH, "FLOAT", "VEC3");
          const POSITION_QUANTIZED = featureTable.getData("POSITION_QUANTIZED", INSTANCES_LENGTH, "UNSIGNED_SHORT", "VEC3");
          const QUANTIZED_VOLUME_OFFSET = featureTable.getData("QUANTIZED_VOLUME_OFFSET", 1, "FLOAT", "VEC3");
          const QUANTIZED_VOLUME_SCALE = featureTable.getData("QUANTIZED_VOLUME_SCALE", 1, "FLOAT", "VEC3");
          const NORMAL_UP = featureTable.getData("NORMAL_UP", INSTANCES_LENGTH, "FLOAT", "VEC3");
          const NORMAL_RIGHT = featureTable.getData("NORMAL_RIGHT", INSTANCES_LENGTH, "FLOAT", "VEC3");
          const NORMAL_UP_OCT32P = featureTable.getData("NORMAL_UP_OCT32P", INSTANCES_LENGTH, "UNSIGNED_SHORT", "VEC2");
          const NORMAL_RIGHT_OCT32P = featureTable.getData("NORMAL_RIGHT_OCT32P", INSTANCES_LENGTH, "UNSIGNED_SHORT", "VEC2");
          const SCALE_NON_UNIFORM = featureTable.getData("SCALE_NON_UNIFORM", INSTANCES_LENGTH, "FLOAT", "VEC3");
          const SCALE = featureTable.getData("SCALE", INSTANCES_LENGTH, "FLOAT", "SCALAR");
          const RTC_CENTER = featureTable.getData("RTC_CENTER", 1, "FLOAT", "VEC3");
          const EAST_NORTH_UP = featureTable.getData("EAST_NORTH_UP");
          if (!POSITION && POSITION_QUANTIZED) {
            POSITION = new Float32Array(INSTANCES_LENGTH * 3);
            for (let i = 0; i < INSTANCES_LENGTH; i++) {
              POSITION[i * 3 + 0] = QUANTIZED_VOLUME_OFFSET[0] + POSITION_QUANTIZED[i * 3 + 0] / 65535 * QUANTIZED_VOLUME_SCALE[0];
              POSITION[i * 3 + 1] = QUANTIZED_VOLUME_OFFSET[1] + POSITION_QUANTIZED[i * 3 + 1] / 65535 * QUANTIZED_VOLUME_SCALE[1];
              POSITION[i * 3 + 2] = QUANTIZED_VOLUME_OFFSET[2] + POSITION_QUANTIZED[i * 3 + 2] / 65535 * QUANTIZED_VOLUME_SCALE[2];
            }
          }
          const averageVector = new Vector35();
          for (let i = 0; i < INSTANCES_LENGTH; i++) {
            averageVector.x += POSITION[i * 3 + 0] / INSTANCES_LENGTH;
            averageVector.y += POSITION[i * 3 + 1] / INSTANCES_LENGTH;
            averageVector.z += POSITION[i * 3 + 2] / INSTANCES_LENGTH;
          }
          const instances = [];
          const meshes = [];
          model.scene.updateMatrixWorld();
          model.scene.traverse((child) => {
            if (child.isMesh) {
              meshes.push(child);
              const { geometry, material } = child;
              const instancedMesh = new InstancedMesh(geometry, material, INSTANCES_LENGTH);
              instancedMesh.position.copy(averageVector);
              if (RTC_CENTER) {
                instancedMesh.position.x += RTC_CENTER[0];
                instancedMesh.position.y += RTC_CENTER[1];
                instancedMesh.position.z += RTC_CENTER[2];
              }
              instances.push(instancedMesh);
            }
          });
          for (let i = 0; i < INSTANCES_LENGTH; i++) {
            tempPos.set(
              POSITION[i * 3 + 0] - averageVector.x,
              POSITION[i * 3 + 1] - averageVector.y,
              POSITION[i * 3 + 2] - averageVector.z
            );
            tempQuat.identity();
            if (NORMAL_UP && NORMAL_RIGHT) {
              tempUp.set(
                NORMAL_UP[i * 3 + 0],
                NORMAL_UP[i * 3 + 1],
                NORMAL_UP[i * 3 + 2]
              );
              tempRight.set(
                NORMAL_RIGHT[i * 3 + 0],
                NORMAL_RIGHT[i * 3 + 1],
                NORMAL_RIGHT[i * 3 + 2]
              );
              tempFwd.crossVectors(tempRight, tempUp).normalize();
              tempMat.makeBasis(
                tempRight,
                tempUp,
                tempFwd
              );
              tempQuat.setFromRotationMatrix(tempMat);
            } else if (NORMAL_UP_OCT32P && NORMAL_RIGHT_OCT32P) {
              octDecodeInRange(
                NORMAL_UP_OCT32P[i * 2 + 0],
                NORMAL_UP_OCT32P[i * 2 + 1],
                65535,
                tempUp
              );
              octDecodeInRange(
                NORMAL_RIGHT_OCT32P[i * 2 + 0],
                NORMAL_RIGHT_OCT32P[i * 2 + 1],
                65535,
                tempRight
              );
              tempFwd.crossVectors(tempRight, tempUp).normalize();
              tempMat.makeBasis(
                tempRight,
                tempUp,
                tempFwd
              );
              tempQuat.setFromRotationMatrix(tempMat);
            }
            tempSca.set(1, 1, 1);
            if (SCALE_NON_UNIFORM) {
              tempSca.set(
                SCALE_NON_UNIFORM[i * 3 + 0],
                SCALE_NON_UNIFORM[i * 3 + 1],
                SCALE_NON_UNIFORM[i * 3 + 2]
              );
            }
            if (SCALE) {
              tempSca.multiplyScalar(SCALE[i]);
            }
            for (let j = 0, l = instances.length; j < l; j++) {
              const instance = instances[j];
              tempLocalQuat.copy(tempQuat);
              if (EAST_NORTH_UP) {
                instance.updateMatrixWorld();
                tempGlobePos.copy(tempPos).applyMatrix4(instance.matrixWorld);
                this.ellipsoid.getPositionToCartographic(tempGlobePos, tempLatLon);
                this.ellipsoid.getEastNorthUpFrame(tempLatLon.lat, tempLatLon.lon, tempEnuFrame);
                tempLocalQuat.setFromRotationMatrix(tempEnuFrame);
              }
              tempMat.compose(tempPos, tempLocalQuat, tempSca).multiply(adjustmentTransform);
              const mesh = meshes[j];
              tempMat2.multiplyMatrices(tempMat, mesh.matrixWorld);
              instance.setMatrixAt(i, tempMat2);
            }
          }
          model.scene.clear();
          model.scene.add(...instances);
          model.batchTable = batchTable;
          model.featureTable = featureTable;
          model.scene.batchTable = batchTable;
          model.scene.featureTable = featureTable;
          resolve(model);
        }, reject);
      });
    });
  }
};

// build/three/renderer/loaders/CMPTLoader.js
import { Group, DefaultLoadingManager as DefaultLoadingManager4, Matrix4 as Matrix44 } from "three";
var CMPTLoader = class extends CMPTLoaderBase {
  constructor(manager = DefaultLoadingManager4) {
    super();
    this.manager = manager;
    this.adjustmentTransform = new Matrix44();
    this.ellipsoid = WGS84_ELLIPSOID.clone();
  }
  /**
   * Parses a cmpt buffer and resolves to an object containing a `Group` with all
   * sub-tile scenes added as children, and the individual sub-tile results.
   * @param {ArrayBuffer} buffer
   * @returns {Promise<{ scene: Group, tiles: Array }>}
   */
  parse(buffer) {
    const result = super.parse(buffer);
    const { manager, ellipsoid, adjustmentTransform } = this;
    const promises = [];
    for (const i in result.tiles) {
      const { type, buffer: buffer2 } = result.tiles[i];
      switch (type) {
        case "b3dm": {
          const slicedBuffer = buffer2.slice();
          const loader = new B3DMLoader(manager);
          loader.workingPath = this.workingPath;
          loader.fetchOptions = this.fetchOptions;
          loader.adjustmentTransform.copy(adjustmentTransform);
          const promise = loader.parse(slicedBuffer.buffer);
          promises.push(promise);
          break;
        }
        case "pnts": {
          const slicedBuffer = buffer2.slice();
          const loader = new PNTSLoader(manager);
          loader.workingPath = this.workingPath;
          loader.fetchOptions = this.fetchOptions;
          const promise = loader.parse(slicedBuffer.buffer);
          promises.push(promise);
          break;
        }
        case "i3dm": {
          const slicedBuffer = buffer2.slice();
          const loader = new I3DMLoader(manager);
          loader.workingPath = this.workingPath;
          loader.fetchOptions = this.fetchOptions;
          loader.ellipsoid.copy(ellipsoid);
          loader.adjustmentTransform.copy(adjustmentTransform);
          const promise = loader.parse(slicedBuffer.buffer);
          promises.push(promise);
          break;
        }
      }
    }
    return Promise.all(promises).then((results) => {
      const group = new Group();
      results.forEach((result2) => {
        group.add(result2.scene);
      });
      return {
        tiles: results,
        scene: group
      };
    });
  }
};

// build/three/renderer/tiles/TilesGroup.js
import { Group as Group2, Matrix4 as Matrix45 } from "three";
var tempMat3 = /* @__PURE__ */ new Matrix45();
var TilesGroup = class extends Group2 {
  constructor(tilesRenderer) {
    super();
    this.isTilesGroup = true;
    this.name = "TilesRenderer.TilesGroup";
    this.tilesRenderer = tilesRenderer;
    this.matrixWorldInverse = new Matrix45();
  }
  raycast(raycaster, intersects) {
    this.tilesRenderer.raycast(raycaster, intersects);
    return false;
  }
  updateMatrixWorld(force) {
    if (this.matrixAutoUpdate) {
      this.updateMatrix();
    }
    if (this.matrixWorldNeedsUpdate || force) {
      if (this.parent === null) {
        tempMat3.copy(this.matrix);
      } else {
        tempMat3.multiplyMatrices(this.parent.matrixWorld, this.matrix);
      }
      this.matrixWorldNeedsUpdate = false;
      const elA = tempMat3.elements;
      const elB = this.matrixWorld.elements;
      let isDifferent = false;
      for (let i = 0; i < 16; i++) {
        const itemA = elA[i];
        const itemB = elB[i];
        const diff = Math.abs(itemA - itemB);
        if (diff > Number.EPSILON) {
          isDifferent = true;
          break;
        }
      }
      if (isDifferent) {
        this.matrixWorld.copy(tempMat3);
        this.matrixWorldInverse.copy(tempMat3).invert();
        const children = this.children;
        for (let i = 0, l = children.length; i < l; i++) {
          children[i].updateMatrixWorld();
        }
        const { tilesRenderer } = this;
        const { activeTiles, visibleTiles } = tilesRenderer;
        activeTiles.forEach((tile) => {
          if (!visibleTiles.has(tile)) {
            const { scene } = tile.engineData;
            scene.traverse((c) => {
              c.updateMatrix();
              c.matrixWorld.copy(c.matrix);
              if (c.parent) {
                c.matrixWorld.premultiply(c.parent.matrixWorld);
              } else {
                c.matrixWorld.premultiply(this.matrixWorld);
              }
            });
          }
        });
      }
    }
  }
  updateWorldMatrix(updateParents, updateChildren) {
    if (this.parent && updateParents) {
      this.parent.updateWorldMatrix(updateParents, false);
    }
    this.updateMatrixWorld(true);
  }
};

// build/three/renderer/tiles/TilesRenderer.js
import {
  Matrix4 as Matrix48,
  Vector3 as Vector311,
  Vector2 as Vector22,
  LoadingManager,
  EventDispatcher,
  Group as Group3
} from "three";

// build/three/renderer/tiles/raycastTraverse.js
import { Ray as Ray2, Vector3 as Vector36 } from "three";
var _localRay = /* @__PURE__ */ new Ray2();
function intersectTileScene(tile, raycaster, renderer, intersects) {
  const { scene } = tile.engineData;
  const didRaycast = renderer.invokeOnePlugin((plugin) => plugin.raycastTile && plugin.raycastTile(tile, scene, raycaster, intersects));
  if (!didRaycast) {
    raycaster.intersectObject(scene, true, intersects);
  }
}
function isTileInitialized(tile) {
  return "traversal" in tile;
}
function raycastTraverse(renderer, tile, raycaster, intersects, localRay = null) {
  if (!isTileInitialized(tile)) {
    return;
  }
  const { group, activeTiles } = renderer;
  const { boundingVolume } = tile.engineData;
  if (localRay === null) {
    localRay = _localRay;
    localRay.copy(raycaster.ray).applyMatrix4(group.matrixWorldInverse);
  }
  if (!tile.traversal.used || !boundingVolume.intersectsRay(localRay)) {
    return;
  }
  if (activeTiles.has(tile)) {
    intersectTileScene(tile, raycaster, renderer, intersects);
  }
  const children = tile.children;
  for (let i = 0, l = children.length; i < l; i++) {
    raycastTraverse(renderer, children[i], raycaster, intersects, localRay);
  }
}

// build/three/renderer/math/TileBoundingVolume.js
import { Vector3 as Vector39, Sphere as Sphere2 } from "three";

// build/three/renderer/math/OBB.js
import { Matrix4 as Matrix46, Box3, Vector3 as Vector37, Plane, Ray as Ray3 } from "three";
var _worldMin = /* @__PURE__ */ new Vector37();
var _worldMax = /* @__PURE__ */ new Vector37();
var _norm2 = /* @__PURE__ */ new Vector37();
var _ray2 = /* @__PURE__ */ new Ray3();
var OBB = class {
  constructor(box = new Box3(), transform = new Matrix46()) {
    this.box = box.clone();
    this.transform = transform.clone();
    this.inverseTransform = new Matrix46();
    this.points = new Array(8).fill().map(() => new Vector37());
    this.planes = new Array(6).fill().map(() => new Plane());
  }
  copy(source) {
    this.box.copy(source.box);
    this.transform.copy(source.transform);
    this.update();
    return this;
  }
  clone() {
    return new this.constructor().copy(this);
  }
  /**
   * Clamps the given point within the bounds of this OBB
   * @param {Vector3} point
   * @param {Vector3} result
   * @returns {Vector3}
   */
  clampPoint(point, result) {
    return result.copy(point).applyMatrix4(this.inverseTransform).clamp(this.box.min, this.box.max).applyMatrix4(this.transform);
  }
  /**
   * Returns the distance from any edge of this OBB to the specified point.
   * If the point lies inside of this box, the distance will be 0.
   * @param {Vector3} point
   * @returns {number}
   */
  distanceToPoint(point) {
    return this.clampPoint(point, _norm2).distanceTo(point);
  }
  containsPoint(point) {
    _norm2.copy(point).applyMatrix4(this.inverseTransform);
    return this.box.containsPoint(_norm2);
  }
  // returns boolean indicating whether the ray has intersected the obb
  intersectsRay(ray) {
    _ray2.copy(ray).applyMatrix4(this.inverseTransform);
    return _ray2.intersectsBox(this.box);
  }
  // Sets "target" equal to the intersection point.
  // Returns "null" if no intersection found.
  intersectRay(ray, target) {
    _ray2.copy(ray).applyMatrix4(this.inverseTransform);
    if (_ray2.intersectBox(this.box, target)) {
      target.applyMatrix4(this.transform);
      return target;
    } else {
      return null;
    }
  }
  update() {
    const { points, inverseTransform, transform, box } = this;
    inverseTransform.copy(transform).invert();
    const { min, max } = box;
    let index = 0;
    for (let x = -1; x <= 1; x += 2) {
      for (let y = -1; y <= 1; y += 2) {
        for (let z = -1; z <= 1; z += 2) {
          points[index].set(
            x < 0 ? min.x : max.x,
            y < 0 ? min.y : max.y,
            z < 0 ? min.z : max.z
          ).applyMatrix4(transform);
          index++;
        }
      }
    }
    this.updatePlanes();
  }
  updatePlanes() {
    _worldMin.copy(this.box.min).applyMatrix4(this.transform);
    _worldMax.copy(this.box.max).applyMatrix4(this.transform);
    _norm2.set(0, 0, 1).transformDirection(this.transform);
    this.planes[0].setFromNormalAndCoplanarPoint(_norm2, _worldMin);
    this.planes[1].setFromNormalAndCoplanarPoint(_norm2, _worldMax).negate();
    _norm2.set(0, 1, 0).transformDirection(this.transform);
    this.planes[2].setFromNormalAndCoplanarPoint(_norm2, _worldMin);
    this.planes[3].setFromNormalAndCoplanarPoint(_norm2, _worldMax).negate();
    _norm2.set(1, 0, 0).transformDirection(this.transform);
    this.planes[4].setFromNormalAndCoplanarPoint(_norm2, _worldMin);
    this.planes[5].setFromNormalAndCoplanarPoint(_norm2, _worldMax).negate();
  }
  intersectsSphere(sphere) {
    this.clampPoint(sphere.center, _norm2);
    return _norm2.distanceToSquared(sphere.center) <= sphere.radius * sphere.radius;
  }
  intersectsFrustum(frustum) {
    return this._intersectsPlaneShape(frustum.planes, frustum.points);
  }
  intersectsOBB(obb) {
    return this._intersectsPlaneShape(obb.planes, obb.points);
  }
  // takes a series of 6 planes that define and enclosed shape and the 8 points that lie at the corners
  // of that shape to determine whether the OBB is intersected with.
  _intersectsPlaneShape(otherPlanes, otherPoints) {
    const thisPoints = this.points;
    const thisPlanes = this.planes;
    for (let i = 0; i < 6; i++) {
      const plane = otherPlanes[i];
      let maxDistance = -Infinity;
      for (let j = 0; j < 8; j++) {
        const v = thisPoints[j];
        const dist = plane.distanceToPoint(v);
        maxDistance = maxDistance < dist ? dist : maxDistance;
      }
      if (maxDistance < 0) {
        return false;
      }
    }
    for (let i = 0; i < 6; i++) {
      const plane = thisPlanes[i];
      let maxDistance = -Infinity;
      for (let j = 0; j < 8; j++) {
        const v = otherPoints[j];
        const dist = plane.distanceToPoint(v);
        maxDistance = maxDistance < dist ? dist : maxDistance;
      }
      if (maxDistance < 0) {
        return false;
      }
    }
    return true;
  }
};

// build/three/renderer/math/EllipsoidRegion.js
import { Matrix4 as Matrix47, Vector3 as Vector38, Box3 as Box32 } from "three";
var INFLATE_EPSILON = 1e-13;
var PI = Math.PI;
var HALF_PI = PI / 2;
var _orthoX = /* @__PURE__ */ new Vector38();
var _orthoY = /* @__PURE__ */ new Vector38();
var _orthoZ = /* @__PURE__ */ new Vector38();
var _vec3 = /* @__PURE__ */ new Vector38();
var _invMatrix = /* @__PURE__ */ new Matrix47();
var _box = /* @__PURE__ */ new Box32();
var _matrix3 = /* @__PURE__ */ new Matrix47();
function expandSphereRadiusSquared(vec, target) {
  target.radius = Math.max(target.radius, vec.distanceToSquared(target.center));
}
function isTriaxial(radii) {
  return radii.x !== radii.y;
}
var EllipsoidRegion = class extends Ellipsoid {
  constructor(x = 1, y = 1, z = 1, latStart = -HALF_PI, latEnd = HALF_PI, lonStart = 0, lonEnd = 2 * PI, heightStart = 0, heightEnd = 0) {
    super(x, y, z);
    this.latStart = latStart;
    this.latEnd = latEnd;
    this.lonStart = lonStart;
    this.lonEnd = lonEnd;
    this.heightStart = heightStart;
    this.heightEnd = heightEnd;
  }
  /**
   * Computes an oriented bounding box for this region. Writes the box extents into `box` and
   * the orientation frame into `matrix`.
   * @param {Box3} box
   * @param {Matrix4} matrix
   */
  getBoundingBox(box, matrix) {
    if (isTriaxial(this.radius)) {
      console.warn("EllipsoidRegion: Triaxial ellipsoids are not supported.");
    }
    const {
      latStart,
      latEnd,
      lonStart,
      lonEnd,
      heightStart,
      heightEnd
    } = this;
    const latMid = (latStart + latEnd) * 0.5;
    const lonMid = (lonStart + lonEnd) * 0.5;
    const allAboveEquator = latStart > 0;
    const allBelowEquator = latEnd < 0;
    let nearEquatorLat;
    if (allAboveEquator) {
      nearEquatorLat = latStart;
    } else if (allBelowEquator) {
      nearEquatorLat = latEnd;
    } else {
      nearEquatorLat = 0;
    }
    const { min, max } = box;
    min.setScalar(Infinity);
    max.setScalar(-Infinity);
    if (lonEnd - lonStart <= PI) {
      this.getCartographicToNormal(latMid, lonMid, _orthoZ);
      _orthoY.set(0, 0, 1);
      _orthoX.crossVectors(_orthoY, _orthoZ).normalize();
      _orthoY.crossVectors(_orthoZ, _orthoX).normalize();
      matrix.makeBasis(_orthoX, _orthoY, _orthoZ);
      _invMatrix.copy(matrix).invert();
      this.getCartographicToPosition(nearEquatorLat, lonStart, heightEnd, _vec3).applyMatrix4(_invMatrix);
      max.x = Math.abs(_vec3.x);
      min.x = -max.x;
      this.getCartographicToPosition(latEnd, lonStart, heightEnd, _vec3).applyMatrix4(_invMatrix);
      max.y = _vec3.y;
      this.getCartographicToPosition(latEnd, lonMid, heightEnd, _vec3).applyMatrix4(_invMatrix);
      max.y = Math.max(_vec3.y, max.y);
      this.getCartographicToPosition(latStart, lonStart, heightEnd, _vec3).applyMatrix4(_invMatrix);
      min.y = _vec3.y;
      this.getCartographicToPosition(latStart, lonMid, heightEnd, _vec3).applyMatrix4(_invMatrix);
      min.y = Math.min(_vec3.y, min.y);
      this.getCartographicToPosition(latMid, lonMid, heightEnd, _vec3).applyMatrix4(_invMatrix);
      max.z = _vec3.z;
      this.getCartographicToPosition(latStart, lonStart, heightStart, _vec3).applyMatrix4(_invMatrix);
      min.z = _vec3.z;
      this.getCartographicToPosition(latEnd, lonStart, heightStart, _vec3).applyMatrix4(_invMatrix);
      min.z = Math.min(_vec3.z, min.z);
    } else {
      this.getCartographicToPosition(nearEquatorLat, lonMid, heightEnd, _orthoZ);
      _orthoZ.z = 0;
      if (_orthoZ.length() < 1e-10) {
        _orthoZ.set(1, 0, 0);
      } else {
        _orthoZ.normalize();
      }
      _orthoY.set(0, 0, 1);
      _orthoX.crossVectors(_orthoZ, _orthoY).normalize();
      matrix.makeBasis(_orthoX, _orthoY, _orthoZ);
      _invMatrix.copy(matrix).invert();
      this.getCartographicToPosition(nearEquatorLat, lonMid + HALF_PI, heightEnd, _vec3).applyMatrix4(_invMatrix);
      max.x = Math.abs(_vec3.x);
      min.x = -max.x;
      this.getCartographicToPosition(latEnd, 0, allBelowEquator ? heightStart : heightEnd, _vec3).applyMatrix4(_invMatrix);
      max.y = _vec3.y;
      this.getCartographicToPosition(latStart, 0, allAboveEquator ? heightStart : heightEnd, _vec3).applyMatrix4(_invMatrix);
      min.y = _vec3.y;
      this.getCartographicToPosition(nearEquatorLat, lonMid, heightEnd, _vec3).applyMatrix4(_invMatrix);
      max.z = _vec3.z;
      this.getCartographicToPosition(nearEquatorLat, lonEnd, heightEnd, _vec3).applyMatrix4(_invMatrix);
      min.z = _vec3.z;
    }
    box.getCenter(_vec3);
    box.min.sub(_vec3).multiplyScalar(1 + INFLATE_EPSILON);
    box.max.sub(_vec3).multiplyScalar(1 + INFLATE_EPSILON);
    _vec3.applyMatrix4(matrix);
    matrix.setPosition(_vec3);
  }
  /**
   * Computes a bounding sphere for this region. Writes the result into `sphere`.
   * @param {Sphere} sphere
   */
  getBoundingSphere(sphere) {
    if (isTriaxial(this.radius)) {
      console.warn("EllipsoidRegion: Triaxial ellipsoids are not supported.");
    }
    this.getBoundingBox(_box, _matrix3);
    sphere.center.setFromMatrixPosition(_matrix3);
    sphere.radius = 0;
    const {
      latStart,
      latEnd,
      lonStart,
      lonEnd,
      heightStart,
      heightEnd
    } = this;
    const latMid = (latStart + latEnd) * 0.5;
    const lonMid = (lonStart + lonEnd) * 0.5;
    const allAboveEquator = latStart > 0;
    const allBelowEquator = latEnd < 0;
    let nearEquatorLat;
    if (allAboveEquator) {
      nearEquatorLat = latStart;
    } else if (allBelowEquator) {
      nearEquatorLat = latEnd;
    } else {
      nearEquatorLat = 0;
    }
    this.getCartographicToPosition(nearEquatorLat, lonStart, heightEnd, _vec3);
    expandSphereRadiusSquared(_vec3, sphere);
    this.getCartographicToPosition(latEnd, lonStart, heightEnd, _vec3);
    expandSphereRadiusSquared(_vec3, sphere);
    this.getCartographicToPosition(latEnd, lonMid, heightEnd, _vec3);
    expandSphereRadiusSquared(_vec3, sphere);
    this.getCartographicToPosition(latStart, lonStart, heightEnd, _vec3);
    expandSphereRadiusSquared(_vec3, sphere);
    this.getCartographicToPosition(latStart, lonMid, heightEnd, _vec3);
    expandSphereRadiusSquared(_vec3, sphere);
    this.getCartographicToPosition(latMid, lonMid, heightEnd, _vec3);
    expandSphereRadiusSquared(_vec3, sphere);
    this.getCartographicToPosition(latStart, lonStart, heightStart, _vec3);
    expandSphereRadiusSquared(_vec3, sphere);
    if (lonEnd - lonStart > PI) {
      this.getCartographicToPosition(nearEquatorLat, lonMid + PI, heightEnd, _vec3);
      expandSphereRadiusSquared(_vec3, sphere);
    }
    sphere.radius = Math.sqrt(sphere.radius) * (1 + INFLATE_EPSILON);
  }
};

// build/three/renderer/math/TileBoundingVolume.js
var _vecX2 = /* @__PURE__ */ new Vector39();
var _vecY2 = /* @__PURE__ */ new Vector39();
var _vecZ2 = /* @__PURE__ */ new Vector39();
var _sphereVec = /* @__PURE__ */ new Vector39();
var _obbVec = /* @__PURE__ */ new Vector39();
var TileBoundingVolume = class {
  constructor() {
    this.sphere = null;
    this.obb = null;
    this.region = null;
    this.regionObb = null;
  }
  intersectsRay(ray) {
    const sphere = this.sphere;
    const obb = this.obb || this.regionObb;
    if (sphere && !ray.intersectsSphere(sphere)) {
      return false;
    }
    if (obb && !obb.intersectsRay(ray)) {
      return false;
    }
    return true;
  }
  intersectRay(ray, target = null) {
    const sphere = this.sphere;
    const obb = this.obb || this.regionObb;
    let sphereDistSq = -Infinity;
    let obbDistSq = -Infinity;
    if (sphere) {
      if (ray.intersectSphere(sphere, _sphereVec)) {
        sphereDistSq = sphere.containsPoint(ray.origin) ? 0 : ray.origin.distanceToSquared(_sphereVec);
      }
    }
    if (obb) {
      if (obb.intersectRay(ray, _obbVec)) {
        obbDistSq = obb.containsPoint(ray.origin) ? 0 : ray.origin.distanceToSquared(_obbVec);
      }
    }
    const furthestDist = Math.max(sphereDistSq, obbDistSq);
    if (furthestDist === -Infinity) {
      return null;
    }
    ray.at(Math.sqrt(furthestDist), target);
    return target;
  }
  distanceToPoint(point) {
    const sphere = this.sphere;
    const obb = this.obb || this.regionObb;
    let sphereDistance = -Infinity;
    let obbDistance = -Infinity;
    if (sphere) {
      sphereDistance = Math.max(sphere.distanceToPoint(point), 0);
    }
    if (obb) {
      obbDistance = obb.distanceToPoint(point);
    }
    return sphereDistance > obbDistance ? sphereDistance : obbDistance;
  }
  intersectsFrustum(frustum) {
    const obb = this.obb || this.regionObb;
    const sphere = this.sphere;
    if (sphere && !frustum.intersectsSphere(sphere)) {
      return false;
    }
    if (obb && !obb.intersectsFrustum(frustum)) {
      return false;
    }
    return Boolean(sphere || obb);
  }
  intersectsSphere(otherSphere) {
    const obb = this.obb || this.regionObb;
    const sphere = this.sphere;
    if (sphere && !sphere.intersectsSphere(otherSphere)) {
      return false;
    }
    if (obb && !obb.intersectsSphere(otherSphere)) {
      return false;
    }
    return Boolean(sphere || obb);
  }
  intersectsOBB(otherObb) {
    const obb = this.obb || this.regionObb;
    const sphere = this.sphere;
    if (sphere && !otherObb.intersectsSphere(sphere)) {
      return false;
    }
    if (obb && !obb.intersectsOBB(otherObb)) {
      return false;
    }
    return Boolean(sphere || obb);
  }
  getOBB(targetBox, targetMatrix) {
    const obb = this.obb || this.regionObb;
    if (obb) {
      targetBox.copy(obb.box);
      targetMatrix.copy(obb.transform);
    } else {
      this.getAABB(targetBox);
      targetMatrix.identity();
    }
  }
  getAABB(target) {
    if (this.sphere) {
      this.sphere.getBoundingBox(target);
    } else {
      const obb = this.obb || this.regionObb;
      target.copy(obb.box).applyMatrix4(obb.transform);
    }
  }
  getSphere(target) {
    if (this.sphere) {
      target.copy(this.sphere);
    } else if (this.region) {
      this.region.getBoundingSphere(target);
    } else {
      const obb = this.obb || this.regionObb;
      obb.box.getBoundingSphere(target);
      target.applyMatrix4(obb.transform);
    }
  }
  setObbData(data, transform) {
    const obb = new OBB();
    _vecX2.set(data[3], data[4], data[5]);
    _vecY2.set(data[6], data[7], data[8]);
    _vecZ2.set(data[9], data[10], data[11]);
    const scaleX = _vecX2.length();
    const scaleY = _vecY2.length();
    const scaleZ = _vecZ2.length();
    _vecX2.normalize();
    _vecY2.normalize();
    _vecZ2.normalize();
    if (scaleX === 0) {
      _vecX2.crossVectors(_vecY2, _vecZ2);
    }
    if (scaleY === 0) {
      _vecY2.crossVectors(_vecX2, _vecZ2);
    }
    if (scaleZ === 0) {
      _vecZ2.crossVectors(_vecX2, _vecY2);
    }
    obb.transform.set(
      _vecX2.x,
      _vecY2.x,
      _vecZ2.x,
      data[0],
      _vecX2.y,
      _vecY2.y,
      _vecZ2.y,
      data[1],
      _vecX2.z,
      _vecY2.z,
      _vecZ2.z,
      data[2],
      0,
      0,
      0,
      1
    ).premultiply(transform);
    obb.box.min.set(-scaleX, -scaleY, -scaleZ);
    obb.box.max.set(scaleX, scaleY, scaleZ);
    obb.update();
    this.obb = obb;
  }
  setSphereData(x, y, z, radius, transform) {
    const sphere = new Sphere2();
    sphere.center.set(x, y, z);
    sphere.radius = radius;
    sphere.applyMatrix4(transform);
    this.sphere = sphere;
  }
  setRegionData(ellipsoid, west, south, east, north, minHeight, maxHeight) {
    const region = new EllipsoidRegion(
      ...ellipsoid.radius,
      south,
      north,
      west,
      east,
      minHeight,
      maxHeight
    );
    const obb = new OBB();
    region.getBoundingBox(obb.box, obb.transform);
    obb.update();
    this.region = region;
    this.regionObb = obb;
  }
};

// build/three/renderer/math/ExtendedFrustum.js
import { Frustum, Matrix3, Vector3 as Vector310 } from "three";
var _mat3 = /* @__PURE__ */ new Matrix3();
function findIntersectionPoint(plane1, plane2, plane3, target) {
  const A = _mat3.set(
    plane1.normal.x,
    plane1.normal.y,
    plane1.normal.z,
    plane2.normal.x,
    plane2.normal.y,
    plane2.normal.z,
    plane3.normal.x,
    plane3.normal.y,
    plane3.normal.z
  );
  target.set(-plane1.constant, -plane2.constant, -plane3.constant);
  target.applyMatrix3(A.invert());
  return target;
}
var ExtendedFrustum = class extends Frustum {
  constructor() {
    super();
    this.points = Array(8).fill().map(() => new Vector310());
  }
  setFromProjectionMatrix(...args) {
    super.setFromProjectionMatrix(...args);
    this.calculateFrustumPoints();
    return this;
  }
  calculateFrustumPoints() {
    const { planes, points } = this;
    const planeIntersections = [
      [planes[0], planes[3], planes[4]],
      // Near top left
      [planes[1], planes[3], planes[4]],
      // Near top right
      [planes[0], planes[2], planes[4]],
      // Near bottom left
      [planes[1], planes[2], planes[4]],
      // Near bottom right
      [planes[0], planes[3], planes[5]],
      // Far top left
      [planes[1], planes[3], planes[5]],
      // Far top right
      [planes[0], planes[2], planes[5]],
      // Far bottom left
      [planes[1], planes[2], planes[5]]
      // Far bottom right
    ];
    planeIntersections.forEach((planes2, index) => {
      findIntersectionPoint(planes2[0], planes2[1], planes2[2], points[index]);
    });
  }
};

// build/three/renderer/utils/MemoryUtils.js
var MemoryUtils_exports = {};
__export(MemoryUtils_exports, {
  estimateBytesUsed: () => estimateBytesUsed,
  getTextureByteLength: () => getTextureByteLength
});
import { estimateBytesUsed as _estimateBytesUsed } from "three/addons/utils/BufferGeometryUtils.js";
import { TextureUtils } from "three";
var UNKNOWN_TEXTURE_BYTE_LENGTH = 0;
function getFormatByteLength(width, height, format, type) {
  try {
    return TextureUtils.getByteLength(width, height, format, type);
  } catch {
    return UNKNOWN_TEXTURE_BYTE_LENGTH;
  }
}
function getTextureByteLength(tex) {
  if (!tex) {
    return 0;
  }
  if (tex.isExternalTexture) {
    return tex.userData?.byteLength ?? UNKNOWN_TEXTURE_BYTE_LENGTH;
  }
  const { format, type, image, mipmaps } = tex;
  if (tex.isCompressedTexture && Array.isArray(mipmaps) && mipmaps.length > 0) {
    let bytes2 = 0;
    for (const mip of mipmaps) {
      if (mip?.data?.byteLength) {
        bytes2 += mip.data.byteLength;
      } else {
        bytes2 += getFormatByteLength(mip.width, mip.height, format, type);
      }
    }
    return bytes2;
  }
  if (!image) {
    return UNKNOWN_TEXTURE_BYTE_LENGTH;
  }
  let bytes = getFormatByteLength(image.width, image.height, format, type);
  bytes *= tex.generateMipmaps ? 4 / 3 : 1;
  return bytes;
}
function estimateBytesUsed(object) {
  const dedupeSet = /* @__PURE__ */ new Set();
  let totalBytes = 0;
  object.traverse((c) => {
    if (c.geometry && !dedupeSet.has(c.geometry)) {
      totalBytes += _estimateBytesUsed(c.geometry);
      dedupeSet.add(c.geometry);
    }
    if (c.material) {
      const material = c.material;
      for (const key in material) {
        const value = material[key];
        if (value && value.isTexture && !dedupeSet.has(value)) {
          totalBytes += getTextureByteLength(value);
          dedupeSet.add(value);
        }
      }
    }
  });
  return totalBytes;
}

// build/three/renderer/tiles/TilesRenderer.js
import { GLTFLoader as GLTFLoader3 } from "three/addons/loaders/GLTFLoader.js";
var INITIAL_FRUSTUM_CULLED = /* @__PURE__ */ Symbol("INITIAL_FRUSTUM_CULLED");
var tempMat4 = /* @__PURE__ */ new Matrix48();
var tempVector = /* @__PURE__ */ new Vector311();
var tempVector2 = /* @__PURE__ */ new Vector22();
var X_AXIS = /* @__PURE__ */ new Vector311(1, 0, 0);
var Y_AXIS = /* @__PURE__ */ new Vector311(0, 1, 0);
function updateFrustumCulled(object, toInitialValue) {
  object.traverse((c) => {
    c.frustumCulled = c[INITIAL_FRUSTUM_CULLED] && toInitialValue;
  });
}
var TilesRenderer = class extends TilesRendererBase {
  /**
   * If `true`, all tile meshes automatically have `frustumCulled` set to `false` since the
   * tiles renderer performs its own frustum culling. If `displayActiveTiles` is `true` or
   * multiple cameras are being used, consider setting this to `false`.
   * @type {boolean}
   * @default true
   */
  get autoDisableRendererCulling() {
    return this._autoDisableRendererCulling;
  }
  set autoDisableRendererCulling(value) {
    if (this._autoDisableRendererCulling !== value) {
      super._autoDisableRendererCulling = value;
      this.forEachLoadedModel((scene) => {
        updateFrustumCulled(scene, !value);
      });
    }
  }
  constructor(...args) {
    super(...args);
    this.accelerateRaycast = true;
    this.group = new TilesGroup(this);
    this.ellipsoid = WGS84_ELLIPSOID.clone();
    this.cameras = [];
    this.cameraMap = /* @__PURE__ */ new Map();
    this.cameraInfo = [];
    this._upRotationMatrix = new Matrix48();
    this._bytesUsed = /* @__PURE__ */ new WeakMap();
    this._autoDisableRendererCulling = true;
    this.manager = new LoadingManager();
    this._listeners = {};
  }
  addEventListener(type, listener) {
    EventDispatcher.prototype.addEventListener.call(this, type, listener);
  }
  hasEventListener(type, listener) {
    return EventDispatcher.prototype.hasEventListener.call(this, type, listener);
  }
  removeEventListener(type, listener) {
    EventDispatcher.prototype.removeEventListener.call(this, type, listener);
  }
  dispatchEvent(e) {
    EventDispatcher.prototype.dispatchEvent.call(this, e);
  }
  /* Public API */
  /**
   * Returns the axis-aligned bounding box of the root tile in the group's local space.
   * @param {Box3} target - Target box to write into.
   * @returns {boolean} Whether the tileset is loaded and a bounding box is available.
   */
  getBoundingBox(target) {
    if (!this.root) {
      return false;
    }
    const boundingVolume = this.root.engineData.boundingVolume;
    if (boundingVolume) {
      boundingVolume.getAABB(target);
      return true;
    } else {
      return false;
    }
  }
  /**
   * Returns the oriented bounding box and transform of the root tile.
   * @param {Box3} targetBox - Target box to write into (in local OBB space).
   * @param {Matrix4} targetMatrix - Transform from OBB local space to group local space.
   * @returns {boolean} Whether the tileset is loaded and an OBB is available.
   */
  getOrientedBoundingBox(targetBox, targetMatrix) {
    if (!this.root) {
      return false;
    }
    const boundingVolume = this.root.engineData.boundingVolume;
    if (boundingVolume) {
      boundingVolume.getOBB(targetBox, targetMatrix);
      return true;
    } else {
      return false;
    }
  }
  /**
   * Returns the bounding sphere of the root tile in the group's local space.
   * @param {Sphere} target - Target sphere to write into.
   * @returns {boolean} Whether the tileset is loaded and a bounding sphere is available.
   */
  getBoundingSphere(target) {
    if (!this.root) {
      return false;
    }
    const boundingVolume = this.root.engineData.boundingVolume;
    if (boundingVolume) {
      boundingVolume.getSphere(target);
      return true;
    } else {
      return false;
    }
  }
  /**
   * Iterates over all currently loaded tile scenes.
   * @param {Function} callback - Called with `( scene: Object3D, tile: object )` for each loaded tile.
   */
  forEachLoadedModel(callback) {
    this.traverse((tile) => {
      const scene = tile.engineData && tile.engineData.scene;
      if (scene) {
        callback(scene, tile);
      }
    }, null, false);
  }
  /**
   * Performs a raycast against all loaded tile scenes. Compatible with Three.js raycasting.
   * Supports `raycaster.firstHitOnly` for early termination.
   * @param {Raycaster} raycaster
   * @param {Array} intersects - Array to push intersection results into.
   */
  raycast(raycaster, intersects) {
    if (!this.root) {
      return;
    }
    if (this.accelerateRaycast) {
      raycastTraverse(this, this.root, raycaster, intersects);
    } else {
      const hits = raycaster.firstHitOnly ? [] : intersects;
      for (const tile of this.activeTiles) {
        const { scene } = tile.engineData;
        if (!this.invokeOnePlugin((plugin) => {
          return plugin.raycastTile && plugin.raycastTile(tile, scene, raycaster, hits);
        })) {
          raycaster.intersectObject(scene, true, hits);
        }
      }
      if (raycaster.firstHitOnly && hits.length > 0) {
        hits.sort((a, b) => a.distance - b.distance);
        intersects.push(hits[0]);
      }
    }
  }
  /**
   * Returns whether the given camera is registered with this renderer.
   * @param {Camera} camera
   * @returns {boolean}
   */
  hasCamera(camera) {
    return this.cameraMap.has(camera);
  }
  /**
   * Registers a camera with the renderer so it is used for tile selection and screen-space error
   * calculation. Use `setResolution` or `setResolutionFromRenderer` to provide the camera's resolution.
   * @param {Camera} camera
   * @returns {boolean} Whether the camera was newly added.
   */
  setCamera(camera) {
    const cameras = this.cameras;
    const cameraMap = this.cameraMap;
    if (!cameraMap.has(camera)) {
      cameraMap.set(camera, new Vector22());
      cameras.push(camera);
      this.dispatchEvent({ type: "add-camera", camera });
      return true;
    }
    return false;
  }
  /**
   * Sets the render resolution for a registered camera, used for screen-space error calculation.
   * @param {Camera} camera - A previously registered camera.
   * @param {number|Vector2} xOrVec - Render width in pixels, or a Vector2 containing width and height.
   * @param {number} [y] - Render height in pixels when `xOrVec` is a number.
   * @returns {boolean} Whether the camera is registered and the resolution was updated.
   */
  setResolution(camera, xOrVec, y) {
    const cameraMap = this.cameraMap;
    if (!cameraMap.has(camera)) {
      return false;
    }
    const width = xOrVec.isVector2 ? xOrVec.x : xOrVec;
    const height = xOrVec.isVector2 ? xOrVec.y : y;
    const cameraVec = cameraMap.get(camera);
    if (cameraVec.width !== width || cameraVec.height !== height) {
      cameraVec.set(width, height);
      this.dispatchEvent({ type: "camera-resolution-change" });
    }
    return true;
  }
  /**
   * Returns the render resolution previously set for a registered camera.
   * @param {Camera} camera - A previously registered camera.
   * @param {Vector2} target - Vector2 to write the result into.
   * @returns {Vector2|null} The target with width/height filled in, or null if the camera is not registered.
   */
  getResolution(camera, target) {
    const vec = this.cameraMap.get(camera);
    if (!vec) return null;
    return target.copy(vec);
  }
  /**
   * Sets the render resolution for a camera by reading the current size from a WebGLRenderer.
   * @param {Camera} camera - A previously registered camera.
   * @param {WebGLRenderer} renderer
   * @returns {boolean} Whether the camera is registered and the resolution was updated.
   */
  setResolutionFromRenderer(camera, renderer) {
    renderer.getSize(tempVector2);
    return this.setResolution(camera, tempVector2.x, tempVector2.y);
  }
  /**
   * Unregisters a camera from the renderer.
   * @param {Camera} camera
   * @returns {boolean} Whether the camera was found and removed.
   */
  deleteCamera(camera) {
    const cameras = this.cameras;
    const cameraMap = this.cameraMap;
    if (cameraMap.has(camera)) {
      const index = cameras.indexOf(camera);
      cameras.splice(index, 1);
      cameraMap.delete(camera);
      this.dispatchEvent({ type: "delete-camera", camera });
      return true;
    }
    return false;
  }
  /* Overriden */
  loadRootTileset(...args) {
    return super.loadRootTileset(...args).then((root) => {
      const { asset, extensions = {} } = root;
      const upAxis = asset && asset.gltfUpAxis || "y";
      switch (upAxis.toLowerCase()) {
        case "x":
          this._upRotationMatrix.makeRotationAxis(Y_AXIS, -Math.PI / 2);
          break;
        case "y":
          this._upRotationMatrix.makeRotationAxis(X_AXIS, Math.PI / 2);
          break;
      }
      if ("3DTILES_ellipsoid" in extensions) {
        const ext = extensions["3DTILES_ellipsoid"];
        const { ellipsoid } = this;
        ellipsoid.name = ext.body;
        if (ext.radii) {
          ellipsoid.radius.set(...ext.radii);
        } else {
          ellipsoid.radius.set(1, 1, 1);
        }
      }
      return root;
    });
  }
  prepareForTraversal() {
    const group = this.group;
    const cameras = this.cameras;
    const cameraMap = this.cameraMap;
    const cameraInfo = this.cameraInfo;
    while (cameraInfo.length > cameras.length) {
      cameraInfo.pop();
    }
    while (cameraInfo.length < cameras.length) {
      cameraInfo.push({
        frustum: new ExtendedFrustum(),
        isOrthographic: false,
        sseDenominator: -1,
        // used if isOrthographic:false
        position: new Vector311(),
        invScale: -1,
        pixelSize: 0
        // used if isOrthographic:true
      });
    }
    tempVector.setFromMatrixScale(group.matrixWorldInverse);
    if (Math.abs(Math.max(tempVector.x - tempVector.y, tempVector.x - tempVector.z)) > 1e-6) {
      console.warn("ThreeTilesRenderer : Non uniform scale used for tile which may cause issues when calculating screen space error.");
    }
    for (let i = 0, l = cameraInfo.length; i < l; i++) {
      const camera = cameras[i];
      const info = cameraInfo[i];
      const frustum = info.frustum;
      const position = info.position;
      const resolution = cameraMap.get(camera);
      if (resolution.width === 0 || resolution.height === 0) {
        console.warn("TilesRenderer: resolution for camera error calculation is not set.");
      }
      const projection = camera.projectionMatrix.elements;
      info.isOrthographic = projection[15] === 1;
      if (info.isOrthographic) {
        const w = 2 / projection[0];
        const h = 2 / projection[5];
        info.pixelSize = Math.max(h / resolution.height, w / resolution.width);
      } else {
        info.sseDenominator = 2 / projection[5] / resolution.height;
      }
      tempMat4.copy(group.matrixWorld);
      tempMat4.premultiply(camera.matrixWorldInverse);
      tempMat4.premultiply(camera.projectionMatrix);
      frustum.setFromProjectionMatrix(tempMat4, camera.coordinateSystem, camera.reversedDepth);
      position.set(0, 0, 0);
      position.applyMatrix4(camera.matrixWorld);
      position.applyMatrix4(group.matrixWorldInverse);
    }
  }
  update() {
    super.update();
    if (this.cameras.length === 0 && this.root) {
      let found = false;
      this.invokeAllPlugins((plugin) => found = found || Boolean(plugin !== this && plugin.calculateTileViewError));
      if (found === false) {
        console.warn("TilesRenderer: no cameras defined. Cannot update 3d tiles.");
      }
    }
  }
  preprocessNode(tile, tilesetDir, parentTile = null) {
    super.preprocessNode(tile, tilesetDir, parentTile);
    const transform = new Matrix48();
    if (tile.transform) {
      const transformArr = tile.transform;
      for (let i = 0; i < 16; i++) {
        transform.elements[i] = transformArr[i];
      }
    }
    if (parentTile) {
      transform.premultiply(parentTile.engineData.transform);
    }
    const transformInverse = new Matrix48().copy(transform).invert();
    const boundingVolume = new TileBoundingVolume();
    if ("sphere" in tile.boundingVolume) {
      boundingVolume.setSphereData(...tile.boundingVolume.sphere, transform);
    }
    if ("box" in tile.boundingVolume) {
      boundingVolume.setObbData(tile.boundingVolume.box, transform);
    }
    if ("region" in tile.boundingVolume) {
      boundingVolume.setRegionData(this.ellipsoid, ...tile.boundingVolume.region);
    }
    tile.engineData.transform = transform;
    tile.engineData.transformInverse = transformInverse;
    tile.engineData.boundingVolume = boundingVolume;
    tile.engineData.geometry = null;
    tile.engineData.materials = null;
    tile.engineData.textures = null;
  }
  async parseTile(buffer, tile, extension, url, abortSignal) {
    const engineData = tile.engineData;
    const workingPath = LoaderUtils_exports.getWorkingPath(url);
    const fetchOptions = this.fetchOptions;
    const manager = this.manager;
    let promise = null;
    const tileTransform = engineData.transform;
    const upRotationMatrix = this._upRotationMatrix;
    const fileType = (LoaderUtils_exports.readMagicBytes(buffer) || extension).toLowerCase();
    switch (fileType) {
      case "b3dm": {
        const loader = new B3DMLoader(manager);
        loader.workingPath = workingPath;
        loader.fetchOptions = fetchOptions;
        loader.adjustmentTransform.copy(upRotationMatrix);
        promise = loader.parse(buffer);
        break;
      }
      case "pnts": {
        const loader = new PNTSLoader(manager);
        loader.workingPath = workingPath;
        loader.fetchOptions = fetchOptions;
        promise = loader.parse(buffer);
        break;
      }
      case "i3dm": {
        const loader = new I3DMLoader(manager);
        loader.workingPath = workingPath;
        loader.fetchOptions = fetchOptions;
        loader.adjustmentTransform.copy(upRotationMatrix);
        loader.ellipsoid.copy(this.ellipsoid);
        promise = loader.parse(buffer);
        break;
      }
      case "cmpt": {
        const loader = new CMPTLoader(manager);
        loader.workingPath = workingPath;
        loader.fetchOptions = fetchOptions;
        loader.adjustmentTransform.copy(upRotationMatrix);
        loader.ellipsoid.copy(this.ellipsoid);
        promise = loader.parse(buffer).then((res) => res.scene);
        break;
      }
      // 3DTILES_content_gltf
      case "gltf":
      case "glb": {
        const loader = manager.getHandler("path.gltf") || manager.getHandler("path.glb") || new GLTFLoader3(manager);
        loader.setWithCredentials(fetchOptions.credentials === "include");
        loader.setRequestHeader(fetchOptions.headers || {});
        if (fetchOptions.credentials === "include" && fetchOptions.mode === "cors") {
          loader.setCrossOrigin("use-credentials");
        }
        let resourcePath = loader.resourcePath || loader.path || workingPath;
        if (!/[\\/]$/.test(resourcePath) && resourcePath.length) {
          resourcePath += "/";
        }
        promise = loader.parseAsync(buffer, resourcePath).then((result2) => {
          result2.scene = result2.scene || new Group3();
          const { scene: scene2 } = result2;
          scene2.updateMatrix();
          scene2.matrix.multiply(upRotationMatrix).decompose(scene2.position, scene2.quaternion, scene2.scale);
          return result2;
        });
        break;
      }
      default: {
        promise = this.invokeOnePlugin((plugin) => plugin.parseToMesh && plugin.parseToMesh(buffer, tile, extension, url, abortSignal));
        break;
      }
    }
    const result = await promise;
    if (result === null) {
      throw new Error(`TilesRenderer: Content type "${fileType}" not supported.`);
    }
    let scene;
    let metadata;
    if (result.isObject3D) {
      scene = result;
      metadata = null;
    } else {
      scene = result.scene;
      metadata = result;
    }
    scene.updateMatrix();
    scene.matrix.premultiply(tileTransform);
    scene.matrix.decompose(scene.position, scene.quaternion, scene.scale);
    await this.invokeAllPlugins((plugin) => {
      return plugin.processTileModel && plugin.processTileModel(scene, tile);
    });
    scene.traverse((c) => {
      c[INITIAL_FRUSTUM_CULLED] = c.frustumCulled;
    });
    updateFrustumCulled(scene, !this.autoDisableRendererCulling);
    const materials = [];
    const geometry = [];
    const textures = [];
    scene.traverse((c) => {
      if (c.geometry) {
        geometry.push(c.geometry);
      }
      if (c.material) {
        const material = c.material;
        materials.push(c.material);
        for (const key in material) {
          const value = material[key];
          if (value && value.isTexture) {
            textures.push(value);
          }
        }
      }
    });
    if (abortSignal.aborted) {
      for (let i = 0, l = textures.length; i < l; i++) {
        const texture = textures[i];
        if (texture.image instanceof ImageBitmap) {
          texture.image.close();
        }
        texture.dispose();
      }
      return;
    }
    engineData.materials = materials;
    engineData.geometry = geometry;
    engineData.textures = textures;
    engineData.scene = scene;
    engineData.metadata = metadata;
  }
  disposeTile(tile) {
    super.disposeTile(tile);
    const engineData = tile.engineData;
    if (engineData.scene) {
      const materials = engineData.materials;
      const geometry = engineData.geometry;
      const textures = engineData.textures;
      const parent = engineData.scene.parent;
      engineData.scene.traverse((child) => {
        if (child.userData.meshFeatures) {
          child.userData.meshFeatures.dispose();
        }
        if (child.userData.structuralMetadata) {
          child.userData.structuralMetadata.dispose();
        }
      });
      for (let i = 0, l = geometry.length; i < l; i++) {
        geometry[i].dispose();
      }
      for (let i = 0, l = materials.length; i < l; i++) {
        materials[i].dispose();
      }
      for (let i = 0, l = textures.length; i < l; i++) {
        const texture = textures[i];
        if (texture.image instanceof ImageBitmap) {
          texture.image.close();
        }
        texture.dispose();
      }
      if (parent) {
        parent.remove(engineData.scene);
      }
      engineData.scene = null;
      engineData.materials = null;
      engineData.textures = null;
      engineData.geometry = null;
      engineData.metadata = null;
    }
  }
  setTileActive(tile, active) {
    const scene = tile.engineData.scene;
    const group = this.group;
    if (scene) {
      scene.traverse((c) => {
        c.updateMatrix();
        c.matrixWorld.copy(c.matrix);
        if (c.parent) {
          c.matrixWorld.premultiply(c.parent.matrixWorld);
        } else {
          c.matrixWorld.premultiply(group.matrixWorld);
        }
      });
    }
    super.setTileActive(tile, active);
  }
  setTileVisible(tile, visible) {
    const scene = tile.engineData.scene;
    const group = this.group;
    if (visible) {
      if (scene) {
        group.add(scene);
      }
    } else {
      if (scene) {
        group.remove(scene);
      }
    }
    super.setTileVisible(tile, visible);
  }
  calculateBytesUsed(tile, scene) {
    const bytesUsed = this._bytesUsed;
    if (!bytesUsed.has(tile) && scene) {
      bytesUsed.set(tile, estimateBytesUsed(scene));
    }
    return bytesUsed.get(tile) ?? null;
  }
  calculateTileViewError(tile, target) {
    const engineData = tile.engineData;
    const cameras = this.cameras;
    const cameraInfo = this.cameraInfo;
    const boundingVolume = engineData.boundingVolume;
    let inView = false;
    let inViewError = 0;
    let inViewDistance = Infinity;
    let maxCameraError = 0;
    let minCameraDistance = Infinity;
    for (let i = 0, l = cameras.length; i < l; i++) {
      const info = cameraInfo[i];
      let error;
      let distance;
      if (info.isOrthographic) {
        const pixelSize = info.pixelSize;
        error = tile.geometricError / pixelSize;
        distance = Infinity;
      } else {
        const sseDenominator = info.sseDenominator;
        distance = boundingVolume.distanceToPoint(info.position);
        error = distance === 0 ? Infinity : tile.geometricError / (distance * sseDenominator);
      }
      const frustum = cameraInfo[i].frustum;
      if (boundingVolume.intersectsFrustum(frustum)) {
        inView = true;
        inViewError = Math.max(inViewError, error);
        inViewDistance = Math.min(inViewDistance, distance);
      }
      maxCameraError = Math.max(maxCameraError, error);
      minCameraDistance = Math.min(minCameraDistance, distance);
    }
    if (inView) {
      target.inView = true;
      target.error = inViewError;
      target.distanceFromCamera = inViewDistance;
    } else {
      target.inView = false;
      target.error = maxCameraError;
      target.distanceFromCamera = minCameraDistance;
    }
  }
  dispose() {
    super.dispose();
    this.group.removeFromParent();
  }
};

// build/three/renderer/controls/GlobeControls.js
import {
  Matrix4 as Matrix411,
  Quaternion as Quaternion3,
  Vector2 as Vector26,
  Vector3 as Vector314,
  MathUtils as MathUtils5,
  Ray as Ray6,
  Group as Group4
} from "three";

// build/three/renderer/controls/EnvironmentControls.js
import {
  Matrix4 as Matrix410,
  Quaternion as Quaternion2,
  Vector2 as Vector25,
  Vector3 as Vector313,
  Raycaster,
  Plane as Plane2,
  EventDispatcher as EventDispatcher2,
  MathUtils as MathUtils4,
  Ray as Ray5
} from "three";

// build/three/renderer/controls/PivotPointMesh.js
import { Mesh, PlaneGeometry, ShaderMaterial, Vector2 as Vector23 } from "three";
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
        resolution: { value: new Vector23() },
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

// build/three/renderer/controls/PointerTracker.js
import { Vector2 as Vector24 } from "three";
var _vec4 = /* @__PURE__ */ new Vector24();
var _vec23 = /* @__PURE__ */ new Vector24();
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
    this.hoverPosition = new Vector24();
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
    this.hoverPosition = new Vector24();
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
    const position = new Vector24();
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
    this.getCenterPoint(_vec4);
    this.getPreviousCenterPoint(_vec23);
    return _vec4.sub(_vec23).length();
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

// build/three/renderer/controls/utils.js
import { Matrix4 as Matrix49, Ray as Ray4, Vector3 as Vector312 } from "three";
var _matrix4 = /* @__PURE__ */ new Matrix49();
function makeRotateAroundPoint(point, quat, target) {
  target.makeTranslation(-point.x, -point.y, -point.z);
  _matrix4.makeRotationFromQuaternion(quat);
  target.premultiply(_matrix4);
  _matrix4.makeTranslation(point.x, point.y, point.z);
  target.premultiply(_matrix4);
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
  const ray = raycaster instanceof Ray4 ? raycaster : raycaster.ray;
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

// build/three/renderer/controls/EnvironmentControls.js
var NONE = 0;
var DRAG = 1;
var ROTATE = 2;
var ZOOM = 3;
var WAITING = 4;
var FREE_ROTATE = 5;
var DRAG_PLANE_THRESHOLD = 0.05;
var DRAG_UP_THRESHOLD = 0.025;
var _rotMatrix = /* @__PURE__ */ new Matrix410();
var _invMatrix2 = /* @__PURE__ */ new Matrix410();
var _delta = /* @__PURE__ */ new Vector313();
var _vec5 = /* @__PURE__ */ new Vector313();
var _pos2 = /* @__PURE__ */ new Vector313();
var _center = /* @__PURE__ */ new Vector313();
var _forward = /* @__PURE__ */ new Vector313();
var _right = /* @__PURE__ */ new Vector313();
var _targetRight = /* @__PURE__ */ new Vector313();
var _rotationAxis = /* @__PURE__ */ new Vector313();
var _quaternion = /* @__PURE__ */ new Quaternion2();
var _plane = /* @__PURE__ */ new Plane2();
var _localUp = /* @__PURE__ */ new Vector313();
var _mouseBefore = /* @__PURE__ */ new Vector313();
var _mouseAfter = /* @__PURE__ */ new Vector313();
var _identityQuat = /* @__PURE__ */ new Quaternion2();
var _ray3 = /* @__PURE__ */ new Ray5();
var _flightDir = /* @__PURE__ */ new Vector313();
var _zoomPointPointer = /* @__PURE__ */ new Vector25();
var _pointer = /* @__PURE__ */ new Vector25();
var _prevPointer = /* @__PURE__ */ new Vector25();
var _deltaPointer = /* @__PURE__ */ new Vector25();
var _centerPoint = /* @__PURE__ */ new Vector25();
var _startCenterPoint = /* @__PURE__ */ new Vector25();
var _changeEvent = { type: "change" };
var _startEvent = { type: "start" };
var _endEvent = { type: "end" };
var EnvironmentControls = class extends EventDispatcher2 {
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
    this.fallbackPlane = new Plane2(new Vector313(0, 1, 0), 0);
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
    this.pivotPoint = new Vector313();
    this.zoomDirectionSet = false;
    this.zoomPointSet = false;
    this.zoomDirection = new Vector313();
    this.zoomPoint = new Vector313();
    this.zoomDelta = 0;
    this.rotationInertiaPivot = new Vector313();
    this.rotationInertia = new Vector25();
    this.dragInertia = new Vector313();
    this.inertiaTargetDistance = Infinity;
    this.inertiaStableFrames = 0;
    this.pivotMesh = new PivotPointMesh();
    this.pivotMesh.raycast = () => {
    };
    this.pivotMesh.scale.setScalar(0.25);
    this.raycaster = new Raycaster();
    this.raycaster.firstHitOnly = true;
    this.up = new Vector313(0, 1, 0);
    this._lastTime = performance.now();
    this._keysDown = /* @__PURE__ */ new Set();
    this._detachCallback = null;
    this._upInitialized = false;
    this._lastUsedState = NONE;
    this._zoomPointWasSet = false;
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
      _vec5.copy(result).project(camera);
      if (_vec5.x < -1 || _vec5.x > 1 || _vec5.y < -1 || _vec5.y > 1) {
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
    const inertiaNeedsUpdate = this._inertiaNeedsUpdate();
    const adjustCameraRotation = this.needsUpdate || inertiaNeedsUpdate;
    if (this.needsUpdate || inertiaNeedsUpdate) {
      const zoomDelta = this.zoomDelta;
      this._updateZoom();
      this._updatePosition(deltaTime);
      this._updateRotation(deltaTime);
      if (state === DRAG || state === ROTATE || state === FREE_ROTATE) {
        _forward.set(0, 0, -1).transformDirection(camera.matrixWorld);
        this.inertiaTargetDistance = _vec5.copy(pivotPoint).sub(camera.position).dot(_forward);
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
      setRaycasterFromCamera(_ray3, _vec5.set(0, 0, -1), camera);
      _ray3.applyMatrix4(camera.matrixWorldInverse);
      _ray3.direction.normalize();
      _ray3.recast(-_ray3.direction.dot(_ray3.origin)).at(stableDistance / _ray3.direction.z, _vec5);
      _vec5.applyMatrix4(camera.matrixWorld);
      setRaycasterFromCamera(_ray3, _delta.set(pixelThreshold, pixelThreshold, -1), camera);
      _ray3.applyMatrix4(camera.matrixWorldInverse);
      _ray3.direction.normalize();
      _ray3.recast(-_ray3.direction.dot(_ray3.origin)).at(stableDistance / _ray3.direction.z, _delta);
      _delta.applyMatrix4(camera.matrixWorld);
      _vec5.sub(pivotPoint).normalize();
      _delta.sub(pivotPoint).normalize();
      const threshold = _vec5.angleTo(_delta) / deltaTime;
      rotationInertia.multiplyScalar(factor);
      if (rotationInertia.lengthSq() < threshold ** 2 || !enableDamping) {
        rotationInertia.set(0, 0);
      }
    }
    if (dragInertia.lengthSq() > 0) {
      setRaycasterFromCamera(_ray3, _vec5.set(0, 0, -1), camera);
      _ray3.applyMatrix4(camera.matrixWorldInverse);
      _ray3.direction.normalize();
      _ray3.recast(-_ray3.direction.dot(_ray3.origin)).at(stableDistance / _ray3.direction.z, _vec5);
      _vec5.applyMatrix4(camera.matrixWorld);
      setRaycasterFromCamera(_ray3, _delta.set(pixelThreshold, pixelThreshold, -1), camera);
      _ray3.applyMatrix4(camera.matrixWorldInverse);
      _ray3.direction.normalize();
      _ray3.recast(-_ray3.direction.dot(_ray3.origin)).at(stableDistance / _ray3.direction.z, _delta);
      _delta.applyMatrix4(camera.matrixWorld);
      const threshold = _vec5.distanceTo(_delta) / deltaTime;
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
      _mouseBefore.unproject(camera);
      const normalizedDelta = Math.pow(0.95, Math.abs(scale * 0.05));
      let scaleFactor = scale > 0 ? 1 / Math.abs(normalizedDelta) : normalizedDelta;
      scaleFactor *= zoomSpeed;
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
      const finalZoomDirection = _vec5.copy(zoomDirection);
      if (this.zoomPointSet || this._updateZoomPoint()) {
        const dist = zoomPoint.distanceTo(camera.position);
        if (scale < 0) {
          const remainingDistance = Math.min(0, dist - maxDistance);
          scale = scale * dist * zoomSpeed * 25e-4;
          scale = Math.max(scale, remainingDistance);
        } else {
          const remainingDistance = Math.max(0, dist - minDistance);
          scale = scale * Math.max(dist - minDistance, 0) * zoomSpeed * 25e-4;
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
      if (raycaster.ray.intersectPlane(_plane, _vec5)) {
        _delta.subVectors(pivotPoint, _vec5);
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
      _vec5.crossVectors(_localUp, _forward).normalize();
      const sign = Math.sign(_vec5.dot(_right));
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
    camera.matrixWorld.decompose(camera.position, camera.quaternion, _vec5);
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
        this.getUpDirection(zoomPoint, _vec5);
        let amt = Math.max(_vec5.dot(up) - 0.6, 0) / 0.4;
        amt = MathUtils4.mapLinear(amt, 0, 0.5, 0, 1);
        amt = Math.min(amt, 1);
        if (camera.isOrthographicCamera) {
          amt *= 0.1;
        }
        _quaternion.slerp(_identityQuat, 1 - amt);
      }
      makeRotateAroundPoint(zoomPoint, _quaternion, _rotMatrix);
      camera.updateMatrixWorld();
      camera.matrixWorld.premultiply(_rotMatrix);
      camera.matrixWorld.decompose(camera.position, camera.quaternion, _vec5);
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
      if (raycaster.ray.intersectPlane(plane, _vec5)) {
        const planeHit = {
          point: _vec5.clone(),
          distance: raycaster.ray.origin.distanceTo(_vec5)
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
    let multiplier = MathUtils4.mapLinear(1 - Math.abs(_forward.dot(up)), 0, 0.2, 0, 1);
    multiplier = MathUtils4.clamp(multiplier, 0, 1);
    alpha *= multiplier;
    _targetRight.crossVectors(up, _forward);
    _targetRight.lerp(_right, 1 - alpha).normalize();
    _quaternion.setFromUnitVectors(_right, _targetRight);
    camera.quaternion.premultiply(_quaternion);
    let fixedPoint = null;
    if (state === DRAG || state === ROTATE || state === FREE_ROTATE) {
      fixedPoint = _pos2.copy(pivotPoint);
    } else if (zoomPointSet) {
      fixedPoint = _pos2.copy(zoomPoint);
    }
    if (fixedPoint) {
      _invMatrix2.copy(camera.matrixWorld).invert();
      _vec5.copy(fixedPoint).applyMatrix4(_invMatrix2);
      camera.updateMatrixWorld();
      _vec5.applyMatrix4(camera.matrixWorld);
      _center.subVectors(fixedPoint, _vec5);
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
      _vec5.crossVectors(up, _forward);
      const sign = Math.sign(_vec5.dot(_right));
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
    _vec5.crossVectors(_forward, _right).normalize();
    _rotMatrix.makeBasis(_right, _vec5, _forward);
    camera.quaternion.setFromRotationMatrix(_rotMatrix);
    let fixedPoint = null;
    if (state === DRAG || state === ROTATE || state === FREE_ROTATE) {
      fixedPoint = _pos2.copy(pivotPoint);
    } else if (zoomPointSet) {
      fixedPoint = _pos2.copy(zoomPoint);
    }
    if (fixedPoint) {
      _invMatrix2.copy(camera.matrixWorld).invert();
      _vec5.copy(fixedPoint).applyMatrix4(_invMatrix2);
      camera.updateMatrixWorld();
      _vec5.applyMatrix4(camera.matrixWorld);
      _center.subVectors(fixedPoint, _vec5);
      camera.position.add(_center);
    }
    camera.updateMatrixWorld();
  }
};

// build/three/renderer/controls/GlobeControls.js
var _invMatrix3 = /* @__PURE__ */ new Matrix411();
var _rotMatrix2 = /* @__PURE__ */ new Matrix411();
var _pos3 = /* @__PURE__ */ new Vector314();
var _vec6 = /* @__PURE__ */ new Vector314();
var _center2 = /* @__PURE__ */ new Vector314();
var _forward2 = /* @__PURE__ */ new Vector314();
var _targetRight2 = /* @__PURE__ */ new Vector314();
var _globalUp = /* @__PURE__ */ new Vector314();
var _quaternion2 = /* @__PURE__ */ new Quaternion3();
var _zoomPointUp = /* @__PURE__ */ new Vector314();
var _toCenter = /* @__PURE__ */ new Vector314();
var _ray4 = /* @__PURE__ */ new Ray6();
var _ellipsoid = /* @__PURE__ */ new Ellipsoid();
var _pointer2 = /* @__PURE__ */ new Vector26();
var _latLon = {};
var MIN_ELEVATION = 2550;
var GlobeControls = class extends EnvironmentControls {
  /**
   * The world matrix of `ellipsoidGroup`, representing the ellipsoid's coordinate frame.
   * @type {Matrix4}
   * @readonly
   */
  get ellipsoidFrame() {
    return this.ellipsoidGroup.matrixWorld;
  }
  /**
   * The inverse of `ellipsoidFrame`.
   * @type {Matrix4}
   * @readonly
   */
  get ellipsoidFrameInverse() {
    const { ellipsoidGroup, ellipsoidFrame, _ellipsoidFrameInverse } = this;
    return ellipsoidGroup.matrixWorldInverse ? ellipsoidGroup.matrixWorldInverse : _ellipsoidFrameInverse.copy(ellipsoidFrame).invert();
  }
  constructor(scene = null, camera = null, domElement = null) {
    super(scene, camera, domElement);
    this.isGlobeControls = true;
    this._dragMode = 0;
    this._rotationMode = 0;
    this.maxZoom = 0.01;
    this.nearMargin = 0.25;
    this.farMargin = 0;
    this.useFallbackPlane = false;
    this.autoAdjustCameraRotation = false;
    this.globeInertia = new Quaternion3();
    this.globeInertiaFactor = 0;
    this.ellipsoid = WGS84_ELLIPSOID.clone();
    this.ellipsoidGroup = new Group4();
    this._ellipsoidFrameInverse = new Matrix411();
  }
  /**
   * Sets the ellipsoid model and its scene group for globe-aware interaction.
   * @param {Ellipsoid} [ellipsoid] - Ellipsoid to use. Defaults to a WGS84 clone.
   * @param {Group} [ellipsoidGroup] - Group whose world matrix defines the ellipsoid frame.
   */
  setEllipsoid(ellipsoid, ellipsoidGroup) {
    this.ellipsoid = ellipsoid || WGS84_ELLIPSOID.clone();
    this.ellipsoidGroup = ellipsoidGroup || new Group4();
  }
  getPivotPoint(target) {
    const { camera, ellipsoidFrame, ellipsoidFrameInverse, ellipsoid } = this;
    _forward2.set(0, 0, -1).transformDirection(camera.matrixWorld);
    _ray4.origin.copy(camera.position);
    _ray4.direction.copy(_forward2);
    _ray4.applyMatrix4(ellipsoidFrameInverse);
    ellipsoid.closestPointToRayEstimate(_ray4, _vec6).applyMatrix4(ellipsoidFrame);
    if (super.getPivotPoint(target) === null || _pos3.subVectors(target, _ray4.origin).dot(_ray4.direction) > _pos3.subVectors(_vec6, _ray4.origin).dot(_ray4.direction)) {
      target.copy(_vec6);
    }
    return target;
  }
  /**
   * Returns the vector from the camera to the center of the ellipsoid in world space.
   * @param {Vector3} target
   * @returns {Vector3}
   */
  getVectorToCenter(target) {
    const { ellipsoidFrame, camera } = this;
    return target.setFromMatrixPosition(ellipsoidFrame).sub(camera.position);
  }
  /**
   * Returns the distance from the camera to the center of the ellipsoid.
   * @returns {number}
   */
  getDistanceToCenter() {
    return this.getVectorToCenter(_vec6).length();
  }
  getUpDirection(point, target) {
    const { ellipsoidFrame, ellipsoidFrameInverse, ellipsoid } = this;
    _vec6.copy(point).applyMatrix4(ellipsoidFrameInverse);
    ellipsoid.getPositionToNormal(_vec6, target);
    target.transformDirection(ellipsoidFrame);
  }
  getCameraUpDirection(target) {
    const { ellipsoidFrame, ellipsoidFrameInverse, ellipsoid, camera } = this;
    if (camera.isOrthographicCamera) {
      this._getVirtualOrthoCameraPosition(_vec6);
      _vec6.applyMatrix4(ellipsoidFrameInverse);
      ellipsoid.getPositionToNormal(_vec6, target);
      target.transformDirection(ellipsoidFrame);
    } else {
      this.getUpDirection(camera.position, target);
    }
  }
  update(deltaTime = Math.min(this._getDeltaTime(), 64 / 1e3)) {
    if (!this.enabled || !this.camera || deltaTime === 0) {
      return;
    }
    const { camera, pivotMesh } = this;
    if (this._isNearControls()) {
      this.scaleZoomOrientationAtEdges = this.zoomDelta < 0;
    } else {
      if (this.state !== NONE && this._dragMode !== 1 && this._rotationMode !== 1) {
        pivotMesh.visible = false;
      }
      this.scaleZoomOrientationAtEdges = false;
    }
    const adjustCameraRotation = this.needsUpdate || this._inertiaNeedsUpdate();
    super.update(deltaTime);
    this.adjustCamera(camera);
    if (adjustCameraRotation && (this._isNearControls() || this.state === FREE_ROTATE)) {
      this.getCameraUpDirection(_globalUp);
      this._alignCameraUp(_globalUp, 1);
      this.getCameraUpDirection(_globalUp);
      this._clampRotation(_globalUp);
    }
  }
  // Updates the passed camera near and far clip planes to encapsulate the ellipsoid from the
  // current position in addition to adjusting the height.
  adjustCamera(camera) {
    super.adjustCamera(camera);
    const { ellipsoidFrame, ellipsoidFrameInverse, ellipsoid, nearMargin, farMargin } = this;
    const maxRadius = this._getMaxWorldRadius();
    if (camera.isPerspectiveCamera) {
      const distanceToCenter = _vec6.setFromMatrixPosition(ellipsoidFrame).sub(camera.position).length();
      const margin = nearMargin * maxRadius;
      const alpha = MathUtils5.clamp((distanceToCenter - maxRadius) / margin, 0, 1);
      const minNear = MathUtils5.lerp(1, 1e3, alpha);
      camera.near = Math.max(minNear, distanceToCenter - maxRadius - margin);
      _pos3.copy(camera.position).applyMatrix4(ellipsoidFrameInverse);
      ellipsoid.getPositionToCartographic(_pos3, _latLon);
      const elevation = Math.max(ellipsoid.getPositionElevation(_pos3), MIN_ELEVATION);
      const horizonDistance = ellipsoid.calculateHorizonDistance(_latLon.lat, elevation);
      camera.far = horizonDistance + 0.1 + maxRadius * farMargin;
      camera.updateProjectionMatrix();
    } else {
      this._getVirtualOrthoCameraPosition(camera.position, camera);
      camera.updateMatrixWorld();
      _invMatrix3.copy(camera.matrixWorld).invert();
      _vec6.setFromMatrixPosition(ellipsoidFrame).applyMatrix4(_invMatrix3);
      const distanceToCenter = -_vec6.z;
      camera.near = distanceToCenter - maxRadius * (1 + nearMargin);
      camera.far = distanceToCenter + 0.1 + maxRadius * farMargin;
      camera.position.addScaledVector(_forward2, camera.near);
      camera.far -= camera.near;
      camera.near = 0;
      camera.updateProjectionMatrix();
      camera.updateMatrixWorld();
    }
  }
  // resets the "stuck" drag modes
  setState(...args) {
    super.setState(...args);
    this._dragMode = 0;
    this._rotationMode = 0;
  }
  _updateInertia(deltaTime) {
    super._updateInertia(deltaTime);
    const {
      globeInertia,
      enableDamping,
      dampingFactor,
      camera,
      cameraRadius,
      minDistance,
      inertiaTargetDistance,
      ellipsoidFrame
    } = this;
    if (!this.enableDamping || this.inertiaStableFrames > 1) {
      this.globeInertiaFactor = 0;
      this.globeInertia.identity();
      return;
    }
    const factor = Math.pow(2, -deltaTime / dampingFactor);
    const stableDistance = Math.max(camera.near, cameraRadius, minDistance, inertiaTargetDistance);
    const resolution = 2 * 1e3;
    const pixelWidth = 2 / resolution;
    const pixelThreshold = 0.25 * pixelWidth;
    _center2.setFromMatrixPosition(ellipsoidFrame);
    if (this.globeInertiaFactor !== 0) {
      setRaycasterFromCamera(_ray4, _vec6.set(0, 0, -1), camera);
      _ray4.applyMatrix4(camera.matrixWorldInverse);
      _ray4.direction.normalize();
      _ray4.recast(-_ray4.direction.dot(_ray4.origin)).at(stableDistance / _ray4.direction.z, _vec6);
      _vec6.applyMatrix4(camera.matrixWorld);
      setRaycasterFromCamera(_ray4, _pos3.set(pixelThreshold, pixelThreshold, -1), camera);
      _ray4.applyMatrix4(camera.matrixWorldInverse);
      _ray4.direction.normalize();
      _ray4.recast(-_ray4.direction.dot(_ray4.origin)).at(stableDistance / _ray4.direction.z, _pos3);
      _pos3.applyMatrix4(camera.matrixWorld);
      _vec6.sub(_center2).normalize();
      _pos3.sub(_center2).normalize();
      this.globeInertiaFactor *= factor;
      const threshold = _vec6.angleTo(_pos3) / deltaTime;
      const globeAngle = 2 * Math.acos(globeInertia.w) * this.globeInertiaFactor;
      if (globeAngle < threshold || !enableDamping) {
        this.globeInertiaFactor = 0;
        globeInertia.identity();
      }
    }
    if (this.globeInertiaFactor !== 0) {
      if (globeInertia.w === 1 && (globeInertia.x !== 0 || globeInertia.y !== 0 || globeInertia.z !== 0)) {
        globeInertia.w = Math.min(globeInertia.w, 1 - 1e-9);
      }
      _center2.setFromMatrixPosition(ellipsoidFrame);
      _quaternion2.identity().slerp(globeInertia, this.globeInertiaFactor * deltaTime);
      makeRotateAroundPoint(_center2, _quaternion2, _rotMatrix2);
      camera.matrixWorld.premultiply(_rotMatrix2);
      camera.matrixWorld.decompose(camera.position, camera.quaternion, _vec6);
    }
  }
  _inertiaNeedsUpdate() {
    return super._inertiaNeedsUpdate() || this.globeInertiaFactor !== 0;
  }
  _getFlightSpeedScale() {
    const altitude = this.getDistanceToCenter() - this._getMaxWorldRadius();
    return 2 * Math.max(altitude, 1e3);
  }
  _updateFlight(deltaTime) {
    const { camera } = this;
    const didFly = super._updateFlight(deltaTime);
    if (didFly) {
      const maxDistance = this._getMaxPerspectiveDistance();
      const distToCenter = this.getDistanceToCenter();
      if (distToCenter > maxDistance) {
        this.getVectorToCenter(_vec6).normalize();
        camera.position.addScaledVector(_vec6, distToCenter - maxDistance);
        camera.updateMatrixWorld();
      }
      if (!this._isNearControls()) {
        const distanceAlpha = MathUtils5.clamp(
          MathUtils5.mapLinear(this.getDistanceToCenter(), this._getPerspectiveTransitionDistance(), maxDistance, 0, 1),
          0,
          1
        );
        this._tiltTowardsCenter(0.02 * distanceAlpha);
        this._alignCameraUpToNorth(0.01 * distanceAlpha);
      }
    }
    return didFly;
  }
  _updatePosition(deltaTime) {
    if (this.state === DRAG) {
      if (this._dragMode === 0) {
        this._dragMode = this._isNearControls() ? 1 : -1;
      }
      const {
        raycaster,
        camera,
        pivotPoint,
        pointerTracker,
        domElement,
        ellipsoidFrame,
        ellipsoidFrameInverse
      } = this;
      const pivotDir = _pos3;
      const newPivotDir = _targetRight2;
      pointerTracker.getCenterPoint(_pointer2);
      adjustedPointerToCoords(_pointer2, domElement, _pointer2);
      setRaycasterFromCamera(raycaster, _pointer2, camera);
      raycaster.ray.applyMatrix4(ellipsoidFrameInverse);
      const pivotRadius = _vec6.copy(pivotPoint).applyMatrix4(ellipsoidFrameInverse).length();
      _ellipsoid.radius.setScalar(pivotRadius);
      if (!_ellipsoid.intersectRay(raycaster.ray, _vec6)) {
        this.resetState();
        this._updateInertia(deltaTime);
        return;
      }
      _vec6.applyMatrix4(ellipsoidFrame);
      _center2.setFromMatrixPosition(ellipsoidFrame);
      pivotDir.subVectors(pivotPoint, _center2).normalize();
      newPivotDir.subVectors(_vec6, _center2).normalize();
      _quaternion2.setFromUnitVectors(newPivotDir, pivotDir);
      makeRotateAroundPoint(_center2, _quaternion2, _rotMatrix2);
      camera.matrixWorld.premultiply(_rotMatrix2);
      camera.matrixWorld.decompose(camera.position, camera.quaternion, _vec6);
      if (pointerTracker.getMoveDistance() / deltaTime < 2 * window.devicePixelRatio) {
        this.inertiaStableFrames++;
      } else {
        this.globeInertia.copy(_quaternion2);
        this.globeInertiaFactor = 1 / deltaTime;
        this.inertiaStableFrames = 0;
      }
    }
  }
  // disable rotation once we're outside the control transition
  _updateRotation(...args) {
    if (this.state === FREE_ROTATE) {
      super._updateRotation(...args);
      return;
    }
    if (this._rotationMode === 1 || this._isNearControls()) {
      this._rotationMode = 1;
      super._updateRotation(...args);
    } else {
      this.pivotMesh.visible = false;
      this._rotationMode = -1;
    }
  }
  _updateZoom() {
    const { zoomDelta, zoomSpeed, zoomPoint, camera, maxZoom, state } = this;
    if (state !== ZOOM && zoomDelta === 0) {
      return;
    }
    this.rotationInertia.set(0, 0);
    this.dragInertia.set(0, 0, 0);
    this.globeInertia.identity();
    this.globeInertiaFactor = 0;
    const deltaAlpha = MathUtils5.clamp(MathUtils5.mapLinear(Math.abs(zoomDelta), 0, 20, 0, 1), 0, 1);
    if (this._isNearControls() || zoomDelta > 0) {
      this._updateZoomDirection();
      if (zoomDelta < 0 && (this.zoomPointSet || this._updateZoomPoint())) {
        _forward2.set(0, 0, -1).transformDirection(camera.matrixWorld).normalize();
        _toCenter.copy(this.up).multiplyScalar(-1);
        this.getUpDirection(zoomPoint, _zoomPointUp);
        const upAlpha = MathUtils5.clamp(MathUtils5.mapLinear(-_zoomPointUp.dot(_toCenter), 1, 0.95, 0, 1), 0, 1);
        const forwardAlpha = 1 - _forward2.dot(_toCenter);
        const cameraAlpha = camera.isOrthographicCamera ? 0.05 : 1;
        const adjustedDeltaAlpha = MathUtils5.clamp(deltaAlpha * 3, 0, 1);
        const alpha = Math.min(upAlpha * forwardAlpha * cameraAlpha * adjustedDeltaAlpha, 0.1);
        _toCenter.lerpVectors(_forward2, _toCenter, alpha).normalize();
        _quaternion2.setFromUnitVectors(_forward2, _toCenter);
        makeRotateAroundPoint(zoomPoint, _quaternion2, _rotMatrix2);
        camera.matrixWorld.premultiply(_rotMatrix2);
        camera.matrixWorld.decompose(camera.position, camera.quaternion, _toCenter);
        this.zoomDirection.subVectors(zoomPoint, camera.position).normalize();
      }
      super._updateZoom();
    } else if (camera.isPerspectiveCamera) {
      const transitionDistance = this._getPerspectiveTransitionDistance();
      const maxDistance = this._getMaxPerspectiveDistance();
      const distanceAlpha = MathUtils5.mapLinear(this.getDistanceToCenter(), transitionDistance, maxDistance, 0, 1);
      this._tiltTowardsCenter(MathUtils5.lerp(0, 0.4, distanceAlpha * deltaAlpha));
      this._alignCameraUpToNorth(MathUtils5.lerp(0, 0.2, distanceAlpha * deltaAlpha));
      const dist = this.getDistanceToCenter() - this._getMaxWorldRadius();
      const scale = zoomDelta * dist * zoomSpeed * 25e-4;
      const clampedScale = Math.max(scale, Math.min(this.getDistanceToCenter() - maxDistance, 0));
      this.getVectorToCenter(_vec6).normalize();
      this.camera.position.addScaledVector(_vec6, clampedScale);
      this.camera.updateMatrixWorld();
      this.zoomDelta = 0;
    } else {
      const transitionZoom = this._getOrthographicTransitionZoom();
      const minZoom = this._getMinOrthographicZoom();
      const distanceAlpha = MathUtils5.mapLinear(camera.zoom, transitionZoom, minZoom, 0, 1);
      this._tiltTowardsCenter(MathUtils5.lerp(0, 0.4, distanceAlpha * deltaAlpha));
      this._alignCameraUpToNorth(MathUtils5.lerp(0, 0.2, distanceAlpha * deltaAlpha));
      const scale = this.zoomDelta;
      const normalizedDelta = Math.pow(0.95, Math.abs(scale * 0.05));
      const scaleFactor = scale > 0 ? 1 / Math.abs(normalizedDelta) : normalizedDelta;
      const maxScaleFactor = minZoom / camera.zoom;
      const clampedScaleFactor = Math.max(scaleFactor * zoomSpeed, Math.min(maxScaleFactor, 1));
      camera.zoom = Math.min(maxZoom, camera.zoom * clampedScaleFactor);
      camera.updateProjectionMatrix();
      this.zoomDelta = 0;
      this.zoomDirectionSet = false;
    }
  }
  // tilt the camera to align with north
  _alignCameraUpToNorth(alpha) {
    const { ellipsoidFrame } = this;
    _globalUp.set(0, 0, 1).transformDirection(ellipsoidFrame);
    this._alignCameraUp(_globalUp, alpha);
  }
  // tilt the camera to look at the center of the globe
  _tiltTowardsCenter(alpha) {
    const {
      camera,
      ellipsoidFrame
    } = this;
    _forward2.set(0, 0, -1).transformDirection(camera.matrixWorld).normalize();
    _vec6.setFromMatrixPosition(ellipsoidFrame).sub(camera.position).normalize();
    _vec6.lerp(_forward2, 1 - alpha).normalize();
    _quaternion2.setFromUnitVectors(_forward2, _vec6);
    camera.quaternion.premultiply(_quaternion2);
    camera.updateMatrixWorld();
  }
  // returns the perspective camera transition distance can move to based on globe size and fov
  _getPerspectiveTransitionDistance() {
    const { camera } = this;
    if (!camera.isPerspectiveCamera) {
      throw new Error();
    }
    const ellipsoidRadius = this._getMaxWorldRadius();
    const fovHoriz = 2 * Math.atan(Math.tan(MathUtils5.DEG2RAD * camera.fov * 0.5) * camera.aspect);
    const distVert = ellipsoidRadius / Math.tan(MathUtils5.DEG2RAD * camera.fov * 0.5);
    const distHoriz = ellipsoidRadius / Math.tan(fovHoriz * 0.5);
    const dist = Math.max(distVert, distHoriz);
    return dist;
  }
  // returns the max distance the perspective camera can move to based on globe size and fov
  _getMaxPerspectiveDistance() {
    const { camera } = this;
    if (!camera.isPerspectiveCamera) {
      throw new Error();
    }
    const ellipsoidRadius = this._getMaxWorldRadius();
    const fovHoriz = 2 * Math.atan(Math.tan(MathUtils5.DEG2RAD * camera.fov * 0.5) * camera.aspect);
    const distVert = ellipsoidRadius / Math.tan(MathUtils5.DEG2RAD * camera.fov * 0.5);
    const distHoriz = ellipsoidRadius / Math.tan(fovHoriz * 0.5);
    const dist = 2 * Math.max(distVert, distHoriz);
    return dist;
  }
  // returns the transition threshold for orthographic zoom based on the globe size and camera settings
  _getOrthographicTransitionZoom() {
    const { camera } = this;
    if (!camera.isOrthographicCamera) {
      throw new Error();
    }
    const orthoHeight = camera.top - camera.bottom;
    const orthoWidth = camera.right - camera.left;
    const orthoSize = Math.max(orthoHeight, orthoWidth);
    const ellipsoidRadius = this._getMaxWorldRadius();
    const ellipsoidDiameter = 2 * ellipsoidRadius;
    return 2 * orthoSize / ellipsoidDiameter;
  }
  // returns the minimum allowed orthographic zoom based on the globe size and camera settings
  _getMinOrthographicZoom() {
    const { camera } = this;
    if (!camera.isOrthographicCamera) {
      throw new Error();
    }
    const orthoHeight = camera.top - camera.bottom;
    const orthoWidth = camera.right - camera.left;
    const orthoSize = Math.min(orthoHeight, orthoWidth);
    const ellipsoidRadius = this._getMaxWorldRadius();
    const ellipsoidDiameter = 2 * ellipsoidRadius;
    return 0.7 * orthoSize / ellipsoidDiameter;
  }
  // returns the "virtual position" of the orthographic based on where it is and
  // where it's looking primarily so we can reasonably position the camera object
  // in space and derive a reasonable "up" value.
  _getVirtualOrthoCameraPosition(target, camera = this.camera) {
    const { ellipsoidFrame, ellipsoidFrameInverse, ellipsoid } = this;
    if (!camera.isOrthographicCamera) {
      throw new Error();
    }
    _ray4.origin.copy(camera.position);
    _ray4.direction.set(0, 0, -1).transformDirection(camera.matrixWorld);
    _ray4.applyMatrix4(ellipsoidFrameInverse);
    ellipsoid.closestPointToRayEstimate(_ray4, _pos3).applyMatrix4(ellipsoidFrame);
    const orthoHeight = camera.top - camera.bottom;
    const orthoWidth = camera.right - camera.left;
    const orthoSize = Math.max(orthoHeight, orthoWidth) / camera.zoom;
    _forward2.set(0, 0, -1).transformDirection(camera.matrixWorld);
    const dist = _pos3.sub(camera.position).dot(_forward2);
    target.copy(camera.position).addScaledVector(_forward2, dist - orthoSize * 4);
  }
  _isNearControls() {
    const { camera } = this;
    if (camera.isPerspectiveCamera) {
      return this.getDistanceToCenter() < this._getPerspectiveTransitionDistance();
    } else {
      return camera.zoom > this._getOrthographicTransitionZoom();
    }
  }
  _raycast(raycaster) {
    const result = super._raycast(raycaster);
    if (result === null) {
      const { ellipsoid, ellipsoidFrame, ellipsoidFrameInverse } = this;
      _ray4.copy(raycaster.ray).applyMatrix4(ellipsoidFrameInverse);
      const point = ellipsoid.intersectRay(_ray4, _vec6);
      if (point !== null) {
        point.applyMatrix4(ellipsoidFrame);
        return {
          point: point.clone(),
          distance: point.distanceTo(raycaster.ray.origin)
        };
      } else {
        return null;
      }
    } else {
      return result;
    }
  }
  _getMaxWorldRadius() {
    const { ellipsoid, ellipsoidFrame } = this;
    return Math.max(...ellipsoid.radius) * ellipsoidFrame.getMaxScaleOnAxis();
  }
};

// build/three/renderer/controls/CameraTransitionManager.js
import { Clock, EventDispatcher as EventDispatcher3, MathUtils as MathUtils6, OrthographicCamera, PerspectiveCamera, Quaternion as Quaternion4, Vector3 as Vector315 } from "three";
var _forward3 = /* @__PURE__ */ new Vector315();
var _vec7 = /* @__PURE__ */ new Vector315();
var _orthographicCamera = /* @__PURE__ */ new OrthographicCamera();
var _targetOffset = /* @__PURE__ */ new Vector315();
var _perspOffset = /* @__PURE__ */ new Vector315();
var _orthoOffset = /* @__PURE__ */ new Vector315();
var _quat = /* @__PURE__ */ new Quaternion4();
var _targetQuat = /* @__PURE__ */ new Quaternion4();
var CameraTransitionManager = class extends EventDispatcher3 {
  /**
   * Whether a transition animation is currently in progress.
   * @type {boolean}
   * @readonly
   */
  get animating() {
    return this._alpha !== 0 && this._alpha !== 1;
  }
  /**
   * Transition progress from 0 (at perspective) to 1 (at orthographic).
   * @type {number}
   * @readonly
   */
  get alpha() {
    return this._target === 0 ? 1 - this._alpha : this._alpha;
  }
  /**
   * The currently active camera. Returns `perspectiveCamera`, `orthographicCamera`, or the
   * blended `transitionCamera` depending on the current transition state.
   * @type {Camera}
   * @readonly
   */
  get camera() {
    if (this._alpha === 0) return this.perspectiveCamera;
    if (this._alpha === 1) return this.orthographicCamera;
    return this.transitionCamera;
  }
  /**
   * The target camera mode. Set to `'perspective'` or `'orthographic'` to jump instantly without
   * animation. Use `toggle()` to animate the transition.
   * @type {string}
   */
  get mode() {
    return this._target === 0 ? "perspective" : "orthographic";
  }
  set mode(v) {
    if (v === this.mode) {
      return;
    }
    const prevCamera = this.camera;
    if (v === "perspective") {
      this._target = 0;
      this._alpha = 0;
    } else {
      this._target = 1;
      this._alpha = 1;
    }
    this.dispatchEvent({ type: "camera-change", camera: this.camera, prevCamera });
  }
  constructor(perspectiveCamera = new PerspectiveCamera(), orthographicCamera = new OrthographicCamera()) {
    super();
    this.perspectiveCamera = perspectiveCamera;
    this.orthographicCamera = orthographicCamera;
    this.transitionCamera = new PerspectiveCamera();
    this.orthographicPositionalZoom = true;
    this.orthographicOffset = 50;
    this.fixedPoint = new Vector315();
    this.duration = 200;
    this.autoSync = true;
    this.easeFunction = (x) => x;
    this._target = 0;
    this._alpha = 0;
    this._clock = new Clock();
  }
  /**
   * Begins an animated transition to the opposite camera mode. Dispatches a `'toggle'` event.
   */
  toggle() {
    this._target = this._target === 1 ? 0 : 1;
    this._clock.getDelta();
    this.dispatchEvent({ type: "toggle" });
  }
  /**
   * Advances the transition animation and updates the active camera. Must be called each frame.
   * @param {number} [deltaTime] - Time in seconds since the last frame. Defaults to the clock delta, capped at 64ms.
   */
  update(deltaTime = Math.min(this._clock.getDelta(), 64 / 1e3)) {
    if (this.autoSync) {
      this.syncCameras();
    }
    const { perspectiveCamera, orthographicCamera, transitionCamera, camera } = this;
    const delta = deltaTime * 1e3;
    if (this._alpha !== this._target) {
      const direction = Math.sign(this._target - this._alpha);
      const step = direction * delta / this.duration;
      this._alpha = MathUtils6.clamp(this._alpha + step, 0, 1);
      this.dispatchEvent({ type: "change", alpha: this.alpha });
    }
    const prevCamera = camera;
    let newCamera = null;
    if (this._alpha === 0) {
      newCamera = perspectiveCamera;
    } else if (this._alpha === 1) {
      newCamera = orthographicCamera;
    } else {
      newCamera = transitionCamera;
      this._updateTransitionCamera();
    }
    if (prevCamera !== newCamera) {
      if (newCamera === transitionCamera) {
        this.dispatchEvent({ type: "transition-start" });
      }
      this.dispatchEvent({ type: "camera-change", camera: newCamera, prevCamera });
      if (prevCamera === transitionCamera) {
        this.dispatchEvent({ type: "transition-end" });
      }
    }
  }
  /**
   * Synchronises the non-active camera so that both cameras represent the same viewpoint.
   * Called automatically by `update` when `autoSync` is true.
   */
  syncCameras() {
    const fromCamera = this._getFromCamera();
    const { perspectiveCamera, orthographicCamera, transitionCamera, fixedPoint } = this;
    _forward3.set(0, 0, -1).transformDirection(fromCamera.matrixWorld).normalize();
    if (fromCamera.isPerspectiveCamera) {
      if (this.orthographicPositionalZoom) {
        orthographicCamera.position.copy(perspectiveCamera.position).addScaledVector(_forward3, -this.orthographicOffset);
        orthographicCamera.rotation.copy(perspectiveCamera.rotation);
        orthographicCamera.updateMatrixWorld();
      } else {
        const orthoDist = _vec7.subVectors(fixedPoint, orthographicCamera.position).dot(_forward3);
        const perspDist = _vec7.subVectors(fixedPoint, perspectiveCamera.position).dot(_forward3);
        _vec7.copy(perspectiveCamera.position).addScaledVector(_forward3, perspDist);
        orthographicCamera.rotation.copy(perspectiveCamera.rotation);
        orthographicCamera.position.copy(_vec7).addScaledVector(_forward3, -orthoDist);
        orthographicCamera.updateMatrixWorld();
      }
      const distToPoint = Math.abs(_vec7.subVectors(perspectiveCamera.position, fixedPoint).dot(_forward3));
      const projectionHeight = 2 * Math.tan(MathUtils6.DEG2RAD * perspectiveCamera.fov * 0.5) * distToPoint;
      const orthoHeight = orthographicCamera.top - orthographicCamera.bottom;
      orthographicCamera.zoom = orthoHeight / projectionHeight;
      orthographicCamera.updateProjectionMatrix();
    } else {
      const distToPoint = Math.abs(_vec7.subVectors(orthographicCamera.position, fixedPoint).dot(_forward3));
      const orthoHeight = (orthographicCamera.top - orthographicCamera.bottom) / orthographicCamera.zoom;
      const targetDist = orthoHeight * 0.5 / Math.tan(MathUtils6.DEG2RAD * perspectiveCamera.fov * 0.5);
      perspectiveCamera.rotation.copy(orthographicCamera.rotation);
      perspectiveCamera.position.copy(orthographicCamera.position).addScaledVector(_forward3, distToPoint).addScaledVector(_forward3, -targetDist);
      perspectiveCamera.updateMatrixWorld();
      if (this.orthographicPositionalZoom) {
        orthographicCamera.position.copy(perspectiveCamera.position).addScaledVector(_forward3, -this.orthographicOffset);
        orthographicCamera.updateMatrixWorld();
      }
    }
    transitionCamera.position.copy(perspectiveCamera.position);
    transitionCamera.rotation.copy(perspectiveCamera.rotation);
  }
  _getTransitionDirection() {
    return Math.sign(this._target - this._alpha);
  }
  _getToCamera() {
    const dir = this._getTransitionDirection();
    if (dir === 0) {
      return this._target === 0 ? this.perspectiveCamera : this.orthographicCamera;
    } else if (dir > 0) {
      return this.orthographicCamera;
    } else {
      return this.perspectiveCamera;
    }
  }
  _getFromCamera() {
    const dir = this._getTransitionDirection();
    if (dir === 0) {
      return this._target === 0 ? this.perspectiveCamera : this.orthographicCamera;
    } else if (dir > 0) {
      return this.perspectiveCamera;
    } else {
      return this.orthographicCamera;
    }
  }
  _updateTransitionCamera() {
    const { perspectiveCamera, orthographicCamera, transitionCamera, fixedPoint } = this;
    const alpha = this.easeFunction(this._alpha);
    _forward3.set(0, 0, -1).transformDirection(orthographicCamera.matrixWorld).normalize();
    _orthographicCamera.copy(orthographicCamera);
    _orthographicCamera.position.addScaledVector(_forward3, orthographicCamera.near);
    orthographicCamera.far -= orthographicCamera.near;
    orthographicCamera.near = 0;
    _forward3.set(0, 0, -1).transformDirection(perspectiveCamera.matrixWorld).normalize();
    const distToPoint = Math.abs(_vec7.subVectors(perspectiveCamera.position, fixedPoint).dot(_forward3));
    const projectionHeight = 2 * Math.tan(MathUtils6.DEG2RAD * perspectiveCamera.fov * 0.5) * distToPoint;
    const targetQuat = _targetQuat.slerpQuaternions(perspectiveCamera.quaternion, _orthographicCamera.quaternion, alpha);
    const targetFov = MathUtils6.lerp(perspectiveCamera.fov, 1, alpha);
    const targetDistance = projectionHeight * 0.5 / Math.tan(MathUtils6.DEG2RAD * targetFov * 0.5);
    const orthoOffset = _orthoOffset.copy(_orthographicCamera.position).sub(fixedPoint).applyQuaternion(_quat.copy(_orthographicCamera.quaternion).invert());
    const perspOffset = _perspOffset.copy(perspectiveCamera.position).sub(fixedPoint).applyQuaternion(_quat.copy(perspectiveCamera.quaternion).invert());
    const targetOffset = _targetOffset.lerpVectors(perspOffset, orthoOffset, alpha);
    targetOffset.z -= Math.abs(targetOffset.z) - targetDistance;
    const distToPersp = -(perspOffset.z - targetOffset.z);
    const distToOrtho = -(orthoOffset.z - targetOffset.z);
    const targetNearPlane = MathUtils6.lerp(distToPersp + perspectiveCamera.near, distToOrtho + _orthographicCamera.near, alpha);
    const targetFarPlane = MathUtils6.lerp(distToPersp + perspectiveCamera.far, distToOrtho + _orthographicCamera.far, alpha);
    const planeDelta = Math.max(targetFarPlane, 0) - Math.max(targetNearPlane, 0);
    transitionCamera.aspect = perspectiveCamera.aspect;
    transitionCamera.fov = targetFov;
    transitionCamera.near = Math.max(targetNearPlane, planeDelta * 1e-5);
    transitionCamera.far = targetFarPlane;
    transitionCamera.position.copy(targetOffset).applyQuaternion(targetQuat).add(fixedPoint);
    transitionCamera.quaternion.copy(targetQuat);
    transitionCamera.updateProjectionMatrix();
    transitionCamera.updateMatrixWorld();
  }
};
export {
  B3DMLoader,
  CAMERA_FRAME,
  CMPTLoader,
  CameraTransitionManager,
  ENU_FRAME,
  Ellipsoid,
  EllipsoidRegion,
  EnvironmentControls,
  GeoUtils_exports as GeoUtils,
  GlobeControls,
  I3DMLoader,
  MemoryUtils_exports as MemoryUtils,
  OBB,
  OBJECT_FRAME,
  PNTSLoader,
  TilesRenderer,
  WGS84_ELLIPSOID
};
