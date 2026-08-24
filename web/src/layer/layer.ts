// (C) 2014 Minoru Akagi
// SPDX-License-Identifier: MIT

import { THREE } from "../three.js";

import { conf, Group } from "../core.js";
import { Materials } from "../material.js";

import type { BlockData, LayerData, LayerType, LayerProperties, ObjectEventMap, SceneProperties } from "../types.js";
import type { Scene } from "../scene.js";


export class MapLayer extends THREE.EventDispatcher {

	id: number | null = null
	properties: LayerProperties | Record<string, never> = {};
	objects: THREE.Object3D[] = [];

	declare type: LayerType;
	declare materials: Materials;
	declare objectGroup: Group;
	declare sceneData: SceneProperties;
	declare addEventListener: THREE.EventDispatcher<ObjectEventMap>["addEventListener"];
	declare dispatchEvent: THREE.EventDispatcher<ObjectEventMap>["dispatchEvent"];

	constructor() {
		super();

		this.materials = new Materials();
		this.materials.addEventListener("renderRequest", () => this.requestRender());

		this.objectGroup = new Group();
	}

	addObject(object: THREE.Object3D) {
		object.userData.layerId = this.id;
		this.objectGroup.add(object);

		const o = this.objects;
		object.traverse(obj => o.push(obj));

		return this.objectGroup.children.length - 1;
	}

	addObjects(objects: THREE.Object3D[]) {
		for (const obj of objects) {
			this.addObject(obj);
		}
	}

	clearObjects() {
		this.objectGroup.traverse((obj) => {
			if (obj.geometry) obj.geometry.dispose();
		});

		this.materials.dispose();

		this.objectGroup.clear();

		this.objects.length = 0;
	}

	visibleObjects() {
		return (this.visible) ? this.objects : [];
	}

	loadData(data: LayerData | BlockData, scene: Scene): void {
		if (data.type == "layer") {
			this.loadLayerData(data, scene);
		}
		else if (data.type) {
			this.loadBlockData(data, scene);
		}
	}

	loadLayerData(data: LayerData, scene: Scene): void {
		const p = data.properties;
		if (p !== undefined) {
			this.properties = p;
			this.objectGroup.name = p.name;
			this.objectGroup.visible = (p.visible || conf.allVisible) ? true : false;
		}

		this.sceneData = scene.userData;
	}

	loadBlockData(data: BlockData, scene: Scene): void { }

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
		this.dispatchEvent({ type: "renderRequest" });
	}

}
