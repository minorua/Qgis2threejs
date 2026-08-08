// (C) 2014 Minoru Akagi
// SPDX-License-Identifier: MIT
// https://github.com/minorua/Qgis2threejs

import { THREE } from "./three.js";

import type { App, Gui, Modules, Tweens } from "./types.js";

export { conf } from "./conf.js";

export const app = {} as App;

export const gui = {

	modules: [],
	dat: null

} as Gui;

export const modules = { THREE } as Modules;

export const tweens: Tweens = {};

export const deg2rad = Math.PI / 180;

/**
 * @enum {string}
 */
export const LayerType = {

	DEM: "dem",
	Point: "point",
	Line: "line",
	Polygon: "polygon",
	PointCloud: "pc"

};

export type LayerType = typeof LayerType[keyof typeof LayerType];

/**
 * @enum {number}
 */
export const MaterialType = {

	MeshLambert: 0,
	MeshPhong: 1,
	MeshToon: 2,
	MeshBasic: 8,
	MeshStandard: 7,

	Line: 3,
	MeshLine: 4,
	Sprite: 5,
	Point: 6,

	Unknown: -1

};

export type MaterialType = typeof MaterialType[keyof typeof MaterialType];

/**
 * @enum {number}
 */
export const TweenType = {

	CameraMotion: 64,
	Opacity: 65,
	Texture: 66,
	GrowingLine: 67

};

export type TweenType = typeof TweenType[keyof typeof TweenType];

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

}
