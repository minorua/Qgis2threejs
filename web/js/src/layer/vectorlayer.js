// (C) 2014 Minoru Akagi
// SPDX-License-Identifier: MIT

import { THREE } from "../three.js";

import { app, conf, Group } from "../core.js";
import { MapLayer } from "./layer.js";


export class VectorLayer extends MapLayer {

	BuilderFactory = {}

	constructor() {
		super();
        this.builder = null;
		this.features = [];
		this.labels = [];
	}

    build(features, startIndex) {
        const { objType } = this.properties;

        if (!this.builder || this.builder.type !== objType) {
            const BuilderClass = this.BuilderFactory[objType];
            if (!BuilderClass) return;

            this.builder = new BuilderClass(this, this.sceneData.zScale);
        }

        this.builder.build(features, startIndex);
    }

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

	/**
	 * @param {import("../types.js").VectorLayerData} data
	 * @param {import("../scene.js").Scene} scene
	 */
	loadLayerData(data, scene) {
		this.clearObjects();
		this.clearLabels();

		super.loadLayerData(data, scene);

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
			if (block.url !== undefined) {
				app.loadJSONFile(block.url);
			}
			else {
				this.build(block.features, block.startIndex);
				if (this.properties.label !== undefined) this.buildLabels(block.features);
			}
		});
	}

	/**
	 * @param {import("../types.js").FeatureBlockData} data
	 * @param {import("../scene.js").Scene} scene
	 */
	loadBlockData(data, scene) {
		super.loadBlockData(data, scene);

		this.build(data.features, data.startIndex);
		if (this.properties.label !== undefined) this.buildLabels(data.features);
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


export class BuilderBase {

    constructor(type, layer) {
        this.type = type;
        this.layer = layer
        this.materials = layer.materials
        this.zScale = layer.sceneData.zScale;
    }

    build(features, startIndex) {
        const { layer } = this;

        for (let fidx = 0; fidx < features.length; fidx++) {
            const f = features[fidx];
			const objs = this.createObjects(f);

			for (const obj of objs) {
				obj.userData.properties = f.prop;
			}

            layer.addFeature(startIndex + fidx, f, objs);
        }
    }

	createObjects(f) { return []; }

}
