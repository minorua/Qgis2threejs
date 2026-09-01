// (C) 2022 Minoru Akagi
// SPDX-License-Identifier: MIT

// https://github.com/NASA-AMMOS/3DTilesRendererJS/blob/master/src/core/renderer/API.md

import { buildTile } from "../layer/demlayer.js";

import type { TilesRenderer } from "lib/3d-tiles-renderer/3d-tiles-renderer.js";
import type { MapLayer } from "../layer/layer.js";


export class Q3DPlugin {

    name: string = "Q3D_PLUGIN";
    priority: number = 0;
    tiles: typeof TilesRenderer;
    tileset;
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
    fetchData(url, options) {
        if (typeof window.requestTileData !== "function") return;

        const pending = this.pendingRequests.get(url);
        if (pending) return pending.promise;

        let resolve, reject;
        const promise = new Promise((res, rej) => {
            resolve = res;
            reject = rej;
        });

        this.pendingRequests.set(url, { promise, resolve, reject });

        console.debug("Requesting tile data...", url, options);

        window.requestTileData(url);

        return promise;
    }

    dataReceived(url, data) {
        const pending = this.pendingRequests.get(url);
        if (!pending) return;

        console.debug("Tile data received: ", url, data);

        pending.resolve(data);
        this.pendingRequests.delete(this);
    }

    /**
     * @param content
     * @param {Tile} tile
     * @param {string} extension
     */
	parseTile(content, tile, extension, url, abortSignal) {
        buildTile(this.layer, content, tile, this.showBoundingBox, this.showBoundingVolume);

        return Promise.resolve(true);
	}

    /**
     * @param {Tile} tile
     */
	disposeTile(tile) {
        /*
		if (/.subtree$/i.test(tile.content?.uri)) {

			// TODO: ideally the plugin doesn't need to know about children being processed
			tile.children.forEach(child => {

				// TODO: there should be a reliable way for removing children like this.
				this.tiles.processNodeQueue.remove(child);

			});
			tile.children.length = 0;

		}
        */
	}

}
