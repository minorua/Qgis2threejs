// (C) 2014 Minoru Akagi
// SPDX-License-Identifier: MIT

import { THREE } from "../three.js";

import { deg2rad, Group, LayerType, UV } from "../core.js";
import { BuilderBase, VectorLayer } from "./vectorlayer.js";
import { Models } from "../model.js";

const HALF_PI = Math.PI / 2;


export class PointLayer extends VectorLayer {

    BuilderFactory = {
        "Sphere": SphereBuilder,
        "Cylinder": CylinderBuilder,
        "Cone": ConeBuilder,
        "Box": BoxBuilder,
        "Disk": DiskBuilder,
        "Plane": PlaneBuilder,
        "Point":  PointBuilder,
        "Billboard": BillboardBuilder,
        "3D Model": ModelBuilder
    }

    constructor() {
        super();
        this.type = LayerType.Point;
    }

	/**
	 * @param {import("../types.js").VectorLayerData | import("../types.js").FeatureBlockData} data
	 * @param {import("../scene.js").Scene} scene
	 */
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

    buildLabels(features) {
        super.buildLabels(features, f => f.geom.pts);
    }

}


class Builder extends BuilderBase {

    constructor(type, layer) {
        super(type, layer);

        this.geometry = null;
    }

    createObjects(f) {
        const { geometry, layer } = this;
        const material = layer.materials.mtl(f.mtl.idx);

        const meshes = [];
        for (const pt of f.geom.pts) {
            const mesh = new THREE.Mesh(geometry, material);
            this.transform(mesh, f.geom, pt);

            meshes.push(mesh);
        }
        return meshes;
    }

    transform(mesh, geom, pt) {}

}


class SphereBuilder extends Builder {

    constructor(layer) {
        super("Sphere", layer);

        this.geometry = new THREE.SphereGeometry(1, 32, 32);
    }

    transform(mesh, geom, pt) {
        mesh.scale.setScalar(geom.r);
        mesh.position.fromArray(pt);
    }

}


class BoxBuilder extends Builder {

    constructor(layer) {
        super("Box", layer);

        this.geometry = new THREE.BoxGeometry(1, 1, 1);
    }

    transform(mesh, geom, pt) {
        mesh.scale.set(geom.w, geom.h, geom.d);
        mesh.rotation.x = HALF_PI;
        mesh.position.set(pt[0], pt[1], pt[2] + geom.h / 2);
    }

}


class DiskBuilder extends Builder {

    constructor(layer) {
        super("Disk", layer);

        this.geometry = new THREE.CircleGeometry(1, 32);
    }

    transform(mesh, geom, pt) {
        mesh.scale.set(geom.r, geom.r * this.zScale, 1);
        mesh.rotateOnWorldAxis(UV.i, -geom.d * deg2rad);
        mesh.rotateOnWorldAxis(UV.k, -geom.dd * deg2rad);
        mesh.position.fromArray(pt);
    }

}


class PlaneBuilder extends Builder {

    constructor(layer) {
        super("Plane", layer);

        this.geometry = new THREE.PlaneGeometry(1, 1, 1, 1);
    }

    transform(mesh, geom, pt) {
        mesh.scale.set(geom.w, geom.l * this.zScale, 1);
        mesh.rotateOnWorldAxis(UV.i, -geom.d * deg2rad);
        mesh.rotateOnWorldAxis(UV.k, -geom.dd * deg2rad);
        mesh.position.fromArray(pt);
    }

}


class CBuilderBase extends Builder {

    transform(mesh, geom, pt) {
        mesh.scale.set(geom.r, geom.h, geom.r);
        mesh.rotation.x = HALF_PI;
        mesh.position.set(pt[0], pt[1], pt[2] + geom.h / 2);
    }

}


class CylinderBuilder extends CBuilderBase {

    constructor(layer) {
        super("Cylinder", layer);

        this.geometry = new THREE.CylinderGeometry(1, 1, 1, 32);
    }

}


class ConeBuilder extends CBuilderBase {

    constructor(layer) {
        super("Cone", layer);

        this.geometry = new THREE.CylinderGeometry(0, 1, 1, 32);
    }

}


class PointBuilder extends Builder {

    constructor(layer) {
        super("Point", layer)
    }

    build(features, startIndex) {
        const { layer } = this;
        for (let fidx = 0; fidx < features.length; fidx++) {
            const f = features[fidx];

            const obj = new THREE.Points(
                new THREE.BufferGeometry().setAttribute("position", new THREE.Float32BufferAttribute(f.geom.pts, 3)),
                layer.materials.mtl(f.mtl.idx)
            );
            obj.userData.properties = f.prop;

            layer.addFeature(startIndex + fidx, f, [obj]);
        }
    }

}


class BillboardBuilder extends Builder {

    constructor(layer) {
        super("Billboard", layer)
    }

    build(features, startIndex) {
        const { layer } = this;
        const { materials } = layer;

        const errMtl = {
            mtl: new THREE.SpriteMaterial({color: 0xffffff}),
            callbackOnLoad: () => {}
        };

        features.forEach((f, fidx) => {
            const material = (f.mtl) ? materials.get(f.mtl.idx) : errMtl;

            if (!f.mtl) {
                console.warn("[" + layer.properties.name + "] Billboard: There is a missing material.");
            }

            const gs = f.geom.size;
            const sprites = [];
            for (const pt of f.geom.pts) {
                const sprite = new THREE.Sprite(material.mtl);

                sprite.position.fromArray(pt);
                sprite.scale.set(gs, gs, 1);
                sprite.userData.properties = f.prop;

                sprites.push(sprite);
            }

            material.callbackOnLoad(() => {
                const { image } = material.mtl.map;
                const scaleY = gs * image.height / image.width;

                for (const sprite of sprites) {
                    sprite.scale.set(gs, scaleY, 1);
                    sprite.updateMatrixWorld();
                }
            });

            layer.addFeature(startIndex + fidx, f, sprites);
        });
    }

}


class ModelBuilder extends Builder {

    constructor(layer) {
        super("3D Model", layer)
    }

    build(features, startIndex) {
        const { layer } = this;

        const q = new THREE.Quaternion();
        const e = new THREE.Euler();

        features.forEach((f, fidx) => {
            const model = layer.models.get(f.model);

            if (!model) {
                console.warn(`[${layer.properties.name}] 3D Model: There is a missing model.`);
                return;
            }

            const groups = [];

            for (const pt of f.geom.pts) {
                const group = new Group();

                group.position.fromArray(pt);
                group.scale.set(1, 1, this.zScale);
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

            layer.addFeature(fidx + startIndex, f, groups);
        });

    }

}
