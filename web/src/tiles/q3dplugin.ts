// (C) 2022 Minoru Akagi
// SPDX-License-Identifier: MIT

// https://github.com/NASA-AMMOS/3DTilesRendererJS/blob/master/src/core/renderer/API.md

import { THREE } from "../three.js";

import { GridGeometry } from "../layer/demlayer.js";
import { Material } from "../material.js";
import { decodeBase64TypedArrayObject } from "../utils.js";

import type { TilesRenderer } from "lib/3d-tiles-renderer/3d-tiles-renderer.js";
import type { MapLayer } from "../layer/layer.js";
import type { ParsedDEMGridData } from "../types.js";


export class Q3DPlugin {

    name: string = "Q3D_PLUGIN";
    priority: number = 0;
    tiles: typeof TilesRenderer;
    tileset;
    pendingRequests = new Map();
    layer: MapLayer;

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

        console.info("Requesting tile data...", url, options);

        window.requestTileData(url);

        return promise;
    }

    dataReceived(url, data) {
        const pending = this.pendingRequests.get(url);
        if (!pending) return;

        console.info("Tile data received: ", url, data);

        pending.resolve(data);
        this.pendingRequests.delete(this);
    }

    /**
     * @param content
     * @param {Tile} tile
     * @param {string} extension
     */
	parseTile(content, tile, extension, url, abortSignal) {

        console.info("parseTile", extension, content);
        console.info(tile);

        const box = tile.boundingVolume.box;
        console.info("Box", box);

        const geometry = new GridGeometry();
        const material = new Material();
        material.loadData(content.material, () => {
            // TODO: requestRender()
        });

        const mesh = new THREE.Mesh(geometry, material.mtl);
        mesh.position.fromArray(box);

        const geom_data = content.grid;
        const build = (grid_data: ParsedDEMGridData) => {
            geometry.loadData(grid_data.dem_values, grid_data.columns, grid_data.rows, geom_data.extent, grid_data.nodata, geom_data.segments);
            mesh.material.needsUpdate = true;		// update shader after computing vertex normals

            // TODO: THIS IS DEBUG CODE.
            const helper = new THREE.Box3Helper(
                geometry.boundingBox,
                0xffff00
            );
            helper.updateMatrixWorld();     // necessary because this is not called before rendering

            mesh.add(helper);

            // this.buildAuxiliaryObjects(layer, geom, mesh);

            // layer.requestRender();
        };

        const grid = geom_data.grid;
        if ("url" in grid) {
            // app.loadJSONBinaryFile(grid.url).then(build);
        }
        else {
            decodeBase64TypedArrayObject(grid).then(build);
        }

        // TODO: THIS IS DEBUG CODE.
        this.layer.materials.add(material);

        const { engineData } = tile;
        engineData.materials = [material.mtl];
		engineData.geometry = [geometry];
		engineData.textures = [];
        engineData.scene = mesh;
		engineData.metadata = null;

        return Promise.resolve(true);
	}

    /**
     * @param content
     * @param {Tile} tile
     * @param {string} extension
     */
	parseTileDebug(content, tile, extension, url, abortSignal) {

        console.info("parseTile", extension, content);
        console.info(tile);

        const box = tile.boundingVolume.box;
        console.info("Box", box);

        const m = new Material();
        m.loadData(content.material, () => {
            // TODO: requestRender()
        });

        let material = m.mtl;
        if (true) {
            material = new THREE.MeshLambertMaterial({
                color: Math.random() * 0xffffff,
                side: THREE.DoubleSide
            });
        }

        const geometry = new THREE.PlaneGeometry(1, 1, 128, 128);
        const mesh = new THREE.Mesh(geometry, material);
        mesh.position.fromArray(box);
        mesh.scale.set(box[3] * 2, box[7] * 2, box[11] * 2);

        // TODO: THIS IS DEBUG CODE.
        geometry.computeBoundingBox();
        const helper = new THREE.Box3Helper(
            geometry.boundingBox,
            0xffffff
        );
        helper.updateMatrixWorld();     // necessary because this is not called before rendering

        mesh.add(helper);

        // TODO: THIS IS DEBUG CODE.
        this.layer.materials.add(m);

        const { engineData } = tile;
        engineData.materials = [material];
		engineData.geometry = [geometry];
		engineData.textures = [];
        engineData.scene = mesh;
		engineData.metadata = null;

        return Promise.resolve(true);
	}

    /**
     * @param {Tile} tile
     */
	disposeTile(tile) {

		if (/.subtree$/i.test(tile.content?.uri)) {

            /*
			// TODO: ideally the plugin doesn't need to know about children being processed
			tile.children.forEach(child => {

				// TODO: there should be a reliable way for removing children like this.
				this.tiles.processNodeQueue.remove(child);

			});
			tile.children.length = 0;
            */

		}

	}

}
