// (C) 2017 Minoru Akagi
// SPDX-License-Identifier: MIT

import { THREE } from "./three.js";

import { app, conf, modules, MaterialType } from "./core.js";


export class Material {

	constructor() {
		this.loaded = false;
	}

	// material: a THREE.Material-based object
	set(material) {
		this.mtl = material;
		this.origProp = {};
		return this;
	}

	// callback is called when material has been completely loaded
	loadData(data, callback) {
		this.origProp = data;
		this.groupId = data.mtlIndex;

		const m = data;
		const opt = {};
		let defer = false;

		if (m.ds) opt.side = THREE.DoubleSide;

		if (m.flat) opt.flatShading = true;

		// texture
		if (m.image !== undefined) {
			if (m.image.url !== undefined) {
				opt.map = app.loadTextureFile(m.image.url, () => {
					this._loadCompleted(callback);
				});
				defer = true;
			}
			else {    // base64
				opt.map = new THREE.TextureLoader(app.loadingManager).load(m.image.base64);
				defer = true;
				delete m.image.base64;
			}
			opt.map.anisotropy = conf.texture.anisotropy;
			opt.map.colorSpace = THREE.SRGBColorSpace;
		}

		if (m.c !== undefined) opt.color = m.c;

		if (m.o !== undefined && m.o < 1) {
			opt.opacity = m.o;
			opt.transparent = true;
		}

		if (m.t) opt.transparent = true;

		if (m.w) opt.wireframe = true;

		if (m.bm) {
			this.mtl = new THREE.MeshBasicMaterial(opt);
		}
		else if (m.type == MaterialType.MeshLambert) {
			this.mtl = new THREE.MeshLambertMaterial(opt);
		}
		else if (m.type == MaterialType.MeshPhong) {
			this.mtl = new THREE.MeshPhongMaterial(opt);
		}
		else if (m.type == MaterialType.MeshToon) {
			this.mtl = new THREE.MeshToonMaterial(opt);
		}
		else if (m.type == MaterialType.Point) {
			opt.size = m.s;
			this.mtl = new THREE.PointsMaterial(opt);
		}
		else if (m.type == MaterialType.Line) {

			if (m.dashed) {
				opt.dashSize = conf.line.dash.dashSize;
				opt.gapSize = conf.line.dash.gapSize;
				this.mtl = new THREE.LineDashedMaterial(opt);
			}
			else {
				this.mtl = new THREE.LineBasicMaterial(opt);
			}
		}
		else if (m.type == MaterialType.MeshLine) {

			opt.lineWidth = m.thickness;
			if (m.dashed) {
				opt.dashArray = 0.03;
				opt.dashRatio = 0.45;
				opt.dashOffset = 0.015;
				opt.transparent = true;
			}
			// opt.sizeAttenuation = 1;

			this.mtl = new modules.meshline.MeshLineMaterial(opt);
			this._updateAspect = () => {
				this.mtl.resolution.set(app.width, app.height);
			};

			this._updateAspect();
			app.addEventListener("canvasSizeChanged", this._updateAspect);
		}
		else if (m.type == MaterialType.Sprite) {
			opt.color = 0xffffff;
			this.mtl = new THREE.SpriteMaterial(opt);
		}
		else {
			if (m.roughness !== undefined) opt.roughness = m.roughness;
			if (m.metalness !== undefined) opt.metalness = m.metalness;

			this.mtl = new THREE.MeshStandardMaterial(opt);
		}

		if (!defer) this._loadCompleted(callback);
	}

	_loadCompleted(anotherCallback) {
		this.loaded = true;

		if (this._callbacks !== undefined) {
			for (const callback of this._callbacks) {
				callback();
			}
			this._callbacks = [];
		}

		if (anotherCallback) anotherCallback();
	}

	callbackOnLoad(callback) {
		if (this.loaded) return callback();

		if (this._callbacks === undefined) this._callbacks = [];
		this._callbacks.push(callback);
	}

	dispose() {
		if (!this.mtl) return;

		if (this.mtl.map) this.mtl.map.dispose();   // dispose of texture
		this.mtl.dispose();
		this.mtl = null;

		if (this._updateAspect) {
			app.removeEventListener("canvasSizeChanged", this._updateAspect);
			this._updateAspect = undefined;
		}
	}
}


export class Materials extends THREE.EventDispatcher {

	constructor() {
		super();
		this.array = [];
	}

	// material: instance of Material object or THREE.Material-based object
	add(material) {
		if (material instanceof Material) {
			this.array.push(material);
		}
		else {
			this.array.push(new Material().set(material));
		}
	}

	get(index) {
		return this.array[index];
	}

	mtl(index) {
		return this.array[index].mtl;
	}

	loadData(data) {
		let iterated = false;

		const callback = () => {
			if (iterated) this.dispatchEvent({type: "renderRequest"});
		};

		for (const m of data) {
			const mtl = new Material();
			mtl.loadData(m, callback);
			this.add(mtl);
		}
		iterated = true;
	}

	dispose() {
		for (const m of this.array) {
			m.dispose();
		}
		this.array = [];
	}

	addFromObject3D(object) {
		const materials = new Set();

		object.traverse((obj) => {
			if (obj.material === undefined) return;

			for (const material of (Array.isArray(obj.material) ? obj.material : [obj.material])) {
				materials.add(material);
			}
		});

		for (const material of materials) {
			this.array.push(new Material().set(material));
		}
	}

	// opacity
	opacity() {
		if (this.array.length == 0) return 1;

		let sum = 0;
		for (const m of this.array) {
			sum += m.mtl.opacity;
		}
		return sum / this.array.length;
	}

	setOpacity(opacity) {
		for (const m of this.array) {
			m.mtl.opacity = opacity;

			const t = Boolean(m.origProp.t) || (opacity < 1);
			if (m.mtl.transparent !== t) {
				m.mtl.transparent = t;
				m.mtl.needsUpdate = true;
			}
		}
	}

	// wireframe: boolean
	setWireframeMode(wireframe) {
		for (const m of this.array) {
			if (m.origProp.w || m.mtl instanceof THREE.LineBasicMaterial) continue;
			m.mtl.wireframe = wireframe;
		}
	}

	removeItem(material, dispose) {
		for (let i = this.array.length - 1; i >= 0; i--) {
			if (this.array[i].mtl === material) {
				this.array.splice(i, 1);
				break;
			}
		}
		if (dispose) material.dispose();
	}

	removeItemsByGroupId(groupId) {
		for (let i = this.array.length - 1; i >= 0; i--) {
			if (this.array[i].groupId === groupId) {
				this.array.splice(i, 1);
			}
		}
	}

}
