// (C) 2014 Minoru Akagi
// SPDX-License-Identifier: MIT

import { THREE } from "../three.js";

import { app, conf, deg2rad, LayerType, UV } from "../core.js";
import { MapLayer } from "./layer.js";
import { Material } from "../material.js";
import * as Utils from "../utils.js";

import type { DEMBlockData, DEMBlockGridData, DEMBlockMeshData, DEMLayerData, DEMLayerProperties, DEMMeshData, MapExtent, TIN_Border, Vec3 } from "../types.js";
import type { Scene } from "../scene.js";

/*
 The GridGeometry class is almost the same as PlaneGeometry, but it does not
 generate triangles that include vertices with no-data values.

 It supports tile mode. When the grid has margin areas (right/bottom)
 with no actual data, pass `segments` explicitly so that UV coordinates
 are calculated based on the full tile extent rather than only the
 data-containing region.
*/
class GridGeometry extends THREE.BufferGeometry {

	type = "GridGeometry";

	/**
	 * @param values    - DEM values
	 * @param columns   - Number of columns of actual grid data
	 * @param rows      - Number of rows of actual grid data
	 * @param extent    - Extent of the plane
	 * @param nodata    - No data value
	 * @param segments	- Segments of a tile side. When supplied, the grid is treated as a square tile.
	 */
	loadData(dem_values: Float32Array, columns: number, rows: number, extent: MapExtent, nodata?: number, segments?: number) {
		const { width, height }  = extent;
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
				const z = dem_values[i];

				vertices.push(x, -y, (z === nodata) ? 0 : z);
				uvs.push(ix / segmentsX, v);

				if (ix === 0 || iy === 0) continue;

				const a = i - columns - 1;
				const b = i - 1;
				const c = i;
				const d = i - columns;

				if (dem_values[b] === nodata || dem_values[d] === nodata) continue;
				if (dem_values[a] !== nodata) indices.push(a, b, d);
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

	materials: Material[] = [];
	currentMtlIndex: number = 0;

	obj!: THREE.Mesh;
	data!: DEMBlockData;

	loadData(data: DEMBlockData, layer: DEMLayer, callback?: (mesh: THREE.Mesh) => void) {
		this.data = data;

		if ("materials" in data === false) return;

		// load material
		for (const m of data.materials) {
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

	_auxArgs(): { x0: number, y0: number, x1: number, y1: number, xres: number, yres: number } {
		return { x0: 0, y0: 0, x1: 0, y1: 0, xres: 0, yres: 0 };
	}

	buildSides(layer: DEMLayer, parent: THREE.Mesh, material: THREE.Material, z0: number) {
		const { values: gridValues, width: w, height: h } = this.data.grid;
		const { x0, y0, x1, y1 } = this._auxArgs();

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

	addEdges(layer: DEMLayer, parent: THREE.Mesh, material: THREE.Material, z0: number) {
		const { values: gridValues, width: w, height: h } = this.data.grid;
		const { x0, y0, x1, y1, xres, yres } = this._auxArgs();

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
	addWireframe(layer: DEMLayer, parent: THREE.Mesh, material: THREE.Material) {
		const { values: gridValues, width: w, height: h } = this.data.grid;
		const { x0, y0, xres, yres } = this._auxArgs();

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


class DEMGridBlock extends DEMBlockBase {

	declare data: DEMBlockGridData;

	loadData(data: DEMBlockGridData, layer: DEMLayer, callback: (mesh: THREE.Mesh) => void): THREE.Mesh | void {
		super.loadData(data, layer, callback);

		if (data.grid === undefined) return;

		const geom = new GridGeometry();
		const material = (this.materials[this.currentMtlIndex] || {}).mtl;
		const mesh = new THREE.Mesh(geom, material);
		mesh.position.fromArray(data.translate);
		mesh.scale.z = data.zScale;
		layer.addObject(mesh);

		const buildGeometry = (values, grid) => {
			const nodata = (grid.nodata === undefined) ? undefined : new Float32Array(Utils.base64ToUint8Array(grid.nodata).buffer)[0];
			geom.loadData(values, grid.columns, grid.rows, data.extent, nodata, data.segments);
			if (callback) callback(mesh);
		};

		const grid = data.grid;
		if ("url" in grid) {
			app.loadFile(grid.url, "arraybuffer", (buf) => {
				buildGeometry(new Float32Array(buf), grid);
			});
		}
		else {
			const bytes = Utils.base64ToUint8Array(grid.base64);
			delete grid.base64;
			buildGeometry(new Float32Array(bytes.buffer), grid);
		}

		this.obj = mesh;
		return mesh;
	}

	_auxArgs() {
		const pw = this.data.width;
		const ph = this.data.height;
		return {
			x0: -pw / 2,
			y0: ph / 2,
			x1: pw / 2,
			y1: -ph / 2,
			xres: pw / (this.data.grid.columns - 1),
			yres: ph / (this.data.grid.rows - 1)
		}
	}
}

class DEMMeshBlock extends DEMBlockBase {

	declare data: DEMBlockMeshData;

	loadData(data: DEMBlockMeshData, layer: DEMLayer, callback: (mesh: THREE.Mesh) => void): THREE.Mesh | void {
		super.loadData(data, layer, callback);

		const mesh_data = data.mesh;
		if (mesh_data === undefined) return;

		const geom = new THREE.BufferGeometry();
		const material = (this.materials[this.currentMtlIndex] || {}).mtl;

		const mesh = new THREE.Mesh(geom, material);
		mesh.position.fromArray(data.translate);
		mesh.scale.z = data.zScale;
		layer.addObject(mesh);

		this.obj = mesh;

		const build = (data) => {
			this.setGeometryData(geom, data);
			this.buildAuxiliaryObjects(layer, geom, mesh);
		};

		if ("url" in mesh_data) {
			app.loadBinaryContainer(mesh_data.url).then((data) => build(data));
		}
		else {    // preview
			build(mesh_data);
		}

		return mesh;
	}

	setGeometryData(geom: THREE.BufferGeometry, data: DEMMeshData) {
		const vert: ArrayBuffer = (typeof data.vertices === "string") ? Utils.base64ToUint8Array(data.vertices).buffer : data.vertices;
		const ind: ArrayBuffer = (typeof data.indices === "string") ? Utils.base64ToUint8Array(data.indices).buffer : data.indices;
		const _uv: ArrayBuffer = (typeof data.uvs === "string") ? Utils.base64ToUint8Array(data.uvs).buffer : data.uvs;

		geom.setAttribute("position", new THREE.Float32BufferAttribute(vert, 3));
		geom.setAttribute("uv", new THREE.Float32BufferAttribute(_uv, 2));
		geom.setIndex(new THREE.Uint32BufferAttribute(ind, 1));

		geom.computeBoundingSphere();
		geom.computeBoundingBox();
		geom.computeVertexNormals();
	}

	buildAuxiliaryObjects(layer, geom, parent) {
		if (layer.properties.sides) {
			const boundaries = this.getBoundaries(geom);

			parent.add(...this.buildSides(boundaries, layer.properties.sides.bottom, layer.auxiliaryMtl.sides.mtl));
			parent.add(this.buildBottom(geom, layer.properties.sides.bottom, layer.auxiliaryMtl.sides.mtl));

			layer.sideVisible = true;
		}
/*
		// TODO: addEdges
		if (this.properties.edges) {
			block.addEdges(this, mesh, this.auxiliaryMtl.edges.mtl, (this.properties.sides) ? this.properties.sides.bottom : undefined);
		}

		// TODO: addWireframe
		if (this.properties.wireframe) {
			block.addWireframe(this, mesh, this.auxiliaryMtl.wireframe.mtl);

			mesh.material.polygonOffset = true;
			mesh.material.polygonOffsetFactor = 1;
			mesh.material.polygonOffsetUnits = 1;
		}
*/
	}

	getBoundaries(geometry: THREE.BufferGeometry): Vec3[][] {
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
	}

	buildSides(boundaries: Vec3[][], z0: number, material: THREE.Material): THREE.Mesh[] {
		const sides = [];
		for (const boundary of boundaries) {
			// TODO: counter clockwise order and front side material
			const side_geom = Utils.createWallGeometry(boundary.flat(), () => z0);

			const side = new THREE.Mesh(side_geom, material);
			sides.push(side);
		}
		return sides;
	}

	buildBottom(surfaceGeom: THREE.BufferGeometry, z0: number, material: THREE.Material): THREE.Mesh {
		// TODO: back side material
		const bottom = new THREE.Mesh(surfaceGeom, material);
		bottom.position.z = z0;
		bottom.scale.z = 0;
		return bottom;
	}
}

class ClippedDEMBlock extends DEMBlockBase {

	loadData(data: DEMBlockGridData, layer: DEMLayer, callback: (mesh: THREE.Mesh) => void): THREE.Mesh | void {
		super.loadData(data, layer, callback);

		if (data.geom === undefined) return;

		const geom = new THREE.BufferGeometry();
		const mesh = new THREE.Mesh(geom, (this.materials[this.currentMtlIndex] || {}).mtl);
		mesh.position.fromArray(data.translate);
		mesh.scale.z = data.zScale;
		layer.addObject(mesh);

		const buildGeometry = (obj: TIN_Border) => {

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

	buildSides(layer: DEMLayer, parent: THREE.Mesh, material: THREE.Material, z0: number) {
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

	addEdges() { }
	addWireframe() { }
}


export class DEMLayer extends MapLayer {

	type = LayerType.DEM;
	blocks: DEMBlockBase[] = [];
	sideVisible: boolean = false;
	auxiliaryMtl: Partial<Record<"sides" | "edges" | "wireframe", Material>> = {};

	anim?: any[];

	declare properties: DEMLayerProperties;

	loadLayerData(data: DEMLayerData, scene: Scene): void {
		this.clearObjects();
		super.loadLayerData(data, scene);

		this.blocks = [];

		var p = scene.userData,
			rotation = p.baseExtent.rotation;

		if (data.properties.clipped) {
			this.objectGroup.position.set(0, 0, 0);
			this.objectGroup.rotation.z = 0;

			if (rotation) {
				// TODO:

				// rotate around center of base extent
				this.objectGroup.position.copy(p.pivot).negate();
				this.objectGroup.position.applyAxisAngle(UV.k, rotation * deg2rad);
				this.objectGroup.position.add(p.pivot);
				this.objectGroup.rotateOnAxis(UV.k, rotation * deg2rad);
			}
		}
		else {
			this.objectGroup.position.set(0, 0, 0);
			this.objectGroup.rotation.z = 0;
		}
		this.objectGroup.updateMatrixWorld();

		this._loadAuxiliaryMaterials(data.properties);

		if (data.body && data.body.blocks) {
			data.body.blocks.forEach((block) => this.loadBlockData(block, scene));
		}
	}

	_loadAuxiliaryMaterials(p: DEMLayerProperties) {
		["sides", "edges", "wireframe"].forEach((a) => {
			if (!p[a]) return;

			const m = new Material();
			m.loadData(p[a].mtl);
			this.materials.add(m);
			this.auxiliaryMtl[a] = m;
		});
	}

	loadBlockData(data: DEMBlockData, scene: Scene): void {
		super.loadBlockData(data, scene);

		let block = this.blocks[data.block];
		if (block === undefined) {
			block = this.blocks[data.block] = createBlock(this);
		}

		block.loadData(data, this, (mesh) => {
			// add auxiliary objects
			if (this.properties.sides) {	// sides and bottom
				block.buildSides(this, mesh, this.auxiliaryMtl.sides.mtl, this.properties.sides.bottom);
				this.sideVisible = true;
			}

			if (this.properties.edges) {
				block.addEdges(this, mesh, this.auxiliaryMtl.edges.mtl, (this.properties.sides) ? this.properties.sides.bottom : undefined);
			}

			if (this.properties.wireframe) {
				block.addWireframe(this, mesh, this.auxiliaryMtl.wireframe.mtl);

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

	set opacity(value: number) {
		for (const b of this.blocks) {
			const m = b.materials[this.currentMtlIndex];
			if (m && m.mtl) {
				m.mtl.opacity = value;
				m.mtl.transparent = (value < 1);
			}
		}
		this.requestRender();
	}

	get currentMtlIndex(): number | undefined {
		const b = this.blocks[0];
		return (b) ? b.currentMtlIndex : undefined;
	}

	set currentMtlIndex(mtlIndex: number) {
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

	setSideVisible(visible: boolean) {
		this.sideVisible = visible;
		this.objectGroup.traverse((obj) => {
			if (obj.name == "side" || obj.name == "bottom") obj.visible = visible;
		});
	}

	// texture animation
	prepareTexAnimation(from: number, to: number) {
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

	setTextureAt(progress: number | null, effect: number) {

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
				a.ctx.drawImage(a.img_from,
					0, 0, w0, h0,
					0, 0, w, h);
				a.ctx.globalAlpha = progress;
				a.ctx.drawImage(a.img_to,
					0, 0, w1, h1,
					0, 0, w, h);
			}
			else if (effect == 2) {  // slide to left (not used)
				if (progress === null) {
					a.ctx.drawImage(a.img_from,
						0, 0, w0, h0,
						0, 0, w, h);
				}
				else {
					ew1 = w1 * progress;
					ew = w * progress;
					a.ctx.drawImage(a.img_to,
						w1 - ew1, 0, ew1, h1,
						w - ew, 0, ew, h);
				}
			}
			a.tex.needsUpdate = true;
		}
	}
}


type BlockConstructor = new () => DEMBlockBase;

function createBlock(layer: DEMLayer) {
	const { clipped } = layer.properties;

	let BlockClass: BlockConstructor = DEMGridBlock;
	if (clipped) {
		BlockClass = ClippedDEMBlock;
		// BlockClass = DEMMeshBlock;
	}

	return new BlockClass();
}
