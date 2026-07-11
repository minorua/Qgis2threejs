// (C) 2014 Minoru Akagi
// SPDX-License-Identifier: MIT

import { THREE } from "../three.js";

import { deg2rad, Group, LayerType, UV } from "../core.js";
import { VectorLayer } from "./vectorlayer.js";
import { Models } from "../model.js";


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
