// (C) 2026 Minoru Akagi
// SPDX-License-Identifier: MIT

// https://github.com/NASA-AMMOS/3DTilesRendererJS/blob/master/src/core/renderer/API.md

import { app } from "../core.js"
import { buildTile } from "../layer/demlayer.js";
import { Material } from "../material.js";
import { decodeBase64TypedArrayObject } from "../utils.js";

import type { TilesRenderer } from "lib/3d-tiles-renderer/3d-tiles-renderer.js";
import type { GridGeomData, GridGeomDataRef, ParsedGridGeomData, Tileset, Tile, DEMTileData, DEMTileEntry } from "../types.js";
import type { MapLayer } from "../layer/layer.js";
import type { DEMLayer } from "../layer/demlayer.js";


export class Q3DPlugin {

    name: string = "Q3D_PLUGIN";
    priority: number = 0;
    tiles: typeof TilesRenderer;
    tileset: Tileset;
    tileEntries: DEMTileEntry[] = [];
    pendingRequests = new Map();
    layer: MapLayer;
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
        if (typeof window.requestTileData !== "function") {
            const tileId = url.split("/").slice(-3).join("/").replace(".tile", "")

            const tileEntry = this.tileEntries.find(entry => entry.tileId === tileId);
            if (tileEntry) return tileEntry;

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
        const grid_data = content.grid as GridGeomData;
        if ("tileId" in content) {     // export
            grid_data.grid = await app.loadJSONBinaryFile((grid_data.grid as GridGeomDataRef).url) as ParsedGridGeomData;
        }
        else {
            grid_data.grid = await decodeBase64TypedArrayObject(grid_data.grid) as ParsedGridGeomData;
        }
        return buildTile(this.layer as DEMLayer, content, tile, this.showBoundingBox, this.showBoundingVolume);
	}

    /**
     * @param {Tile} tile
     */
	disposeTile(tile) {
        console.debug("disposeTile", tile.content.uri);
    }

    setTileMaterialUpdaters(mtlIndex: number) {
        const noop = () => {};

        for (const tile of this.tiles.lruCache.itemList) {
            const mesh = tile.engineData.scene;
            if (!mesh) continue;

            if (mtlIndex !== undefined) {
                this.layer.materials.remove(mesh.material, true);

                const material = new Material();
                material.loadData(mesh.userData.materials[mtlIndex], () => this.layer.requestRender());
                this.layer.materials.add(material);

                const mtl = material.mtl;
                tile.engineData.materials = [mtl];
        		tile.engineData.textures = (mtl.map) ? [mtl.map] : [];
                mesh.material = mtl;
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
                        const material = new Material();
                        material.loadData(content.materials[0], () => this.layer.requestRender());
                        this.layer.materials.add(material);

                        const engineData = tile.engineData;
                        for (const mtl of engineData.materials) {
                            this.layer.materials.removeItem(mtl, true);
                        }

                        const mtl = material.mtl;
                        engineData.materials = [mtl];
                        engineData.textures = (mtl.map) ? [mtl.map] : [];
                        engineData.scene.material = mtl;
                    });

                    this.pendingRequests.set(uri, { promise, resolve, reject });

                    mesh.onBeforeRender = noop;
                };
            }
        }
    }
}
