// (C) 2014 Minoru Akagi
// SPDX-License-Identifier: MIT

import { THREE } from "../three.js";

import { app, conf, LayerType } from "../core.js";
import { MapLayer } from "./layer.js";
import { Material } from "../material.js";
import { createWallGeometry, decodeBase64TypedArrayObject, getBoundaryLines } from "../utils.js";
import { Q3DPlugin } from "../tiles/q3dplugin.js";

import type { DEMBlockData, DEMBlockGridData, DEMBlockMeshData, DEMLayerData, DEMLayerProperties, MapExtent, ParsedDEMGridData, ParsedDEMMeshData, Point3, Vec3 } from "../types.js";
import type { Scene } from "../scene.js";


export class DEMLayer extends MapLayer {

	type = LayerType.DEM;
	blocks: DEMBlockBase[] = [];
	sideVisible: boolean = false;
	auxiliaryMtl: Partial<Record<"sides", Material>> = {};
	tilesRenderer = null;

	anim?: any[];

	declare properties: DEMLayerProperties;

	loadLayerData(data: DEMLayerData, scene: Scene): void {
		this.clearObjects();
		super.loadLayerData(data, scene);

		this.blocks = [];

		if (data.properties) {
			this._loadAuxiliaryMaterials(data.properties);
		}

		if (data.body && data.body.blocks) {
			data.body.blocks.forEach((block) => this.loadBlockData(block, scene));
		}

		// tiles renderer
		if (data.tileset) {
			import("lib/3d-tiles-renderer/3d-tiles-renderer.js").then(mod => {
				const plugin = new Q3DPlugin();
				plugin.layer = this;
				plugin.tileset = data.tileset;

				if (conf.debugMode) {
					plugin.showBoundingBox = true;
					plugin.showBoundingVolume = true;
				}

				this.tilesRenderer = new mod.TilesRenderer();
				this.tilesRenderer.registerPlugin(plugin);
				this.tilesRenderer.setCamera(app.camera);
				this.tilesRenderer.setResolutionFromRenderer(app.camera, app.renderer);

				this.addObject(this.tilesRenderer.group);
				scene.addTilesRenderer(this.tilesRenderer);

				this.requestRender();
			});
		}
		else if (this.tilesRenderer) {
			scene.removeTilesRenderer(this.tilesRenderer);
			this.tilesRenderer = null;
		}
	}

	_loadAuxiliaryMaterials(p: DEMLayerProperties) {
		["sides"].forEach((a) => {
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

		block.loadData(data, this);
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

	visibleObjects() {
		const objs = [];
		if (!this.visible) return objs;

		this.objectGroup.traverse((obj) => {
			if (obj instanceof THREE.Mesh && obj.name != "side" && obj.name != "bottom") objs.push(obj);
		});
		return objs;
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
				if (m instanceof THREE.MeshToonMaterial) {
					mtl = new THREE.MeshToonMaterial(opt);
				}
				else if (m instanceof THREE.MeshPhongMaterial) {
					mtl = new THREE.MeshPhongMaterial(opt);
				}
				else if (m instanceof THREE.MeshStandardMaterial) {
					opt.metalness = m.metalness;
					opt.roughness = m.roughness;
					mtl = new THREE.MeshStandardMaterial(opt);
				}
				else if (m instanceof THREE.MeshBasicMaterial) {
					mtl = new THREE.MeshBasicMaterial(opt);
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


class DEMBlockBase {

	materials: Material[] = [];
	currentMtlIndex: number = 0;

	obj!: THREE.Mesh<THREE.BufferGeometry, THREE.Material>;
	data!: DEMBlockData;

	loadData(data: DEMBlockData, layer: DEMLayer) {
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

	buildAuxiliaryObjects(layer, geom, parent) {
		if (layer.properties.sides) {
			const boundaries = getBoundaryLines(geom);

			parent.add(...this.buildSides(boundaries, layer.properties.sides.bottom, layer.auxiliaryMtl.sides.mtl));
			parent.add(this.buildBottom(geom, layer.properties.sides.bottom, layer.auxiliaryMtl.sides.mtl));

			layer.sideVisible = true;
		}
	}

	buildSides(boundaries: Vec3[][], z0: number, material: THREE.Material): THREE.Mesh[] {
		const sides = [];
		for (const boundary of boundaries) {
			// TODO: counter clockwise order and front side material
			const side_geom = createWallGeometry(boundary.flat(), () => z0);

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


class DEMGridBlock extends DEMBlockBase {

	declare data: DEMBlockGridData;

	loadData(data: DEMBlockGridData, layer: DEMLayer): THREE.Mesh | void {
		super.loadData(data, layer);

		if (data.grid === undefined) return;

		const geom = new GridGeometry();
		const material = (this.materials[this.currentMtlIndex] || {}).mtl;
		const mesh = new THREE.Mesh(geom, material);
		mesh.scale.z = data.zScale;
		mesh.position.fromArray(data.translate);
		layer.addObject(mesh);

		const build = (grid_data: ParsedDEMGridData) => {
			geom.loadData(grid_data.dem_values, grid_data.columns, grid_data.rows, data.extent, grid_data.nodata, data.segments);
			mesh.material.needsUpdate = true;		// update shader after computing vertex normals

			this.buildAuxiliaryObjects(layer, geom, mesh);

			layer.requestRender();
		};

		const grid = data.grid;
		if ("url" in grid) {
			app.loadJSONBinaryFile(grid.url).then(build);
		}
		else {
			decodeBase64TypedArrayObject(grid).then(build);
		}

		this.obj = mesh;
		return mesh;
	}
}

class DEMMeshBlock extends DEMBlockBase {

	declare data: DEMBlockMeshData;

	loadData(data: DEMBlockMeshData, layer: DEMLayer): THREE.Mesh | void {
		super.loadData(data, layer);

		const mesh_data = data.mesh;
		if (mesh_data === undefined) return;

		const geom = new THREE.BufferGeometry();
		const material = (this.materials[this.currentMtlIndex] || {}).mtl;

		const mesh = new THREE.Mesh(geom, material);
		mesh.position.fromArray(data.translate);
		mesh.scale.z = data.zScale;
		layer.addObject(mesh);

		this.obj = mesh;

		const build = (mesh_data: ParsedDEMMeshData) => {
			this.setGeometryData(geom, mesh_data);
			if (!geom.getAttribute("uv")) {
				this.calculateUVs(geom, data.extent, layer.sceneData.origin);
			}
			this.buildAuxiliaryObjects(layer, geom, mesh);

			layer.requestRender();
		};

		if ("url" in mesh_data) {
			app.loadJSONBinaryFile(mesh_data.url).then(build);
		}
		else {    // preview
			decodeBase64TypedArrayObject(mesh_data).then(build);
		}

		return mesh;
	}

	setGeometryData(geom: THREE.BufferGeometry, data: ParsedDEMMeshData) {
		geom.setAttribute("position", new THREE.Float32BufferAttribute(data.vertices, 3));

		geom.setIndex(new THREE.Uint32BufferAttribute(data.indices, 1));

		if (data.uvs) {
			geom.setAttribute("uv", new THREE.Float32BufferAttribute(data.uvs, 2));
		}

		geom.computeBoundingSphere();
		geom.computeBoundingBox();
		geom.computeVertexNormals();

		// update shader after computing vertex normals
		if (this.obj && this.obj.material) {
			this.obj.material.needsUpdate = true;
		}
	}

	calculateUVs(geom: THREE.BufferGeometry, extent: MapExtent, localOrigin: Point3) {
		const vert = geom.getAttribute("position").array;

		const {width, height} = extent;
		const x0 = extent.cx - localOrigin.x - width * 0.5;
		const y0 = extent.cy - localOrigin.y - height * 0.5;

		const uvs = [];
		for (let i = 0; i < vert.length; i += 3) {
			uvs.push((vert[i] - x0) / width, (vert[i + 1] - y0) / height);
		}
		geom.setAttribute("uv", new THREE.Float32BufferAttribute(uvs, 2));
	}
}


type BlockConstructor = new () => DEMBlockBase;

function createBlock(layer: DEMLayer) {
	const { dataType } = layer.properties;

	let BlockClass: BlockConstructor = (dataType === "mesh") ? DEMMeshBlock : DEMGridBlock;

	return new BlockClass();
}


/*
 The GridGeometry class is almost the same as PlaneGeometry, but it does not
 generate triangles that include vertices with no-data values.

 It supports tile mode. When the grid has margin areas (right/top)
 with no actual data, pass `segments` explicitly so that UV coordinates
 are calculated based on the full tile extent rather than only the
 data-containing region.
*/
export class GridGeometry extends THREE.BufferGeometry {

	/**
	 * @param array     - DEM values
	 * @param columns   - Number of columns of actual grid data
	 * @param rows      - Number of rows of actual grid data
	 * @param extent    - Extent of the plane
	 * @param nodata    - No data value
	 * @param segments	- Segments of a tile side. When supplied, the grid is treated as a square tile.
	 */
	loadData(array: Float32Array, columns: number, rows: number, extent: MapExtent, nodata?: number | Float32Array, segments?: number) {
		if (nodata instanceof Float32Array) nodata = nodata[0];

		const { width, height }  = extent;
		const isTileMode = (segments !== undefined);
		const segmentsX = (isTileMode) ? segments : columns - 1;
		const segmentsY = (isTileMode) ? segments : rows - 1;
		const segment_width = width / segmentsX;
		const segment_height = ((isTileMode) ? width : height) / segmentsY;
		const half_w = width / 2;
		const half_h = ((isTileMode) ? width : height) / 2;
		const iyd = (isTileMode) ? segments - rows + 1 : 0;

		const indices = [];
		const vertices = [];
		const uvs = [];

		let vertexIndex = 0;
		let currIndices = new Array(columns);
		let prevIndices = new Array(columns);

		for (let iy = 0; iy < rows; iy++) {

		    currIndices.fill(-1);

			const iyt = iy + iyd;
			const y = -iyt * segment_height + half_h;
			const v = 1 - (iyt / segmentsY);

			for (let ix = 0; ix < columns; ix++) {

				const i = ix + iy * columns;
				const z = array[i];

				if (z === nodata) continue;

				currIndices[ix] = vertexIndex;
				++vertexIndex;

				const x = ix * segment_width - half_w;

				vertices.push(x, y, z);
				uvs.push(ix / segmentsX, v);

				if (ix === 0 || iy === 0) continue;

				/*
				prev: a - d
				      | / |
				curr: b - c
				*/
				const a = prevIndices[ix - 1];
				const b = currIndices[ix - 1];
				const c = currIndices[ix];
				const d = prevIndices[ix];

				if (b === -1 || d == -1) continue
				if (a !== -1) indices.push(a, b, d);
				if (c !== -1) indices.push(b, c, d);
			}

			[prevIndices, currIndices] = [currIndices, prevIndices];
		}

		this.setIndex(indices);
		this.setAttribute('position', new THREE.Float32BufferAttribute(vertices, 3));
		this.setAttribute('uv', new THREE.Float32BufferAttribute(uvs, 2));
		this.computeBoundingSphere();
		this.computeBoundingBox();
		this.computeVertexNormals();
	}
}


export function buildTile(layer, data, tile, showBoundingBox = false, showBoundingVolume = false) {
	const material = new Material();
	material.loadData(data.material);
	layer.materials.add(material);

	const geometry = new GridGeometry();
	const mesh = new THREE.Mesh(geometry, material.mtl);
	mesh.position.fromArray(data.translate);

	const geom_data = data.grid;
	decodeBase64TypedArrayObject(geom_data.grid).then((grid_data: ParsedDEMGridData) => {
		geometry.loadData(grid_data.dem_values, grid_data.columns, grid_data.rows, geom_data.extent, grid_data.nodata, geom_data.segments);

		mesh.material.needsUpdate = true;		// update shader after computing vertex normals

		if (showBoundingBox) {
			const helper = new THREE.Box3Helper(
				geometry.boundingBox,
				0xffff00
			);
			helper.updateMatrixWorld();     // necessary because the helper is a grandchild of TilesGroup, which does not call this
			mesh.add(helper);
		}

		if (showBoundingVolume) {
			const box = tile.boundingVolume.box;
			const helper = new THREE.Box3Helper(
				new THREE.Box3().setFromCenterAndSize(
					new THREE.Vector3().fromArray(box),
					new THREE.Vector3(box[3] * 2, box[7] * 2, box[11] * 2)
				),
				0x33ff33
			);
			layer.objectGroup.add(helper);
		}
	});

	const { engineData } = tile;
	engineData.materials = [material.mtl];
	engineData.geometry = [geometry];
	engineData.textures = [];
	engineData.scene = mesh;
	engineData.metadata = null;
}
