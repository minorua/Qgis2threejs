// (C) 2014 Minoru Akagi
// SPDX-License-Identifier: MIT
// https://github.com/minorua/Qgis2threejs

import { THREE } from "./three.js";

export const modules = { THREE };

export { conf } from "./conf.js";

export const app = {};

export const gui = {

	modules: [],
	dat: null

};

export const Tweens = {};

export const deg2rad = Math.PI / 180;

export const LayerType = {

	DEM: "dem",
	Point: "point",
	Line: "line",
	Polygon: "polygon",
	PointCloud: "pc"

};

export const MaterialType = {

	MeshLambert: 0,
	MeshPhong: 1,
	MeshToon: 2,
	Line: 3,
	MeshLine: 4,
	Sprite: 5,
	Point: 6,
	MeshStandard: 7,
	Unknown: -1

};

export const KeyframeType = {

	CameraMotion: 64,
	Opacity: 65,
	Texture: 66,
	GrowingLine: 67

};

export const UV = {

	i: new THREE.Vector3(1, 0, 0),
	j: new THREE.Vector3(0, 1, 0),
	k: new THREE.Vector3(0, 0, 1)

};


export class Group extends THREE.Group {

	add(object) {
		super.add(object);
		object.updateMatrixWorld();
		return this;
	}

	clear() {
		for (let i = this.children.length - 1; i >= 0; i--) {
			this.remove(this.children[i]);
		}
		return this;
	}

}
