// (C) 2026 Minoru Akagi
// SPDX-License-Identifier: MIT

// https://github.com/NASA-AMMOS/3DTilesRendererJS/blob/master/src/core/renderer/API.md

import { app } from "../core.js"
import { buildTile } from "../layer/demlayer.js";
import { Material } from "../material.js";
import { decodeBase64TypedArrayObject } from "../utils.js";

import type { TilesRenderer } from "lib/3d-tiles-renderer/3d-tiles-renderer.js";
import type { DEMGridData, GridGeomDataRef, ParsedGridGeomData, Tileset, Tile, DEMTileData, DEMTileEntry } from "../types.js";
import type { DEMLayer } from "../layer/demlayer.js";


export class DEMPlugin {

    name: string = "DEMPLUGIN";
    priority: number = 0;
    tiles: typeof TilesRenderer;
    tileset: Tileset;
    tileEntries: Map<string, DEMTileData> = new Map();
    pendingRequests = new Map();
    layer: DEMLayer;
    showBoundingBox = false;
    showBoundingVolume = false;

    /**
     * Plugin has been registered.
     * @param tiles the caller
     */
	init(tiles: typeof TilesRenderer) {

        this.tiles = tiles;

    }

    /**
     * Plugin has been unregistered.
     */
    // dispose() {}

    /**
     * @param {Array<{type: string, value: any}>} target
     */
    // getAttributions(target) {
    //     target.push({ type: "copyright", value: "hogehoge" })
    // }

    /**
     * @returns {Tileset}
     */
    loadRootTileset() {
        this.tiles.preprocessTileset(this.tileset, ".");
        console.info("Tileset loaded", this.tileset);
        return Promise.resolve(this.tileset);
    }

    /**
     * @param {string} url
     * @param tile
     * @returns {string}
     */
    // preprocessURL(url, tile) {}

    /**
     * @returns {boolean}
     */
    // doTilesNeedUpdate() {}

    /**
     * Calculates camera view error
     * Set .inView {boolean} whether the tile is visible
     *     .error {number} screen space error
     *     .distanceFromCamera {number}
     * @param {Tile} tile
     * @param target an object to retrieve the results
     * @returns {boolean} false it means "no operation"
     */
    // calculateTileViewError(tile, target) {}

    /**
     * @param {Tile} tile
     * @param {boolean} visible
     */
    // setTileVisible(tile, visible) {}

    /**
     * @param {Tile} tile
     * @param {boolean} visible
     */
    // setEmptyTileVisible(tile, visible) {}

    /**
     * @param {Tile} tile
     * @param {boolean} active
     */
    // setTileActive(tile, active) {}

    /**
     * @param {Tile} tile
     * @param tilesetDir
     * @param parentTile
     */
    // preprocessNode(tile, tilesetDir, parentTile) {}

    /**
     * @param {Tile} tile
     * @param scene
     */
    // calculateBytesUsed(tile, scene) {}

    /**
     * @param url
     * @param options
     */
    async fetchData(url, options) {
        if (window.requestTileData === undefined) {
            const tileId = url.split("/").slice(-3).join("/").replace(".tile", "")

            const entry = this.tileEntries.get(tileId);
            if (entry) return entry;

            throw new Error("Tile entry not found");
        }

        // preview
        const pending = this.pendingRequests.get(url);
        if (pending) return pending.promise;

        let resolve, reject;
        const promise = new Promise((res, rej) => {
            resolve = res;
            reject = rej;
        });

        console.debug("Requesting tile data...", url, options);
        window.requestTileData(url);

        this.pendingRequests.set(url, { promise, resolve, reject });
        return promise;
    }

    /**
     * Called from Scene.loadTileData() in preview mode
     */
    dataReceived(url, data: DEMTileData) {
        const pending = this.pendingRequests.get(url);
        if (!pending) return;

        console.debug("Tile data received: ", url, data);

        pending.resolve(data);
        this.pendingRequests.delete(url);
    }

    /**
     * @param content
     * @param {Tile} tile
     * @param {string} extension
     */
	async parseTile(content: DEMTileEntry | DEMTileData, tile, extension, url, abortSignal) {
        const grid_data = content.geometry as DEMGridData;
        if ("tileId" in content) {     // export
            grid_data.grid = await app.loadJSONBinaryFile((grid_data.grid as GridGeomDataRef).url) as ParsedGridGeomData;
        }
        else {
            grid_data.grid = await decodeBase64TypedArrayObject(grid_data.grid) as ParsedGridGeomData;
        }
        return buildTile(this.layer, content, tile, this.showBoundingBox, this.showBoundingVolume);
	}

    /**
     * @param {Tile} tile
     */
	disposeTile(tile) {
        console.debug("disposeTile", tile.content.uri);
    }

    setTileMaterialUpdaters(mtlIndex: number) {
        const noop = () => {};
        const layer = this.layer;

        for (const tile of this.tiles.lruCache.itemList) {
            const mesh = tile.engineData.scene;
            if (!mesh) continue;

            const engineData = tile.engineData;
            if (window.requestTileData === undefined) {
                layer.materials.removeItem(mesh.material, true);

                const material = new Material();
                material.loadData(mesh.userData.materials[mtlIndex], () => layer.requestRender());
                layer.materials.add(material);

                const mtl = material.mtl;
                mesh.material = mtl;

                engineData.materials = [mtl];
        		engineData.textures = (mtl.map) ? [mtl.map] : [];
            }
            else {      // preview
                mesh.onBeforeRender = (renderer, object, camera, geometry, material, group) => {
                    const uri = tile.content.uri + "?mtl";
                    const pending = this.pendingRequests.get(uri);
                    if (pending) return;

                    window.requestTileData(uri);

                    let resolve, reject;
                    const promise = new Promise((res, rej) => {
                        resolve = res;
                        reject = rej;
                    }).then((content) => {
                        layer.materials.removeItem(mesh.material, true);

                        const material = new Material();
                        material.loadData(content.material, () => layer.requestRender());
                        layer.materials.add(material);

                        const mtl = material.mtl;
                        mesh.material = mtl;

                        engineData.materials = [mtl];
                        engineData.textures = (mtl.map) ? [mtl.map] : [];
                    });

                    this.pendingRequests.set(uri, { promise, resolve, reject });

                    mesh.onBeforeRender = noop;
                };
            }
        }
    }
}
