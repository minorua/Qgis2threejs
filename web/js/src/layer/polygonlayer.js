// (C) 2014 Minoru Akagi
// SPDX-License-Identifier: MIT

import { THREE } from "../three.js";

import { deg2rad, LayerType, UV } from "../core.js";
import { BuilderBase, VectorLayer } from "./vectorlayer.js";
import { arrayToVec2Array } from "../utils.js";


export class PolygonLayer extends VectorLayer {

	BuilderFactory = {
		"Polygon": PolygonBuilder,
		"Extruded": ExtrudedBuilder,
		"Overlay": OverlayBuilder
	}

	constructor() {
		super();

		this.type = LayerType.Polygon;

		// for overlay
		this.borderVisible = true;
		this.sideVisible = true;
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

    createObjects(f) {
        return [this.createObject(f)];
    }

    createObject(f) {}

}


class PolygonBuilder extends Builder {

	constructor(layer) {
		super("Polygon", layer)
	}

	createObject(f) {
		const t = f.geom.triangles;

		const geom = new THREE.BufferGeometry();
		geom.setAttribute("position", new THREE.Float32BufferAttribute(t.v, 3));
		geom.setIndex(t.f);
		return new THREE.Mesh(geom, this.materials.mtl(f.mtl.idx));
	}

}


class ExtrudedBuilder extends Builder {

	constructor(layer) {
		super("Extruded", layer)
	}

	createObject(f) {
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

	constructor(layer) {
		super("Overlay", layer)
	}

	createObject(f) {
		const { sceneData } = this.layer;

		const t = f.geom.triangles;
		const geom = new THREE.BufferGeometry();
		geom.setIndex(t.f);
		geom.setAttribute("position", new THREE.Float32BufferAttribute(t.v, 3));
		geom.computeVertexNormals();

		const mesh = new THREE.Mesh(geom, this.materials.mtl(f.mtl.idx));

		const { rotation } = sceneData.baseExtent;
		if (rotation) {
			// rotate around center of base extent
			mesh.position.copy(sceneData.pivot).negate();
			mesh.position.applyAxisAngle(UV.k, rotation * deg2rad);
			mesh.position.add(sceneData.pivot);
			mesh.rotateOnAxis(UV.k, rotation * deg2rad);
		}

		if (f.geom.brdr === undefined) return mesh;

		// borders
		const bMtl = this.materials.mtl(f.mtl.brdr);

		for (const boundaries of f.geom.brdr) {
			for (const vertices of boundaries) {
				mesh.add(new THREE.Line(
					new THREE.BufferGeometry().setAttribute("position", new THREE.Float32BufferAttribute(vertices, 3)),
					bMtl)
				);
			}
		}
		return mesh;
	}

}
