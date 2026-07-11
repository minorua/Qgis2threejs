// (C) 2014 Minoru Akagi
// SPDX-License-Identifier: MIT

import { THREE } from "../three.js";

import { deg2rad, LayerType, UV } from "../core.js";
import { VectorLayer } from "./vectorlayer.js";
import { arrayToVec2Array } from "../utils.js";


export class PolygonLayer extends VectorLayer {

	constructor() {
		super();

		this.type = LayerType.Polygon;

		// for overlay
		this.borderVisible = true;
		this.sideVisible = true;
	}

	build(features, startIndex) {

		if (this.properties.objType !== this._lastObjType) this._createObject = null;

		const createObject = this._createObject || this.createObjFunc(this.properties.objType);

		for (let fidx = 0; fidx < features.length; fidx++) {
			const f = features[fidx];
			const obj = createObject(f);

			obj.userData.properties = f.prop;

			this.addFeature(fidx + startIndex, f, [obj]);
		}

		this._lastObjType = this.properties.objType;
		this._createObject = createObject;
	}

	createObjFunc(objType) {
		const materials = this.materials;

		if (objType == "Polygon") {
			return (f) => {
				const geom = new THREE.BufferGeometry();
				geom.setAttribute("position", new THREE.Float32BufferAttribute(f.geom.triangles.v, 3));
				geom.setIndex(f.geom.triangles.f);
				return new THREE.Mesh(geom, materials.mtl(f.mtl.idx));
			};
		}
		else if (objType == "Extruded") {
			const createSubObject = (f, polygon, z) => {
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
					materials.mtl(f.mtl.idx)
				);
				mesh.position.z = z;

				if (f.mtl.edge !== undefined) {
					const edgeMtl = materials.mtl(f.mtl.edge);

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
				}
				return mesh;
			};

			return (f) => {
				const { polygons, centroids } = f.geom;

				if (polygons.length === 1) {
					return createSubObject(f, polygons[0], centroids[0][2]);
				}

				const group = new THREE.Group();

				for (let i = 0; i < polygons.length; i++) {
					group.add(createSubObject(f, polygons[i], centroids[i][2]));
				}

				return group;
			};
		}
		else if (objType == "Overlay") {

			return (f) => {
				const geom = new THREE.BufferGeometry();
				geom.setIndex(f.geom.triangles.f);
				geom.setAttribute("position", new THREE.Float32BufferAttribute(f.geom.triangles.v, 3));
				geom.computeVertexNormals();

				const mesh = new THREE.Mesh(geom, materials.mtl(f.mtl.idx));

				const { rotation } = this.sceneData.baseExtent;
				if (rotation) {
					// rotate around center of base extent
					mesh.position.copy(this.sceneData.pivot).negate();
					mesh.position.applyAxisAngle(UV.k, rotation * deg2rad);
					mesh.position.add(this.sceneData.pivot);
					mesh.rotateOnAxis(UV.k, rotation * deg2rad);
				}

				// borders
				if (f.geom.brdr !== undefined) {
					const bMtl = materials.mtl(f.mtl.brdr);

					for (const boundaries of f.geom.brdr) {
						for (const vertices of boundaries) {
							const bGeom = new THREE.BufferGeometry().setAttribute("position", new THREE.Float32BufferAttribute(vertices, 3));

							mesh.add(new THREE.Line(bGeom, bMtl));
						}
					}
				}
				return mesh;
			};
		}
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
