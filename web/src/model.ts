// (C) 2017 Minoru Akagi
// SPDX-License-Identifier: MIT

import { THREE } from "./three.js";

import { app } from "./core.js";
import { base64ToUint8Array } from "./utils.js";

import type { ModelData, ModelEventMap, ModelObject } from "./types.js";


export class Model {

	loaded = false;
	model!: ModelObject;
	private _callbacks: ((obj: ModelObject) => void)[] = [];

	/**
	 * @param data
	 * @param callback Called after model data has been completely loaded.
	 */
	loadData(data: ModelData, callback: (obj: ModelObject) => void) {
		if (data.url !== undefined) {
			this.load(data.url, callback);
		}
		else {
			const bytes = base64ToUint8Array(data.base64);
			this.loadBytes(bytes.buffer, data.ext, data.resourcePath, callback);
		}
	}

	// callback is called when model has been completely loaded
	load(url: string, callback: (obj: ModelObject) => void) {
		app.loadModelFile(url, (model) => {
			this.model = model;
			this._loadCompleted(callback);
		});
	}

	loadBytes(data: Uint8Array, ext: string, resourcePath: string, callback: (obj: ModelObject) => void) {
		app.loadModelData(data, ext, resourcePath, (model) => {
			this.model = model;
			this._loadCompleted(callback);
		});
	}

	_loadCompleted(anotherCallback?: (obj: ModelObject) => void) {
		this.loaded = true;

		for (const callback of this._callbacks) {
			callback(this.model);
		}
		this._callbacks.length = 0;

		if (anotherCallback) anotherCallback(this.model);
	}

	callbackOnLoad(callback: (obj: ModelObject) => void) {
		if (this.loaded) return callback(this.model);

		this._callbacks.push(callback);
	}

}


export class Models extends THREE.EventDispatcher {

	models: Model[] = [];
	cache: Record<string, Model> = {};

	declare addEventListener: THREE.EventDispatcher<ModelEventMap>["addEventListener"];
	declare dispatchEvent: THREE.EventDispatcher<ModelEventMap>["dispatchEvent"];

	loadData(data: ModelData[]) {
		const callback = (obj: ModelObject) => {
			this.dispatchEvent({ type: "modelLoaded", model: obj });
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
