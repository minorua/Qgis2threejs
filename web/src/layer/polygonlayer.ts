// (C) 2014 Minoru Akagi
// SPDX-License-Identifier: MIT

import { THREE } from "../three.js";

import { LayerType } from "../core.js";
import { BuilderBase, VectorLayer } from "./vectorlayer.js";
import { arrayToVec2Array, getBoundaryLines } from "../utils.js";

import type { FeatureData, MeshData } from "../types.js";


export class PolygonLayer extends VectorLayer {

	type = LayerType.Polygon;

	borderVisible = true;	// for overlay
	sideVisible = true;		// for overlay

	BuilderFactory = {
		"Polygon": PolygonBuilder,
		"Extruded": ExtrudedBuilder,
		"Overlay": OverlayBuilder
	}

	buildLabels(features) {
		super.buildLabels(features, f => f.geom.centroids);
	}

	setBorderVisible(visible) {
		if (this.properties.objType != "Overlay") return;

		this.objectGroup.children.forEach((parent) => {
			for (var i = 0, l = parent.children.length; i < l; i++) {
				var obj = parent.children[i];
				if (obj instanceof THREE.Line) obj.visible = visible;
			}
		});
		this.borderVisible = visible;
	}

	setSideVisible(visible) {
		if (this.properties.objType != "Overlay") return;

		this.objectGroup.children.forEach((parent) => {
			for (const obj of parent.children) {
				if (obj instanceof THREE.Mesh) obj.visible = visible;
			}
		});
		this.sideVisible = visible;
	}
}


class Builder extends BuilderBase {

	createObjects(f: FeatureData) {
		return [this.createObject(f)];
	}

	createObject(f: FeatureData) { }

}


class PolygonBuilder extends Builder {

	type = "Polygon";

	createObject(f: FeatureData) {
		const m = f.geom as MeshData;

		const geom = new THREE.BufferGeometry();
		geom.setAttribute("position", new THREE.Float32BufferAttribute(m.vertices, 3));
		geom.setIndex(m.indices);
		return new THREE.Mesh(geom, this.materials.mtl(f.mtl.idx));
	}

}


class ExtrudedBuilder extends Builder {

	type = "Extruded";

	createObject(f: FeatureData) {
		const { polygons, centroids } = f.geom;

		if (polygons.length === 1) {
			return this.createSubObject(f, polygons[0], centroids[0][2]);
		}

		const group = new THREE.Group();

		for (let i = 0; i < polygons.length; i++) {
			group.add(this.createSubObject(f, polygons[i], centroids[i][2]));
		}

		return group;
	}

	createSubObject(f, polygon, z) {
		const shape = new THREE.Shape(arrayToVec2Array(polygon[0]));

		for (let i = 1; i < polygon.length; i++) {
			shape.holes.push(new THREE.Path(arrayToVec2Array(polygon[i])));
		}

		const { h } = f.geom;

		const mesh = new THREE.Mesh(
			new THREE.ExtrudeGeometry(shape, {
				bevelEnabled: false,
				depth: h
			}),
			this.materials.mtl(f.mtl.idx)
		);
		mesh.position.z = z;

		if (f.mtl.edge === undefined) return mesh;

		// edges
		const edgeMtl = this.materials.mtl(f.mtl.edge);

		for (const boundary of polygon) {
			const v = [];

			for (const point of boundary) {
				v.push(point[0], point[1], 0);
			}

			const hGeom = new THREE.BufferGeometry().setAttribute("position", new THREE.Float32BufferAttribute(v, 3));

			const bottomEdge = new THREE.Line(hGeom, edgeMtl);
			mesh.add(bottomEdge);

			const topEdge = new THREE.Line(hGeom, edgeMtl);
			topEdge.position.z = h;
			mesh.add(topEdge);

			// vertical edges
			for (let i = 0; i < boundary.length - 1; i++) {
				const [x, y] = boundary[i];

				const vGeom = new THREE.BufferGeometry().setAttribute("position", new THREE.Float32BufferAttribute([x, y, 0, x, y, h], 3));
				mesh.add(new THREE.Line(vGeom, edgeMtl));
			}
		}
		return mesh;
	};
}


class OverlayBuilder extends Builder {

	type = "Overlay";

	createObject(f: FeatureData) {
		const m = f.geom as MeshData;

		const geom = new THREE.BufferGeometry();
		geom.setAttribute("position", new THREE.Float32BufferAttribute(m.vertices, 3));
		geom.setIndex(m.indices);
		geom.computeVertexNormals();

		const mesh = new THREE.Mesh(geom, this.materials.mtl(f.mtl.idx));

		// boundaries
		if (f.mtl.brdr !== undefined) {
			const bMtl = this.materials.mtl(f.mtl.brdr);

			for (const boundary of getBoundaryLines(geom)) {
				const line = new THREE.Line(
					new THREE.BufferGeometry().setAttribute("position", new THREE.Float32BufferAttribute(boundary.flat(), 3)),
					bMtl
				);
				mesh.add(line);
			}
		}
		return mesh;
	}

}
