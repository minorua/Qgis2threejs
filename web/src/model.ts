// (C) 2017 Minoru Akagi
// SPDX-License-Identifier: MIT

import { THREE } from "./three.js";

import { app } from "./core.js";
import { base64ToUint8Array } from "./utils.js";

import type { ModelData } from "./types.js";


export class Model {

	loaded = false;
	model!: THREE.Group;
	private _callbacks: ((scene: THREE.Group) => void)[] = [];

	/**
	 * @param data
	 * @param callback Called after model data has been completely loaded.
	 */
	loadData(data: ModelData, callback: (scene: THREE.Group) => void) {
		if (data.url !== undefined) {
			this.load(data.url, callback);
		}
		else {
			const bytes = base64ToUint8Array(data.base64);
			this.loadBytes(bytes.buffer, data.ext, data.resourcePath, callback);
		}
	}

	// callback is called when model has been completely loaded
	load(url: string, callback: (scene: THREE.Group) => void) {
		app.loadModelFile(url, (model) => {
			this.model = model;
			this._loadCompleted(callback);
		});
	}

	loadBytes(data: Uint8Array, ext: string, resourcePath: string, callback: (scene: THREE.Group) => void) {
		app.loadModelData(data, ext, resourcePath, (model) => {
			this.model = model;
			this._loadCompleted(callback);
		});
	}

	_loadCompleted(anotherCallback?: (scene: THREE.Group) => void) {
		this.loaded = true;

		for (const callback of this._callbacks) {
			callback(this.model);
		}
		this._callbacks.length = 0;

		if (anotherCallback) anotherCallback(this.model);
	}

	callbackOnLoad(callback: (scene: THREE.Group) => void) {
		if (this.loaded) return callback(this.model);

		this._callbacks.push(callback);
	}

}


export class Models extends THREE.EventDispatcher {

	models: Model[] = [];
	cache: Record<string, Model> = {};

	loadData(data: ModelData[]) {
		const callback = (model) => {
			this.dispatchEvent({ type: "modelLoaded", model: model });
		};

		for (const modelData of data) {
			const { url } = modelData;

			let model = this.cache[url];

			if (model === undefined) {
				model = new Model();
				model.loadData(modelData, callback);

				if (url !== undefined) {
					this.cache[url] = model;
				}
			}

			this.models.push(model);
		}
	}

	get(index: number) {
		return this.models[index];
	}

	clear() {
		this.models.length = 0;
	}

}
