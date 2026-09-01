// (C) 2017 Minoru Akagi
// SPDX-License-Identifier: MIT

import { THREE } from "./three.js";

import { conf, deg2rad, Group, UV } from "./core.js";
import { DEMLayer } from "./layer/demlayer.js";
import { PointLayer } from "./layer/pointlayer.js";
import { LineLayer } from "./layer/linelayer.js";
import { PolygonLayer } from "./layer/polygonlayer.js";

import type { AppData, BlockData, LayerData, SceneData, SceneEventMap, SceneProperties, TileData } from "./types.js";
import type { MapLayer } from "./layer/layer.js";

export class Scene extends THREE.Scene {

	mapLayers: Record<number, MapLayer> = {};		// key is layerId
	tilesRenderers = [];

	declare lightGroup: Group;
	declare labelGroup: Group;
	declare labelConnectorGroup: Group;
	declare userData: SceneProperties;
	declare addEventListener: THREE.EventDispatcher<SceneEventMap>["addEventListener"];
	declare dispatchEvent: THREE.EventDispatcher<SceneEventMap>["dispatchEvent"];

	constructor() {
		super();

		this.lightGroup = new Group();
		this.lightGroup.name = "light";
		this.add(this.lightGroup);

		this.labelGroup = new Group();
		this.labelGroup.name = "label";
		this.add(this.labelGroup);

		this.labelConnectorGroup = new Group();
		this.labelConnectorGroup.name = "label connector";
		this.add(this.labelConnectorGroup);
	}

	add(object) {
		super.add(object);
		object.updateMatrixWorld();
		return this;
	}

	forEachLayer(callback) {
		for (const layerId in this.mapLayers) {
			callback(this.mapLayers[layerId], layerId);
		}
	}

	loadData(data: AppData) {
		switch (data.type) {
			case "scene":
				this.loadSceneData(data);
				break;

			case "layer":
				this.loadLayerData(data);
				break;

			case "block":
				this.loadBlockData(data);
				break;
			case "tile":
				this.loadTileData(data);
				break;
		}
	}

	loadSceneData(data: SceneData) {
		const p = data.properties;
		if (p !== undefined) {
			// fog
			if (p.fog) {
				this.fog = new THREE.FogExp2(p.fog.color, p.fog.density);
			}

			// light
			if (p.light != this.userData.light) {
				this.lightGroup.clear();
				this.buildLights(conf.lights[p.light] || conf.lights.directional);
				this.dispatchEvent({ type: "lightChanged", light: p.light });
			}

			// set initial camera position and parameters
			const be = p.baseExtent;
			if (this.userData.origin === undefined) {
				const s = be.width;

				let pos, focal;
				let v = conf.viewpoint.preset;
				if (v) {
					pos = new THREE.Vector3().copy(v.pos).sub(p.origin);
					focal = new THREE.Vector3().copy(v.lookAt).sub(p.origin);
				}
				else {
					const pivot = new THREE.Vector3(be.cx, be.cy, p.origin.z).sub(p.origin);   // 2D center of extent in 3D world coordinates

					v = conf.viewpoint.default;
					pos = new THREE.Vector3().copy(v.pos).multiplyScalar(s).add(pivot);
					focal = new THREE.Vector3().copy(v.lookAt).multiplyScalar(s).add(pivot);
				}

				pos.z *= p.zScale;
				focal.z *= p.zScale;

				const near = 0.001 * s;
				const far = 100 * s;

				this.requestCameraUpdate(pos, focal, near, far);
			}

			this.userData = p;
		}

		// load layers
		if (data.layers !== undefined) {
			data.layers.forEach((layer) => this.loadLayerData(layer));
		}
	}

	loadLayerData(data: LayerData) {
		let layer = this.mapLayers[data.id];
		if (layer === undefined) {
			layer = createLayer(data);
			if (!layer) return;
			layer.addEventListener("renderRequest", () => this.requestRender());

			this.mapLayers[data.id] = layer;
			this.add(layer.objectGroup);
		}

		layer.loadData(data, this);

		this.requestRender();
	}

	loadBlockData(data: BlockData) {
		const layer = this.mapLayers[data.layer];
		if (layer === undefined) return;

		layer.loadData(data, this);

		this.requestRender();
	}

	loadTileData(data: TileData) {
		for (const tilesRenderer of this.tilesRenderers) {
			const plugin = tilesRenderer.plugins[0];
			plugin.dataReceived(data.url, data.data);
		}
	}

	buildLights(lights, rotation = 0) {
		let light;
		for (const p of lights) {
			if (p.type == "ambient") {
				light = new THREE.AmbientLight(p.color, p.intensity);
			}
			else if (p.type == "directional") {
				light = new THREE.DirectionalLight(p.color, p.intensity);
				light.position.copy(UV.j)
					.applyAxisAngle(UV.i, p.altitude * deg2rad)
					.applyAxisAngle(UV.k, (rotation - p.azimuth) * deg2rad);
			}
			else if (p.type == "point") {
				light = new THREE.PointLight(p.color, p.intensity, 0, p.decay);
				light.position.set(0, 0, p.height);
			}
			else {
				continue;
			}
			this.lightGroup.add(light);
		}
	}

	requestRender() {
		this.dispatchEvent({ type: "renderRequest" });
	}

	requestCameraUpdate(pos: THREE.Vector3, focal: THREE.Vector3, near: number, far: number) {
		this.dispatchEvent({ type: "cameraUpdateRequest", pos: pos, focal: focal, near: near, far: far });
	}

	visibleObjects(includeLabels = false) {
		let objs = [];

		for (const id in this.mapLayers) {
			const layer = this.mapLayers[id];
			if (!layer.visible) continue;

			objs = objs.concat(layer.visibleObjects());

			if (includeLabels && "labels" in layer) {
				objs = objs.concat(layer.labels);
			}
		}

		return objs;
	}

	// 3D world coordinates to map coordinates
	toMapCoordinates(pt) {
		const p = this.userData;
		return {
			x: p.origin.x + pt.x,
			y: p.origin.y + pt.y,
			z: p.origin.z + pt.z / p.zScale
		};
	}

	// map coordinates to 3D world coordinates
	toWorldCoordinates(pt, isLonLat = false) {
		const p = this.userData;
		if (isLonLat && typeof proj4 !== "undefined") {
			// WGS84 long,lat to map coordinates
			var t = proj4(p.proj).forward([pt.x, pt.y]);
			pt = { x: t[0], y: t[1], z: pt.z };
		}

		return {
			x: pt.x - p.origin.x,
			y: pt.y - p.origin.y,
			z: (pt.z - p.origin.z) * p.zScale
		};
	}

	// return bounding box in 3d world coordinates
	boundingBox(onlyVisible = false) {
		const box = new THREE.Box3();
		for (const id in this.mapLayers) {
			if (onlyVisible && !this.mapLayers[id].visible) continue;

			const b = this.mapLayers[id].boundingBox();
			if (b) box.union(b);
		}
		return box;
	}

	// 3d tiles renderer
	addTilesRenderer(tilesRenderer) {
		this.tilesRenderers.push(tilesRenderer);
	}

	removeTilesRenderer(tilesRenderer) {
		const i = this.tilesRenderers.indexOf(tilesRenderer);
		if (i !== -1) {
			this.tilesRenderers.splice(i, 1);
		}
	}

}

function createLayer(data: LayerData) {
	const LayerClass = {
		dem: DEMLayer,
		point: PointLayer,
		line: LineLayer,
		polygon: PolygonLayer,
	}[data.properties.type];

	if (!LayerClass) {
		console.error("Unknown layer type:" + data.properties.type);
		return null;
	}

	const layer = new LayerClass();
	layer.id = data.id;
	layer.objectGroup.userData.layerId = data.id;

	return layer;
}
