// (C) 2014 Minoru Akagi
// SPDX-License-Identifier: MIT

import { THREE } from "../three.js";

import { conf, Group } from "../core.js";
import { Materials } from "../material.js";

/**
 * @import { LayerData, BlockData } from "../types.js"
 */


export class MapLayer extends THREE.EventDispatcher {

	constructor() {
		super();

		this.id = null;
		this.properties = {};

		this.materials = new Materials();
		this.materials.addEventListener("renderRequest", () => this.requestRender());

		this.objectGroup = new Group();
		this.objectGroup.name = "layer";
		this.objects = [];
	}

	addObject(object) {
		object.userData.layerId = this.id;
		this.objectGroup.add(object);

		const o = this.objects;
		object.traverse(obj => o.push(obj));

		return this.objectGroup.children.length - 1;
	}

	addObjects(objects) {
		for (const obj of objects) {
			this.addObject(obj);
		}
	}

	clearObjects() {
		// dispose of geometries
		this.objectGroup.traverse((obj) => {
			if (obj.geometry) obj.geometry.dispose();
		});

		// dispose of materials
		this.materials.dispose();

		// remove all child objects from object group
		for (var i = this.objectGroup.children.length - 1; i >= 0; i--) {
			this.objectGroup.remove(this.objectGroup.children[i]);
		}
		this.objects = [];
	}

	visibleObjects() {
		return (this.visible) ? this.objects : [];
	}

	/**
	 * @param {LayerData | BlockData} data
	 * @param {import("../scene.js").Scene} scene
	 */
	loadData(data, scene) {
		if (data.type == "layer") {
			this.loadLayerData(data, scene);
		}
		else if (data.type) {
			this.loadBlockData(data, scene);
		}
	}

	/**
	 * @param {LayerData} data
	 * @param {import("../scene.js").Scene} scene
	 */
	loadLayerData(data, scene) {
		const p = data.properties;
		if (p !== undefined) {
			this.properties = p;
			this.objectGroup.visible = (p.visible || conf.allVisible) ? true : false;
		}

		this.sceneData = scene.userData;
	}

	/**
	 * @param {BlockData} data
	 * @param {import("../scene.js").Scene} scene
	 */
	loadBlockData(data, scene) {}

	get clickable() {
		return this.properties.clickable;
	}

	get opacity() {
		return this.materials.opacity();
	}

	set opacity(value) {
		this.materials.setOpacity(value);
		this.requestRender();
	}

	get visible() {
		return this.objectGroup.visible;
	}

	set visible(value) {
		this.objectGroup.visible = value;
		this.requestRender();
	}

	boundingBox() {
		return new THREE.Box3().setFromObject(this.objectGroup);
	}

	setWireframeMode(wireframe) {
		this.materials.setWireframeMode(wireframe);
	}

	requestRender() {
		this.dispatchEvent({type: "renderRequest"});
	}

}
