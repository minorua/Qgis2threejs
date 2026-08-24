// (C) 2014 Minoru Akagi
// SPDX-License-Identifier: MIT

import { THREE } from "../three.js";

import { deg2rad, Group, LayerType, UV } from "../core.js";
import { BuilderBase, VectorLayer } from "./vectorlayer.js";
import { Models } from "../model.js";

import type { GeomData, Vec3, VectorLayerData, FeatureBlockData, ModelObject, FeatureData } from "../types.js";
import type { Scene } from "../scene.js";


const HALF_PI = Math.PI / 2;


export class PointLayer extends VectorLayer {

    BuilderFactory = {
        "Sphere": SphereBuilder,
        "Cylinder": CylinderBuilder,
        "Cone": ConeBuilder,
        "Box": BoxBuilder,
        "Disk": DiskBuilder,
        "Plane": PlaneBuilder,
        "Point": PointBuilder,
        "Billboard": BillboardBuilder,
        "3D Model": ModelBuilder
    }

    declare models: Models;

    constructor() {
        super();
        this.type = LayerType.Point;
    }

    loadData(data: VectorLayerData | FeatureBlockData, scene: Scene): void {
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

    geometry = null;

    createObjects(f: FeatureData) {
        const { geometry, layer } = this;
        const material = layer.materials.mtl(f.mtl.idx);
        const geom = f.geom as GeomData;

        const meshes = [];
        for (const pt of geom.pts as Vec3[]) {
            const mesh = new THREE.Mesh(geometry, material);
            this.transform(mesh, geom, pt);

            meshes.push(mesh);
        }
        return meshes;
    }

    transform(mesh: THREE.Mesh, geom: GeomData, pt: Vec3) { }

}


class SphereBuilder extends Builder {

    type = "Sphere";

    constructor(layer) {
        super(layer);

        this.geometry = new THREE.SphereGeometry(1, 32, 32);
    }

    transform(mesh: THREE.Mesh, geom: GeomData, pt: Vec3) {
        mesh.scale.setScalar(geom.r);
        mesh.position.fromArray(pt);
    }

}


class BoxBuilder extends Builder {

    type = "Box";

    constructor(layer) {
        super(layer);

        this.geometry = new THREE.BoxGeometry(1, 1, 1);
    }

    transform(mesh: THREE.Mesh, geom: GeomData, pt: Vec3) {
        mesh.scale.set(geom.w, geom.h, geom.d);
        mesh.rotation.x = HALF_PI;
        mesh.position.set(pt[0], pt[1], pt[2] + geom.h / 2);
    }

}


class DiskBuilder extends Builder {

    type = "Disk";

    constructor(layer) {
        super(layer);

        this.geometry = new THREE.CircleGeometry(1, 32);
    }

    transform(mesh: THREE.Mesh, geom: GeomData, pt: Vec3) {
        mesh.scale.set(geom.r, geom.r * this.zScale, 1);
        mesh.rotateOnWorldAxis(UV.i, -geom.d * deg2rad);
        mesh.rotateOnWorldAxis(UV.k, -geom.dd * deg2rad);
        mesh.position.fromArray(pt);
    }

}


class PlaneBuilder extends Builder {

    type = "Plane";

    constructor(layer) {
        super(layer);

        this.geometry = new THREE.PlaneGeometry(1, 1, 1, 1);
    }

    transform(mesh: THREE.Mesh, geom: GeomData, pt: Vec3) {
        mesh.scale.set(geom.w, geom.l * this.zScale, 1);
        mesh.rotateOnWorldAxis(UV.i, -geom.d * deg2rad);
        mesh.rotateOnWorldAxis(UV.k, -geom.dd * deg2rad);
        mesh.position.fromArray(pt);
    }

}


class CBuilderBase extends Builder {

    transform(mesh: THREE.Mesh, geom: GeomData, pt: Vec3) {
        mesh.scale.set(geom.r, geom.h, geom.r);
        mesh.rotation.x = HALF_PI;
        mesh.position.set(pt[0], pt[1], pt[2] + geom.h / 2);
    }

}


class CylinderBuilder extends CBuilderBase {

    type = "Cylinder";

    constructor(layer) {
        super(layer);

        this.geometry = new THREE.CylinderGeometry(1, 1, 1, 32);
    }

}


class ConeBuilder extends CBuilderBase {

    type = "Cone";

    constructor(layer) {
        super(layer);

        this.geometry = new THREE.CylinderGeometry(0, 1, 1, 32);
    }

}


class PointBuilder extends Builder {

    type = "Point";

    build(features: FeatureData[], startIndex: number) {
        const { layer } = this;
        for (let fidx = 0; fidx < features.length; fidx++) {
            const f = features[fidx];
            const { pts } = f.geom as GeomData;

            const obj = new THREE.Points(
                new THREE.BufferGeometry().setAttribute("position", new THREE.Float32BufferAttribute(pts as number[], 3)),
                layer.materials.mtl(f.mtl.idx)
            );
            obj.userData.properties = f.prop;

            layer.addFeature(startIndex + fidx, f, [obj]);
        }
    }

}


class BillboardBuilder extends Builder {

    type = "Billboard";

    build(features: FeatureData[], startIndex: number) {
        const { layer } = this;
        const { materials } = layer;

        const errMtl = {
            mtl: new THREE.SpriteMaterial({ color: 0xffffff }),
            callbackOnLoad: () => { }
        };

        features.forEach((f, fidx) => {
            const material = (f.mtl) ? materials.get(f.mtl.idx) : errMtl;
            const mtl = material.mtl as THREE.SpriteMaterial;

            if (!f.mtl) {
                console.warn("[" + layer.properties.name + "] Billboard: There is a missing material.");
            }

            const { size, pts } = f.geom as GeomData;
            const sprites = [];
            for (const pt of pts as Vec3[]) {
                const sprite = new THREE.Sprite(mtl);

                sprite.position.fromArray(pt);
                sprite.scale.set(size, size, 1);
                sprite.userData.properties = f.prop;

                sprites.push(sprite);
            }

            material.callbackOnLoad(() => {
                const { image } = mtl.map;
                const scaleY = size * image.height / image.width;

                for (const sprite of sprites) {
                    sprite.scale.set(size, scaleY, 1);
                    sprite.updateMatrixWorld();
                }
            });

            layer.addFeature(startIndex + fidx, f, sprites);
        });
    }

}


class ModelBuilder extends Builder {

    type = "3D Model";

    build(features: FeatureData[], startIndex: number) {
        const layer = this.layer as PointLayer;

        const q = new THREE.Quaternion();
        const e = new THREE.Euler();

        features.forEach((f, fidx) => {
            const model = layer.models.get(f.model);

            if (!model) {
                console.warn(`[${layer.properties.name}] 3D Model: There is a missing model.`);
                return;
            }

            const {
                pts, scale,
                rotateX,
                rotateY,
                rotateZ,
                rotateO = "XYZ"
            } = f.geom as GeomData;

            const groups = [];
            for (const pt of pts as Vec3[]) {
                const group = new Group();

                group.position.fromArray(pt);
                group.scale.set(1, 1, this.zScale);
                group.userData.properties = f.prop;

                groups.push(group);
            }

            model.callbackOnLoad((loadedModel: ModelObject) => {
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
