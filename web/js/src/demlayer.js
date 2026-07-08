// (C) 2014 Minoru Akagi
// SPDX-License-Identifier: MIT

import { THREE } from "./three.js";

import { app, conf, deg2rad, LayerType, UV } from "./core.js";
import { MapLayer } from "./layer.js";
import { Material } from "./material.js";
import * as Utils from "./utils.js";

/*
 The GridGeometry class is almost the same as PlaneGeometry, but it does not
 generate triangles that include vertices with no-data values.

 It supports tile mode. When the grid has margin areas (right/bottom)
 with no actual data, pass `segments` explicitly so that UV coordinates
 are calculated based on the full tile extent rather than only the
 data-containing region.
*/
class GridGeometry extends THREE.BufferGeometry {

	constructor() {
		super();
		this.type = 'GridGeometry';
	}

	/**
	 * @param {object} grid
	 * @param {number} width      - Plane width (or tile size).
	 * @param {number} height     - Plane height (ignored when `segments` is given).
	 * @param {number} [segments] - When supplied, the grid is treated as a square tile.
	 */
	loadData(grid, width, height, segments) {
		const grid_values = grid.values;
		const columns = grid.width;		// number of columns of actual grid data
		const rows = grid.height;		// number of rows of actual grid data
		const nodata = (grid.nodata === undefined) ? undefined : new Float32Array(Utils.base64ToUint8Array(grid.nodata).buffer)[0];

		const isTileMode = (segments !== undefined);
		const segmentsX = (isTileMode) ? segments : columns - 1;
		const segmentsY = (isTileMode) ? segments : rows - 1;
		const segment_width = width / segmentsX;
		const segment_height = ((isTileMode) ? width : height) / segmentsY;
		const half_w = width / 2;
		const half_h = ((isTileMode) ? width : height) / 2;

		const indices = [];
		const vertices = [];
		const uvs = [];

		for (let iy = 0; iy < rows; iy++) {

			const y = iy * segment_height - half_h;
			const v = 1 - (iy / segmentsY);

			for (let ix = 0; ix < columns; ix++) {

				const x = ix * segment_width - half_w;
				const i = ix + iy * columns;
				const z = grid_values[i];

				vertices.push(x, -y, (z === nodata) ? 0 : z);
				uvs.push(ix / segmentsX, v);

				if (ix === 0 || iy === 0) continue;

				const a = i - columns - 1;
				const b = i - 1;
				const c = i;
				const d = i - columns;

				if (grid_values[b] === nodata || grid_values[d] === nodata) continue;
				if (grid_values[a] !== nodata) indices.push(a, b, d);
				if (z !== nodata) indices.push(b, c, d);
			}
		}

		this.setIndex(indices);
		this.setAttribute('position', new THREE.Float32BufferAttribute(vertices, 3));
		this.setAttribute('uv', new THREE.Float32BufferAttribute(uvs, 2));
		this.computeBoundingSphere();
		this.computeBoundingBox();
		this.computeVertexNormals();
	}
}


class DEMBlockBase {

	constructor() {
		this.obj = null;
		this.materials = [];
		this.currentMtlIndex = 0;
	}

	loadData(data, layer, callback) {
		this.data = data;

		// load material
		for (const m of data.materials || []) {
			const mtl = new Material();
			mtl.loadData(m, () => layer.requestRender());
			this.materials[m.mtlIndex] = mtl;

			if (m.useNow) {
				this.currentMtlIndex = m.mtlIndex;
				if (this.obj) {
					layer.materials.removeItem(this.obj.material, true);

					this.obj.material = mtl.mtl;
					layer.requestRender();
				}
				layer.materials.add(mtl);
			}
		}
	}

	/**
	 * @returns {{x0: number, y0: number, x1: number, y1: number, xres: number, yres: number}}
	 */
	_auxArgs() {
		return {x0: 0, y0: 0, x1: 0, y1: 0, xres: 0, yres: 0};
	}

	buildSides(layer, parent, material, z0) {
		const {values: gridValues, width: w, height: h} = this.data.grid;
		const {x0, y0, x1, y1} = this._auxArgs();

		const planeWidth = x1 - x0;
		const planeHeight = y0 - y1;
		const cx = (x0 + x1) / 2;
		const cy = (y0 + y1) / 2;

		const k = w * (h - 1);
		const bandWidth = -2 * z0;

		// front and back
		const geomFr = new THREE.PlaneGeometry(planeWidth, bandWidth, w - 1, 1);
		const geomBa = geomFr.clone();

		const verticesFr = geomFr.attributes.position.array;
		const verticesBa = geomBa.attributes.position.array;

		for (let i = 0; i < w; i++) {
			verticesFr[i * 3 + 1] = gridValues[k + i];
			verticesBa[i * 3 + 1] = gridValues[w - 1 - i];
		}

		const meshFr = new THREE.Mesh(geomFr, material);
		meshFr.rotation.x = Math.PI / 2;
		meshFr.position.x = cx;
		meshFr.position.y = y1;
		meshFr.name = "side";
		parent.add(meshFr);

		const meshBa = new THREE.Mesh(geomBa, material);
		meshBa.rotation.x = Math.PI / 2;
		meshBa.rotation.y = Math.PI;
		meshBa.position.x = cx;
		meshBa.position.y = y0;
		meshBa.name = "side";
		parent.add(meshBa);

		// left and right
		const geomLe = new THREE.PlaneGeometry(bandWidth, planeHeight, 1, h - 1);
		const geomRi = geomLe.clone();

		const verticesLe = geomLe.attributes.position.array;
		const verticesRi = geomRi.attributes.position.array;

		for (let i = 0; i < h; i++) {
			verticesLe[(i * 2 + 1) * 3] = gridValues[w * i];
			verticesRi[i * 2 * 3] = -gridValues[w * (i + 1) - 1];
		}

		const meshLe = new THREE.Mesh(geomLe, material);
		meshLe.rotation.y = -Math.PI / 2;
		meshLe.position.x = x0;
		meshLe.position.y = cy;
		meshLe.name = "side";
		parent.add(meshLe);

		const meshRi = new THREE.Mesh(geomRi, material);
		meshRi.rotation.y = Math.PI / 2;
		meshRi.position.x = x1;
		meshRi.position.y = cy;
		meshRi.name = "side";
		parent.add(meshRi);

		// bottom
		const geom = new THREE.PlaneGeometry(planeWidth, planeHeight);
		const mesh = new THREE.Mesh(geom, material);
		mesh.rotation.x = Math.PI;
		mesh.position.set(cx, cy, z0);
		mesh.name = "bottom";
		parent.add(mesh);

		parent.updateMatrixWorld();
	}

	addEdges(layer, parent, material, z0) {
		const {values: gridValues, width: w, height: h} = this.data.grid;
		const {x0, y0, x1, y1, xres, yres} = this._auxArgs();

		const k = w * (h - 1);

		// terrain edges
		const vlFr = [];
		const vlBk = [];
		const vlLe = [];
		const vlRi = [];

		for (let i = 0; i < w; i++) {
			const x = x0 + xres * i;
			vlFr.push(x, y1, gridValues[k + i]);
			vlBk.push(x, y0, gridValues[i]);
		}

		for (let i = 0; i < h; i++) {
			const y = y0 - yres * i;
			vlLe.push(x0, y, gridValues[w * i]);
			vlRi.push(x1, y, gridValues[w * (i + 1) - 1]);
		}

		const verticesList = [vlFr, vlBk, vlLe, vlRi];

		if (z0 !== undefined) {
			// horizontal rectangle at bottom
			verticesList.push([
				x0, y0, z0,
				x1, y0, z0,
				x1, y1, z0,
				x0, y1, z0,
				x0, y0, z0
			]);

			// vertical lines at corners
			[
				[x0, y1, gridValues.at(-w)],
				[x1, y1, gridValues.at(-1)],
				[x1, y0, gridValues[w - 1]],
				[x0, y0, gridValues[0]]
			].forEach(([x, y, z]) => {
				verticesList.push([x, y, z, x, y, z0]);
			});
		}

		for (const vertices of verticesList) {
			const geom = new THREE.BufferGeometry().setAttribute("position", new THREE.Float32BufferAttribute(vertices, 3));

			const line = new THREE.Line(geom, material);
			line.name = "frame";
			parent.add(line);
		}

		parent.updateMatrixWorld();
	}

	// add quad wireframe
	addWireframe(layer, parent, material) {
		const {values: gridValues, width: w, height: h} = this.data.grid;
		const {x0, y0, xres, yres} = this._auxArgs();

		const group = new THREE.Group();

		for (let x = w - 1; x >= 0; x--) {
			const vertices = [];
			const vx = x0 + xres * x;

			for (let y = h - 1; y >= 0; y--) {
				vertices.push(vx, y0 - yres * y, gridValues[x + w * y]);
			}

			const geom = new THREE.BufferGeometry().setAttribute("position", new THREE.Float32BufferAttribute(vertices, 3));

			group.add(new THREE.Line(geom, material));
		}

		for (let y = h - 1; y >= 0; y--) {
			const vertices = [];
			const vy = y0 - yres * y;

			for (let x = w - 1; x >= 0; x--) {
				vertices.push(x0 + xres * x, vy, gridValues[x + w * y]);
			}

			const geom = new THREE.BufferGeometry().setAttribute("position", new THREE.Float32BufferAttribute(vertices, 3));

			group.add(new THREE.Line(geom, material));
		}

		parent.add(group);
		parent.updateMatrixWorld();
	}
}


class DEMBlock extends DEMBlockBase {

	loadData(data, layer, callback) {
		super.loadData(data, layer, callback);

		if (data.grid === undefined) return;

		const geom = new GridGeometry();
		const mesh = new THREE.Mesh(geom, (this.materials[this.currentMtlIndex] || {}).mtl);
		mesh.position.fromArray(data.translate);
		mesh.scale.z = data.zScale;
		layer.addObject(mesh);

		const buildGeometry = (grid) => {
			geom.loadData(grid, data.width, data.height);
			if (callback) callback(mesh);
		};

		const grid = data.grid;
		if (grid.url !== undefined) {
			app.loadFile(grid.url, "arraybuffer", (buf) => {
				grid.values = new Float32Array(buf);
				buildGeometry(grid);
			});
		}
		else {
			if (grid.base64 !== undefined) {
				const bytes = Utils.base64ToUint8Array(grid.base64);
				grid.values = new Float32Array(bytes.buffer);
				delete grid.base64;
			}
			buildGeometry(grid);
		}

		this.obj = mesh;
		return mesh;
	}

	_auxArgs() {
		const pw = this.data.width,
			  ph = this.data.height;
		return {
			x0: -pw / 2,
			y0: ph / 2,
			x1: pw / 2,
			y1: -ph / 2,
			xres: pw / (this.data.grid.width - 1),
			yres: ph / (this.data.grid.height - 1)
		}
	}
}


class DEMTileBlock extends DEMBlockBase {

	loadData(data, layer, callback) {
		const grid = data.grid;

		super.loadData(data, layer, callback);

		if (grid === undefined) return;

		const geom = new GridGeometry();
		const mesh = new THREE.Mesh(geom, (this.materials[this.currentMtlIndex] || {}).mtl);
		mesh.position.fromArray(data.translate);
		mesh.scale.z = data.zScale;
		layer.addObject(mesh);

		const buildGeometry = (grid) => {
			geom.loadData(grid, data.tileSize, data.tileSize, data.segments);
			if (callback) callback(mesh);
		};

		if (grid.url !== undefined) {
			app.loadFile(grid.url, "arraybuffer", (buf) => {
				grid.values = new Float32Array(buf);
				buildGeometry(grid);
			});
		}
		else {
			if (grid.base64 !== undefined) {
				const bytes = Utils.base64ToUint8Array(grid.base64);
				grid.values = new Float32Array(bytes.buffer);
				delete grid.base64;
			}
			buildGeometry(grid);
		}

		this.obj = mesh;
		return mesh;
	}

	_auxArgs() {
		const res = this.data.tileSize / this.data.segments;
		const pw = (this.data.grid.width - 1) * res;
		const ph = (this.data.grid.height - 1) * res;
		return {
			x0: -this.data.tileSize / 2,
		    y0: this.data.tileSize / 2,
			x1: pw - this.data.tileSize / 2,
			y1: this.data.tileSize / 2 - ph,
			xres: res,
			yres: res
		};
	}
}


class ClippedDEMBlock extends DEMBlockBase {

	loadData(data, layer, callback) {
		super.loadData(data, layer, callback);

		if (data.geom === undefined) return;

		const geom = new THREE.BufferGeometry();
		const mesh = new THREE.Mesh(geom, (this.materials[this.currentMtlIndex] || {}).mtl);
		mesh.position.fromArray(data.translate);
		mesh.scale.z = data.zScale;
		layer.addObject(mesh);

		const buildGeometry = (obj) => {

			const v = obj.triangles.v;
			const normals = [];
			const uvs = [];

			let origin = layer.sceneData.origin,
				be = layer.sceneData.baseExtent,
				base_width = be.width,
				base_height = be.height,
				x0 = be.cx - origin.x - base_width * 0.5,
				y0 = be.cy - origin.y - base_height * 0.5;

			for (let i = 0, l = v.length; i < l; i += 3) {
				normals.push(0, 0, 1);
				uvs.push((v[i] - x0) / base_width, (v[i + 1] - y0) / base_height);
			}

			geom.setIndex(obj.triangles.f);
			geom.setAttribute("position", new THREE.Float32BufferAttribute(v, 3));
			geom.setAttribute("normal", new THREE.Float32BufferAttribute(normals, 3));
			geom.setAttribute("uv", new THREE.Float32BufferAttribute(uvs, 2));
			geom.computeVertexNormals();

			geom.attributes.position.needsUpdate = true;
			geom.attributes.normal.needsUpdate = true;
			geom.attributes.uv.needsUpdate = true;

			this.data.polygons = obj.polygons;
			if (callback) callback(mesh);
		};

		if (data.geom.url !== undefined) {
			app.loadFile(data.geom.url, "json", obj => buildGeometry(obj));
		}
		else {    // preview
			buildGeometry(data.geom);
		}

		this.obj = mesh;
		return mesh;
	}

	buildSides(layer, parent, material, z0) {
		const bzFunc = (_x, _y) => z0;

		// make back-side material for bottom
		const mat_back = material.clone();
		mat_back.side = THREE.BackSide;
		layer.materials.add(mat_back);

		let geom, mesh, shape;
		for (const bnds of this.data.polygons) {
			// sides
			for (const bnd of bnds) {
				geom = Utils.createWallGeometry(bnd, bzFunc);
				mesh = new THREE.Mesh(geom, material);
				mesh.name = "side";
				parent.add(mesh);
			}
			// bottom
			shape = new THREE.Shape(Utils.flatArrayToVec2Array(bnds[0], 3));
			for (let j = 1, m = bnds.length; j < m; j++) {
				shape.holes.push(new THREE.Path(Utils.flatArrayToVec2Array(bnds[j], 3)));
			}
			geom = new THREE.ShapeGeometry(shape);
			mesh = new THREE.Mesh(geom, mat_back);
			mesh.position.z = z0;
			mesh.name = "bottom";
			parent.add(mesh);
		}
		parent.updateMatrixWorld();
	}

	addEdges() {}
	addWireframe() {}
}


export class DEMLayer extends MapLayer {

	constructor() {
		super();
		this.type = LayerType.DEM;
		this.blocks = [];
		this.auxiliaryMtl = {};
	}

	loadData(data, scene) {
		if (data.type == "layer") {
			this.clearObjects();
			super.loadData(data, scene);

			this.blocks = [];

			var p = scene.userData,
				rotation = p.baseExtent.rotation;

			if (data.properties.clipped) {
				this.objectGroup.position.set(0, 0, 0);
				this.objectGroup.rotation.z = 0;

				if (rotation) {
					// rotate around center of base extent
					this.objectGroup.position.copy(p.pivot).negate();
					this.objectGroup.position.applyAxisAngle(UV.k, rotation * deg2rad);
					this.objectGroup.position.add(p.pivot);
					this.objectGroup.rotateOnAxis(UV.k, rotation * deg2rad);
				}
			}
			else {
				this.objectGroup.position.copy(p.pivot);
				this.objectGroup.position.z *= p.zScale;
				this.objectGroup.rotation.z = rotation * deg2rad;
			}
			this.objectGroup.updateMatrixWorld();

			this._loadAuxiliaryMaterials(data.properties);

			if (data.body !== undefined && data.body.blocks !== undefined) {
				data.body.blocks.forEach((block) => {
					this.buildBlock(block, scene, this);
				});
			}
		}
		else if (data.type == "block") {
			this.buildBlock(data, scene, this);
		}
	}

	_loadAuxiliaryMaterials(p) {
		["sides", "edges", "wireframe"].forEach((a) => {
			if (!p[a]) return;

			const m = new Material();
			m.loadData(p[a].mtl);
			this.materials.add(m);
			this.auxiliaryMtl[a] = m;
		});
	}

	buildBlock(data, scene, layer) {

		let block = this.blocks[data.block];
		if (block === undefined) {
			if (layer.properties.tiled) {
				block = new DEMTileBlock();
			}
			else if (layer.properties.clipped) {
				block = new ClippedDEMBlock();
			}
			else {
				block = new DEMBlock();
			}
			this.blocks[data.block] = block;
		}

		block.loadData(data, this, (mesh) => {
			// add auxiliary objects
			if (layer.properties.sides) {	// sides and bottom
				block.buildSides(this, mesh, layer.auxiliaryMtl.sides.mtl, layer.properties.sides.bottom);
				this.sideVisible = true;
			}

			if (layer.properties.edges) {
				block.addEdges(this, mesh, layer.auxiliaryMtl.edges.mtl, (layer.properties.sides) ? layer.properties.sides.bottom : undefined);
			}

			if (layer.properties.wireframe) {
				block.addWireframe(this, mesh, layer.auxiliaryMtl.wireframe.mtl);

				mesh.material.polygonOffset = true;
				mesh.material.polygonOffsetFactor = 1;
				mesh.material.polygonOffsetUnits = 1;
			}

			delete data.grid;	// no longer needed

			this.requestRender();
		});
	}

	get opacity() {
		const b = this.blocks[0];
		if (b && b.materials[this.currentMtlIndex]) {
			const m = b.materials[this.currentMtlIndex];
			return (m.mtl) ? m.mtl.opacity : 1;
		}
		return this.materials.opacity();
	}

	set opacity(value) {
		for (const b of this.blocks) {
			const m = b.materials[this.currentMtlIndex];
			if (m && m.mtl) {
				m.mtl.opacity = value;
				m.mtl.transparent = (value < 1);
			}
		}
		this.requestRender();
	}

	get currentMtlIndex() {
		const b = this.blocks[0];
		return (b) ? b.currentMtlIndex : undefined;
	}

	set currentMtlIndex(mtlIndex) {
		this.materials.removeItemsByGroupId(this.currentMtlIndex);

		for (const b of this.blocks) {
			const m = b.materials[mtlIndex];
			if (m) {
				b.currentMtlIndex = mtlIndex;
				b.obj.material = m.mtl;
				this.materials.add(m);
			}
		}
		this.requestRender();
	}

	setSideVisible(visible) {
		this.sideVisible = visible;
		this.objectGroup.traverse((obj) => {
			if (obj.name == "side" || obj.name == "bottom") obj.visible = visible;
		});
	}

	// texture animation
	prepareTexAnimation(from, to) {
		this.anim = [];
		for (const block of this.blocks) {
			const imgFrom = block.materials[from].mtl.map.image;
			const imgTo = block.materials[to].mtl.map.image;

			const canvas = document.createElement("canvas");
			canvas.width = (imgFrom.width > imgTo.width) ? imgFrom.width : imgTo.width;
			canvas.height = (imgFrom.width > imgTo.width) ? imgFrom.height : imgTo.height;

			const ctx = canvas.getContext("2d");

			const tex = new THREE.CanvasTexture(canvas);
			tex.anisotropy = conf.texture.anisotropy;
			tex.colorSpace = THREE.SRGBColorSpace;

			const opt = {
				map: tex,
				side: THREE.DoubleSide,
				transparent: true
			};

			let mtl;
			const m = block.obj.material;
			if (m) {
				if (m.isMeshToonMaterial) {
					mtl = new THREE.MeshToonMaterial(opt);
				}
				else if (m.isMeshPhongMaterial) {
					mtl = new THREE.MeshPhongMaterial(opt);
				}
			}
			if (mtl === undefined) {
				mtl = new THREE.MeshLambertMaterial(opt);
			}

			block.obj.material = mtl;
			this.materials.add(mtl);

			this.anim.push({
				img_from: imgFrom,
				img_to: imgTo,
				ctx: ctx,
				tex: mtl.map
			});
		}
	}

	setTextureAt(progress, effect) {

		if (this.anim === undefined) return;

		var w, h, w0, h0, w1, h1, ew, ew1;
		for (const a of this.anim) {
			w = a.ctx.canvas.width;
			h = a.ctx.canvas.height;
			w0 = a.img_from.width;
			h0 = a.img_from.height;
			w1 = a.img_to.width;
			h1 = a.img_to.height;

			if (effect == 0) {  // fade in
				a.ctx.globalAlpha = 1;
				a.ctx.drawImage(a.img_from, 0, 0, w0, h0,
											0, 0, w, h);
				a.ctx.globalAlpha = progress;
				a.ctx.drawImage(a.img_to, 0, 0, w1, h1,
										  0, 0, w, h);
			}
			else if (effect == 2) {  // slide to left (not used)
				if (progress === null) {
					a.ctx.drawImage(a.img_from, 0, 0, w0, h0,
												0, 0, w, h);
				}
				else {
					ew1 = w1 * progress;
					ew = w * progress;
					a.ctx.drawImage(a.img_to, w1 - ew1, 0, ew1, h1,
											  w - ew, 0, ew, h);
				}
			}
			a.tex.needsUpdate = true;
		}
	}
}
