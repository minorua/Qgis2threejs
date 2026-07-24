// (C) 2017 Minoru Akagi
// SPDX-License-Identifier: MIT

import { THREE } from "./three.js";

import { app } from "./core.js";
import { base64ToUint8Array } from "./utils.js";


export class Model {

	constructor() {
		this.loaded = false;
	}

	/**
	 * @param {import("./types.js").ModelData} data
	 * @param {(scene: THREE.Group) => void} callback Called after model data has been completely loaded.
	 */
	loadData(data, callback) {
		if (data.url !== undefined) {
			this.load(data.url, callback);
		}
		else {
			const bytes = base64ToUint8Array(data.base64);
			this.loadBytes(bytes.buffer, data.ext, data.resourcePath, callback);
		}
	}

	// callback is called when model has been completely loaded
	load(url, callback) {
		app.loadModelFile(url, (model) => {
			this.model = model;
			this._loadCompleted(callback);
		});
	}

	loadBytes(data, ext, resourcePath, callback) {
		app.loadModelData(data, ext, resourcePath, (model) => {
			this.model = model;
			this._loadCompleted(callback);
		});
	}

	_loadCompleted(anotherCallback) {
		this.loaded = true;

		if (this._callbacks !== undefined) {
			for (const callback of this._callbacks) {
				callback(this.model);
			}
			this._callbacks = [];
		}

		if (anotherCallback) anotherCallback(this.model);
	}

	callbackOnLoad(callback) {
		if (this.loaded) return callback(this.model);

		if (this._callbacks === undefined) this._callbacks = [];
		this._callbacks.push(callback);
	}

}


export class Models extends THREE.EventDispatcher {

	constructor() {
		super();

		this.models = [];
		this.cache = {};
	}

	/**
	 * @param {import("./types.js").ModelData[]} data
	 */
	loadData(data) {
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

	get(index) {
		return this.models[index];
	}

	clear() {
		this.models = [];
	}

}
