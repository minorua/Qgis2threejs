// (C) 2014 Minoru Akagi
// SPDX-License-Identifier: MIT

import { THREE } from "./three.js";

import { app, conf, deg2rad, modules, Group, LayerType, UV } from "./core.js";
import { MapLayer } from "./layer.js";
import { Materials } from "./material.js";
import { Models } from "./model.js";
import { arrayToVec2Array, createWallGeometry } from "./utils.js";


class VectorLayer extends MapLayer {

	constructor() {
		super();
		this.features = [];
		this.labels = [];
	}

	build(features, startIndex) {}

	addFeature(featureIdx, f, objs) {
		super.addObjects(objs);

		for (const obj of objs) {
			obj.userData.featureIdx = featureIdx;
		}
		f.objs = objs;

		this.features[featureIdx] = f;
		return f;
	}

	clearLabels() {
		this.labels = [];
		if (this.labelGroup) this.labelGroup.clear();
		if (this.labelConnectorGroup) this.labelConnectorGroup.clear();
	}

	buildLabels(features, getPointsFunc) {
		if (this.properties.label === undefined || getPointsFunc === undefined) return;

		const label = this.properties.label;
		const bs = this.sceneData.baseExtent.width * 0.016;
		const sc = bs * Math.pow(1.2, label.size);

		const hasOtl = (label.olcolor !== undefined);
		const hasConn = (label.cncolor !== undefined);

		let line_mtl;
		if (hasConn) {
			line_mtl = new THREE.LineBasicMaterial({
				color: label.cncolor
			});
		}

		const hasUnderline = Boolean(hasConn && label.underline);
		let ul_geom, onBeforeRender;
		if (hasUnderline) {
			ul_geom = new THREE.BufferGeometry();
			ul_geom.setAttribute("position", new THREE.Float32BufferAttribute([0, 0, 0, 1, 0, 0], 3));

			onBeforeRender = function (renderer, scene, camera, geometry, material, group) {
				this.quaternion.copy(camera.quaternion);
				this.updateMatrixWorld();
			};
		}

		const canvas = document.createElement("canvas");
		const ctx = canvas.getContext("2d");

		const th = conf.label.canvasHeight;
		const ch = th;
		const font = th + "px " + (label.font || "sans-serif");

		canvas.height = ch;

		for (let i = 0, l = features.length; i < l; i++) {
			const f = features[i];
			const text = f.lbl;
			if (!text) continue;

			let partIdx = 0;
			getPointsFunc(f).forEach((pt) => {

				// label position
				const vec = new THREE.Vector3(pt[0], pt[1], (label.relative) ? pt[2] + f.lh : f.lh);

				// render label text
				ctx.font = font;
				const tw = ctx.measureText(text).width + 2;
				const cw = THREE.MathUtils.ceilPowerOfTwo(tw);

				canvas.width = cw;
				ctx.clearRect(0, 0, cw, ch);

				if (label.bgcolor !== undefined) {
					ctx.fillStyle = label.bgcolor;
					ctx.beginPath();
					ctx.roundRect((cw - tw) / 2, (ch - th) / 2, tw, th, 4);
					ctx.fill();
				}
				ctx.font = font;
				ctx.textAlign = "center";
				ctx.textBaseline = "middle";

				const x = cw / 2;
				const y = ch / 2;

				if (hasOtl) {
					// outline effect
					ctx.fillStyle = label.olcolor;
					for (let j = 0; j < 9; j++) {
						if (j != 4) ctx.fillText(text, x + Math.floor(j / 3) - 1, y + j % 3 - 1);
					}
				}

				ctx.fillStyle = label.color;
				ctx.fillText(text, x, y);

				const tex = new THREE.TextureLoader(app.loadingManager).load(canvas.toDataURL(), () => this.requestRender());
				tex.colorSpace = THREE.SRGBColorSpace;

				const mtl = new THREE.SpriteMaterial({
					map: tex,
					transparent: true
				});

				const sprite = new THREE.Sprite(mtl);
				if (hasUnderline) {
					sprite.center.set((1 - tw / cw) * 0.5, 0);
				}
				else {
					sprite.center.set(0.5, 0);
				}
				sprite.position.copy(vec);
				sprite.scale.set(sc * cw / ch, sc, 1);

				sprite.userData.layerId = this.id;
				sprite.userData.properties = f.prop;
				sprite.userData.objs = f.objs;
				sprite.userData.partIdx = partIdx;
				sprite.userData.isLabel = true;

				this.labelGroup.add(sprite);

				if (conf.label.clickable) this.labels.push(sprite);

				if (hasConn) {
					// a connector
					const geom = new THREE.BufferGeometry();
					geom.setAttribute("position", new THREE.Float32BufferAttribute(vec.toArray().concat(pt), 3));

					const conn = new THREE.Line(geom, line_mtl);
					conn.userData = sprite.userData;

					this.labelConnectorGroup.add(conn);

					if (hasUnderline) {
						const underline = new THREE.Line(ul_geom, line_mtl);
						underline.position.copy(vec);
						underline.scale.x = sc * tw / th;
						underline.updateMatrixWorld();
						underline.onBeforeRender = onBeforeRender;
						conn.add(underline);
					}
				}
				partIdx++;
			});
		}
	}

	loadData(data, scene) {
		if (data.type == "layer") {
			this.clearObjects();
			this.clearLabels();
			super.loadData(data, scene);

			this.features = [];

			if (this.properties.label !== undefined) {
				if (this.labelGroup === undefined) {
					this.labelGroup = new Group();
					this.labelGroup.userData.layerId = this.id;
					this.labelGroup.visible = this.visible;
					scene.labelGroup.add(this.labelGroup);
				}

				if (this.labelConnectorGroup === undefined) {
					this.labelConnectorGroup = new Group();
					this.labelConnectorGroup.userData.layerId = this.id;
					this.labelConnectorGroup.visible = this.visible;
					scene.labelConnectorGroup.add(this.labelConnectorGroup);
				}
			}

			if (data.body === undefined) return;

			if (data.body.materials !== undefined) {
				this.materials.loadData(data.body.materials);
			}

			(data.body.blocks || []).forEach((block) => {
				if (block.url !== undefined) app.loadJSONFile(block.url);
				else {
					this.build(block.features, block.startIndex);
					if (this.properties.label !== undefined) this.buildLabels(block.features);
				}
			});
		}
		else if (data.type == "block") {
			this.build(data.features, data.startIndex);
			if (this.properties.label !== undefined) this.buildLabels(data.features);
		}
	}

	get visible() {
		return this.objectGroup.visible;
	}

	set visible(value) {
		if (this.labelGroup) this.labelGroup.visible = value;
		if (this.labelConnectorGroup) this.labelConnectorGroup.visible = value;

		this.objectGroup.visible = value;
		this.requestRender();
	}

}


export class PointLayer extends VectorLayer {

	constructor() {
		super();
		this.type = LayerType.Point;
	}

	loadData(data, scene) {
		if (data.type == "layer" && data.properties.objType == "3D Model" && data.body !== undefined) {
			if (this.models === undefined) {
				this.models = new Models();
				this.models.addEventListener("modelLoaded", (event) => {
					this.materials.addFromObject3D(event.model.scene);
					this.requestRender();
				});
			}
			else {
				this.models.clear();
			}
			this.models.loadData(data.body.models);
		}
		super.loadData(data, scene);
	}

	build(features, startIndex) {
		const { objType } = this.properties;
		if (objType == "Point") {
			return this.buildPoints(features, startIndex);
		}
		else if (objType == "Billboard") {
			return this.buildBillboards(features, startIndex);
		}
		else if (objType == "3D Model") {
			return this.buildModels(features, startIndex);
		}

		let unitGeom, transform;
		if (this.cachedGeometryType === objType) {
			unitGeom = this.geometryCache;
			transform = this.transformCache;
		}
		else {
			[unitGeom, transform] = this.geomAndTransformFunc(objType);
		}

		for (let fidx = 0; fidx < features.length; fidx++) {
			const f = features[fidx];
			const { pts } = f.geom;
			const material = this.materials.mtl(f.mtl.idx);

			const meshes = [];

			for (const pt of pts) {
				const mesh = new THREE.Mesh(unitGeom, material);

				transform(mesh, f.geom, pt);
				mesh.userData.properties = f.prop;

				meshes.push(mesh);
			}

			this.addFeature(fidx + startIndex, f, meshes);
		}

		this.cachedGeometryType = objType;
		this.geometryCache = unitGeom;
		this.transformCache = transform;
	}

	geomAndTransformFunc(objType) {

		const rx = 90 * deg2rad;

		if (objType == "Sphere") {
			return [
				new THREE.SphereGeometry(1, 32, 32),
				(mesh, geom, pt) => {
					mesh.scale.setScalar(geom.r);
					mesh.position.fromArray(pt);
				}
			];
		}
		else if (objType == "Box") {
			return [
				new THREE.BoxGeometry(1, 1, 1),
				(mesh, geom, pt) => {
					mesh.scale.set(geom.w, geom.h, geom.d);
					mesh.rotation.x = rx;
					mesh.position.set(pt[0], pt[1], pt[2] + geom.h / 2);
				}
			];
		}
		else if (objType == "Disk") {
			const sz = this.sceneData.zScale;
			return [
				new THREE.CircleGeometry(1, 32),
				(mesh, geom, pt) => {
					mesh.scale.set(geom.r, geom.r * sz, 1);
					mesh.rotateOnWorldAxis(UV.i, -geom.d * deg2rad);
					mesh.rotateOnWorldAxis(UV.k, -geom.dd * deg2rad);
					mesh.position.fromArray(pt);
				}
			];
		}
		else if (objType == "Plane") {
			const sz = this.sceneData.zScale;
			return [
				new THREE.PlaneGeometry(1, 1, 1, 1),
				(mesh, geom, pt) => {
					mesh.scale.set(geom.w, geom.l * sz, 1);
					mesh.rotateOnWorldAxis(UV.i, -geom.d * deg2rad);
					mesh.rotateOnWorldAxis(UV.k, -geom.dd * deg2rad);
					mesh.position.fromArray(pt);
				}
			];
		}

		// Cylinder or Cone
		const radiusTop = (objType == "Cylinder") ? 1 : 0;
		return [
			new THREE.CylinderGeometry(radiusTop, 1, 1, 32),
			(mesh, geom, pt) => {
				mesh.scale.set(geom.r, geom.h, geom.r);
				mesh.rotation.x = rx;
				mesh.position.set(pt[0], pt[1], pt[2] + geom.h / 2);
			}
		];
	}

	buildPoints(features, startIndex) {
		for (let fidx = 0; fidx < features.length; fidx++) {
			const f = features[fidx];

			const obj = new THREE.Points(
				new THREE.BufferGeometry().setAttribute("position", new THREE.Float32BufferAttribute(f.geom.pts, 3)),
				this.materials.mtl(f.mtl.idx)
			);
			obj.userData.properties = f.prop;

			this.addFeature(fidx + startIndex, f, [obj]);
		}
	}

	buildBillboards(features, startIndex) {

		const errMtl = {
			mtl: new THREE.SpriteMaterial({color: 0xffffff}),
			callbackOnLoad: () => {}
		};

		features.forEach((f, fidx) => {

			const material = (f.mtl) ? this.materials.get(f.mtl.idx) : errMtl;

			if (!f.mtl) {
				console.warn("[" + this.properties.name + "] Billboard: There is a missing material.");
			}

			const sprites = [];
			for (const pt of f.geom.pts) {
				const sprite = new THREE.Sprite(material.mtl);

				sprite.position.fromArray(pt);
				sprite.scale.set(f.geom.size, f.geom.size, 1);
				sprite.userData.properties = f.prop;

				sprites.push(sprite);
			}

			material.callbackOnLoad(() => {
				const { image } = material.mtl.map;
				const scaleY = f.geom.size * image.height / image.width;

				for (const sprite of sprites) {
					sprite.scale.set(f.geom.size, scaleY, 1);
					sprite.updateMatrixWorld();
				}
			});

			this.addFeature(fidx + startIndex, f, sprites);
		});
	}

	buildModels(features, startIndex) {
		const q = new THREE.Quaternion(),
			  e = new THREE.Euler();

		features.forEach((f, fidx) => {
			const model = this.models.get(f.model);

			if (!model) {
				console.warn(`[${this.properties.name}] 3D Model: There is a missing model.`);
				return;
			}

			const groups = [];

			for (const pt of f.geom.pts) {
				const group = new Group();

				group.position.fromArray(pt);
				group.scale.set(1, 1, this.sceneData.zScale);
				group.userData.properties = f.prop;

				groups.push(group);
			}

			model.callbackOnLoad((loadedModel) => {
				const {
					scale,
					rotateX,
					rotateY,
					rotateZ,
					rotateO = "XYZ"
				} = f.geom;

				for (const group of groups) {
					const obj = loadedModel.scene.clone();

					obj.scale.setScalar(scale);

					q.setFromEuler(
						e.set(
							rotateX * deg2rad,
							rotateY * deg2rad,
							rotateZ * deg2rad,
							rotateO
						)
					);

					if (obj.rotation.x) {
						// Reset coordinate system to z-up and apply the specified rotation.
						obj.rotation.set(0, 0, 0);
						obj.quaternion.multiply(q);
					} else {
						// Convert y-up to z-up and apply the specified rotation.
						obj.quaternion.multiply(q);
						obj.quaternion.multiply(q.setFromEuler(e.set(Math.PI / 2, 0, 0)));
					}

					group.add(obj);
				}
			});

			this.addFeature(fidx + startIndex, f, groups);
		});
	}

	buildLabels(features) {
		super.buildLabels(features, f => f.geom.pts);
	}

}


export class LineLayer extends VectorLayer {

	constructor() {
		super();
		this.type = LayerType.Line;
	}

	clearObjects() {
		super.clearObjects();

		if (this.origMtls) {
			this.origMtls.dispose();
			this.origMtls = undefined;
		}
	}

	build(features, startIndex) {

		if (this._lastObjType !== this.properties.objType) this._createObject = null;

		const createObject = this._createObject || this.createObjFunc(this.properties.objType);

		for (let fidx = 0; fidx < features.length; fidx++) {
			const f = features[fidx];
			const objs = [];

			for (const line of f.geom.lines) {
				const obj = createObject(f, line);

				obj.userData.properties = f.prop;
				obj.userData.mtl = f.mtl;

				objs.push(obj);
			}

			this.addFeature(fidx + startIndex, f, objs);
		}

		this._lastObjType = this.properties.objType;
		this._createObject = createObject;
	}

	createObjFunc(objType) {
		const materials = this.materials;

		if (objType == "Line") {
			return (f, vertices) => {
				const obj = new THREE.Line(
					new THREE.BufferGeometry().setAttribute("position", new THREE.Float32BufferAttribute(vertices, 3)),
					materials.mtl(f.mtl.idx)
				);
				if (obj.material instanceof THREE.LineDashedMaterial) obj.computeLineDistances();
				return obj;
			};
		}
		else if (objType == "Thick Line") {
			return (f, vertices) => {
				const geom = new modules.meshline.MeshLineGeometry();
				geom.setPoints(vertices);

				const mesh = new THREE.Mesh(geom, materials.mtl(f.mtl.idx));
				mesh.raycast = modules.meshline.raycast;
				return mesh;
			};
		}
		else if (objType == "Pipe" || objType == "Cone") {
			let jointGeom, cylinGeom;
			if (objType == "Pipe") {
				jointGeom = new THREE.SphereGeometry(1, 32, 32);
				cylinGeom = new THREE.CylinderGeometry(1, 1, 1, 32);
			}
			else {
				cylinGeom = new THREE.CylinderGeometry(0, 1, 1, 32);
			}

			const axis = UV.j;
			const pt0 = new THREE.Vector3();
			const pt1 = new THREE.Vector3();
			const sub = new THREE.Vector3();

			return (f, points) => {
				const group = new Group();
				const material = materials.mtl(f.mtl.idx);

				pt0.fromArray(points[0]);
				for (let i = 1; i < points.length; i++) {
					pt1.fromArray(points[i]);

					const cylinder = new THREE.Mesh(cylinGeom, material);
					cylinder.scale.set(f.geom.r, pt0.distanceTo(pt1), f.geom.r);
					cylinder.position.set(
						(pt0.x + pt1.x) / 2,
						(pt0.y + pt1.y) / 2,
						(pt0.z + pt1.z) / 2
					);
					cylinder.quaternion.setFromUnitVectors(axis, sub.subVectors(pt1, pt0).normalize());

					group.add(cylinder);

					if (jointGeom && i < points.length - 1) {
						const joint = new THREE.Mesh(jointGeom, material);
						joint.scale.setScalar(f.geom.r);
						joint.position.copy(pt1);

						group.add(joint);
					}

					pt0.copy(pt1);
				}
				return group;
			};
		}
		else if (objType == "Box") {
			// In this method, box corners are exposed near joint when both azimuth and slope of
			// the segments of both sides are different. Also, some unnecessary faces are created.
			const jnt_idx = [
				0, 5, 4, 4, 5, 1,   // left turn - top, side, bottom
				3, 0, 7, 7, 0, 4,
				6, 3, 2, 2, 3, 7,
				4, 1, 0, 0, 1, 5,   // right turn - top, side, bottom
				1, 2, 5, 5, 2, 6,
				2, 7, 6, 6, 7, 3
			];

			return (f, points) => {
				const geometries = [];

				let geom, vf4;
				const pt0 = new THREE.Vector3(),
					  pt1 = new THREE.Vector3(),
					  sub = new THREE.Vector3(),
					  pt = new THREE.Vector3(),
					  ptM = new THREE.Vector3(),
					  scale1 = new THREE.Vector3(1, 1, 1),
					  matrix = new THREE.Matrix4(),
					  quat = new THREE.Quaternion();

				pt0.fromArray(points[0]);

				for (let i = 1, l = points.length; i < l; i++) {
					pt1.fromArray(points[i]);

					const dist = pt0.distanceTo(pt1);

					sub.subVectors(pt1, pt0);

					const rx = Math.atan2(sub.z, Math.sqrt(sub.x * sub.x + sub.y * sub.y));
					const rz = Math.atan2(sub.y, sub.x) - Math.PI / 2;

					ptM.set(
						(pt0.x + pt1.x) / 2,
						(pt0.y + pt1.y) / 2,
						(pt0.z + pt1.z) / 2
					);

					quat.setFromEuler(new THREE.Euler(rx, 0, rz, "ZXY"));
					matrix.compose(ptM, quat, scale1);

					// segment box
					geom = new THREE.BoxGeometry(f.geom.w, dist, f.geom.h);
					geom.deleteAttribute("normal");
					geom.deleteAttribute("uv");
					geom.applyMatrix4(matrix);
					geometries.push(geom);

					// joint
					// backward side
					const wh4 = [
						[-f.geom.w / 2,  f.geom.h / 2],
						[ f.geom.w / 2,  f.geom.h / 2],
						[ f.geom.w / 2, -f.geom.h / 2],
						[-f.geom.w / 2, -f.geom.h / 2]
					];

					const vb4 = [];

					for (let j = 0; j < 4; j++) {
						pt.set(wh4[j][0], -dist / 2, wh4[j][1]);
						pt.applyMatrix4(matrix);

						vb4.push(pt.x, pt.y, pt.z);
					}

					if (vf4) {
						geom = new THREE.BufferGeometry();
						geom.setAttribute("position", new THREE.Float32BufferAttribute(vf4.concat(vb4), 3));
						geom.setIndex(jnt_idx);
						geometries.push(geom);
					}

					// forward side
					vf4 = [];

					for (let j = 0; j < 4; j++) {
						pt.set(wh4[j][0], dist / 2, wh4[j][1]);
						pt.applyMatrix4(matrix);

						vf4.push(pt.x, pt.y, pt.z);
					}

					pt0.copy(pt1);
				}

				return new THREE.Mesh(
					modules.BufferGeometryUtils.mergeGeometries(geometries, false),
					materials.mtl(f.mtl.idx)
				);
			};
		}
		else if (objType == "Wall") {
			return (f, vertices) => {
				return new THREE.Mesh(
					createWallGeometry(vertices, () => f.geom.bh),
					materials.mtl(f.mtl.idx)
				);
			};
		}
	}

	buildLabels(features) {
		// Line layer doesn't support label
		// super.buildLabels(features);
	}

	// prepare for growing line animation
	prepareAnimation(sequential) {

		if (this.origMtls !== undefined) return;

		const computeLineDistances = (obj) => {
			if (!obj.material.isLineDashedMaterial) return;

			obj.computeLineDistances();

			const dists = obj.geometry.attributes.lineDistance.array;
			obj.lineLength = dists[dists.length - 1];

			for (let i = 0; i < dists.length; i++) {
				dists[i] /= obj.lineLength;
			}
		}

		this.origMtls = new Materials();
		this.origMtls.array = this.materials.array;

		this.materials.array = [];

		if (sequential) {
			for (const f of this.features) {
				const m = f.objs[0].material;
				let mtl;

				if (m.isMeshLineMaterial) {
					mtl = new modules.meshline.MeshLineMaterial();
					mtl.color = m.color;
					mtl.opacity = m.opacity;
					mtl.lineWidth = m.lineWidth;
					mtl.dashArray = 2;
					mtl.transparent = true;
				}
				else {
					if (m.isLineDashedMaterial) {
						mtl = m.clone();
					}
					else {
						mtl = new THREE.LineDashedMaterial({
							color: m.color,
							opacity: m.opacity
						});
					}
					mtl.gapSize = 1;
				}

				for (const obj of f.objs) {
					obj.material = mtl;
					computeLineDistances(obj);
				}

				this.materials.add(mtl);
			}
		}
		else {
			for (const origMtl of this.origMtls.array) {
				let mtl = origMtl.mtl;

				if (mtl.isLineDashedMaterial) {
					mtl.gapSize = 1;
				}
				else if (mtl.isMeshLineMaterial) {
					mtl.dashArray = 2;
					mtl.transparent = true;
				}
				else if (mtl.isLineBasicMaterial) {
					mtl = new THREE.LineDashedMaterial({
						color: mtl.color,
						opacity: mtl.opacity
					});
				}

				this.materials.add(mtl);
			}

			this.objectGroup.traverse((obj) => {
				if (obj.userData.mtl === undefined) return;

				obj.material = this.materials.mtl(obj.userData.mtl.idx);
				computeLineDistances(obj);
			});
		}
	}

	// length: number [0 - 1]
	setLineLength(length, featureIdx) {
		if (this.origMtls === undefined) return;

		const setLength = (m) => {
			if (m.isLineDashedMaterial) {
				m.dashSize = length;
			}
			else if (m.isMeshLineMaterial) {
				m.uniforms.dashOffset.value = -length;
			}
		};

		if (featureIdx === undefined) {
			for (const { mtl } of this.materials.array) {
				setLength(mtl);
			}
		}
		else {
			setLength(this.features[featureIdx].objs[0].material);
		}
	}

}


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
