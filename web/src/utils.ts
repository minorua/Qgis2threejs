// (C) 2014 Minoru Akagi
// SPDX-License-Identifier: MIT

import { THREE } from "./three.js";

import type { Base64Data, Vec3 } from "./types.js";

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

export const getBoundaryLines = (geometry: THREE.BufferGeometry): Vec3[][] => {
	const vertices = geometry.getAttribute("position").array;
	const indices = geometry.getIndex().array;

	const edgeKey = (a: number, b: number) => (a < b) ? `${a},${b}` : `${b},${a}`;

	const unpairedHalfEdge = new Set<string>();
	for (let i = 0; i < indices.length; i += 3) {
		const tri = [indices[i], indices[i + 1], indices[i + 2]];

		for (let j = 0; j < 3; j++) {
			const key = edgeKey(tri[j], tri[(j + 1) % 3]);

			if (unpairedHalfEdge.has(key))
				unpairedHalfEdge.delete(key);
			else
				unpairedHalfEdge.add(key);
		}
	}

	const adjacency = new Map<number, number[]>();
	for (const key of unpairedHalfEdge) {
		const [a, b] = key.split(",").map(Number);

		if (!adjacency.has(a)) adjacency.set(a, []);
		if (!adjacency.has(b)) adjacency.set(b, []);
		adjacency.get(a).push(b);
		adjacency.get(b).push(a);
	}

	const remaining = unpairedHalfEdge;
	const boundaries: Vec3[][] = [];

	while (remaining.size > 0) {
		const [firstKey] = remaining;

		const start = Number(firstKey.split(",")[0]);
		let prev = -1;
		let curr = start;

		const line: number[] = [start];

		while (true) {
			const next = (adjacency.get(curr) || []).find(v => v !== prev);
			if (next === undefined) break;

			remaining.delete(edgeKey(curr, next));

			line.push(next);
			prev = curr;
			curr = next;

			if (curr === start) break;
		}

		boundaries.push(line.map((vi) => [vertices[vi * 3], vertices[vi * 3 + 1], vertices[vi * 3 + 2]]));
	}

	return boundaries;
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
	if (typeof Uint8Array.fromBase64 === "function") {
	    return Uint8Array.fromBase64(base64);
  	}
	var bin = atob(base64);
	var len = bin.length;
	var bytes = new Uint8Array(len);
	for (var i = 0; i < len; i++) {
		bytes[i] = bin.charCodeAt(i);
	}
	return bytes;
};

export const decodeBase64TypedArrayObject = async (obj) => {
	return transformObjectValues(obj, async (value) => {
		if (value.__type__ !== undefined) {
			const bin = value as Base64Data;
			let chunk = base64ToUint8Array(bin.data).buffer;

			if (bin.compressed) {
				chunk = await decompress(chunk);
			}

			switch (bin.__type__) {
				case "f32":
					return new Float32Array(chunk);
				case "I32":
					return new Uint32Array(chunk);
			}
		}
	});
};

export const decompress = async (buf: ArrayBuffer): Promise<ArrayBuffer> => {
    const ds = new DecompressionStream("deflate");

    const stream = new Blob([buf]).stream().pipeThrough(ds);

    return await new Response(stream).arrayBuffer();
}

export const transformObjectValues = async (obj, transform) => {
	const visit = async (value) => {
		if (!value || typeof value !== "object") {
			return value;
		}

		const transformed = await transform(value, visit);
		if (transformed !== undefined) {
			return transformed;
		}

		if (Array.isArray(value)) {
			return Promise.all(value.map(visit));
		}

		const o = {};
		for (const key in value) {
			o[key] = await visit(value[key]);
		}
		return o;
	};

	return visit(obj);
};
