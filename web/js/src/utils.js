// (C) 2014 Minoru Akagi
// SPDX-License-Identifier: MIT

import { THREE } from "./three.js";

export const E = (id) => document.getElementById(id);

// Put a stick to given position (for debugging)
let _stick_mat;
export const putStick = (scene, x, y, zFunc, h = 0.2) => {
	if (_stick_mat === undefined) {
		_stick_mat = new THREE.LineBasicMaterial({ color: 0xff0000 });
	}
	const z = zFunc(x, y);
	const geom = new THREE.BufferGeometry().setFromPoints([
		new THREE.Vector3(x, y, z + h),
		new THREE.Vector3(x, y, z)
	]);
	const stick = new THREE.Line(geom, _stick_mat);
	scene.add(stick);
};

// convert latitude and longitude in degrees to the following format
// Ndd°mm′ss.ss″, Eddd°mm′ss.ss″
export const convertToDMS = (lat, lon) => {
	const toDMS = (degrees) => {
		var deg = Math.floor(degrees),
			m = (degrees - deg) * 60,
			min = Math.floor(m),
			sec = (m - min) * 60;
		return deg + "°" + ("0" + min).slice(-2) + "′" + ((sec < 10) ? "0" : "") + sec.toFixed(2) + "″";
	}

	return ((lat < 0) ? "S" : "N") + toDMS(Math.abs(lat)) + ", " +
		((lon < 0) ? "W" : "E") + toDMS(Math.abs(lon));
};

export const createWallGeometry = (vert, bzFunc) => {
	const positions = [];
	const indices = [];

	for (let i = 0; i < vert.length; i += 3) {
		const x = vert[i];
		const y = vert[i + 1];

		positions.push(
			x, y, vert[i + 2],
			x, y, bzFunc(x, y)
		);
	}

	for (let i = 1, v = 1, n = vert.length / 3; i < n; i++, v += 2) {
		indices.push(
			v - 1, v, v + 1,
			v + 1, v, v + 2
		);
	}

	const geom = new THREE.BufferGeometry();
	geom.setAttribute("position", new THREE.Float32BufferAttribute(positions, 3));
	geom.setIndex(indices);
	return geom;
};

export const arrayToVec2Array = (points) => {
	return points.map(([x, y]) => new THREE.Vector2(x, y));
};

export const flatArrayToVec2Array = (vertices, itemSize) => {
	itemSize = itemSize || 2;
	const pts = [];
	for (let i = 0; i < vertices.length; i += itemSize) {
		pts.push(new THREE.Vector2(vertices[i], vertices[i + 1]));
	}
	return pts;
};

export const base64ToUint8Array = (base64) => {
	var bin = atob(base64);
	var len = bin.length;
	var bytes = new Uint8Array(len);
	for (var i = 0; i < len; i++) {
		bytes[i] = bin.charCodeAt(i);
	}
	return bytes;
};
