// (C) 2014 Minoru Akagi
// SPDX-License-Identifier: MIT

import { THREE } from "../three.js";

import { modules, Group, LayerType, UV } from "../core.js";
import { BuilderBase, VectorLayer } from "./vectorlayer.js";
import { Materials } from "../material.js";
import { createWallGeometry } from "../utils.js";


export class LineLayer extends VectorLayer {

    BuilderFactory = {
        "Line": LineBuilder,
        "Thick Line": ThickLineBuilder,
        "Pipe": PipeBuilder,
        "Cone": ConeBuilder,
        "Box": BoxBuilder,
        "Wall": WallBuilder
    }

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

    buildLabels(features) { }	// Line layer doesn't support label

    // prepare for growing line animation
    prepareAnimation(sequential) {

        if (this.origMtls !== undefined) return;

        const computeLineDistances = (obj) => {
            if (obj.material.isLineDashedMaterial !== true) return;

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

                if (m.isLineDashedMaterial) {
                    mtl = m.clone();
                    mtl.gapSize = 1;
                }
                else if (m.isLineBasicMaterial) {
                    mtl = new THREE.LineDashedMaterial({
                        color: m.color,
                        opacity: m.opacity,
                        gapSize: 1
                    });
                }
                else {	// MeshLineMaterial
                    mtl = new modules.meshline.MeshLineMaterial();
                    mtl.color = m.color;
                    mtl.opacity = m.opacity;
                    mtl.lineWidth = m.lineWidth;
                    mtl.dashArray = 2;
                    mtl.transparent = true;
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
                else if (mtl.isLineBasicMaterial) {
                    mtl = new THREE.LineDashedMaterial({
                        color: mtl.color,
                        opacity: mtl.opacity
                    });
                }
                else {	// MeshLineMaterial
                    mtl.dashArray = 2;
                    mtl.transparent = true;
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
            else { // MeshLineMaterial
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


class Builder extends BuilderBase {

    createObjects(f) {
        const objs = [];
        for (const line of f.geom.lines) {
            const obj = this.createObject(f, line);
            obj.userData.mtl = f.mtl;

            objs.push(obj);
        }
        return objs;
    }

    createObject(f, vertices) { }

}


class LineBuilder extends Builder {

    constructor(layer) {
        super("Line", layer);
    }

    createObject(f, vertices) {
        const obj = new THREE.Line(
            new THREE.BufferGeometry().setAttribute("position", new THREE.Float32BufferAttribute(vertices, 3)),
            this.materials.mtl(f.mtl.idx)
        );
        if (obj.material instanceof THREE.LineDashedMaterial) obj.computeLineDistances();
        return obj;
    }

}


class ThickLineBuilder extends Builder {

    constructor(layer) {
        super("Thick Line", layer);
    }

    createObject(f, vertices) {
        const geom = new modules.meshline.MeshLineGeometry();
        geom.setPoints(vertices);

        const mesh = new THREE.Mesh(geom, this.materials.mtl(f.mtl.idx));
        mesh.raycast = modules.meshline.raycast;
        return mesh;
    }

}


class CylinderBuilderBase extends Builder {

    constructor(type, layer) {
        super(type, layer);

        this.cylinGeom = null;
        this.jointGeom = null;

        this.pt0 = new THREE.Vector3();
        this.pt1 = new THREE.Vector3();
        this.sub = new THREE.Vector3();
    }

    createObject(f, vertices) {
        const { cylinGeom, jointGeom, pt0, pt1, sub, materials } = this;
        const axis = UV.j;

        const group = new Group();
        const material = materials.mtl(f.mtl.idx);

        pt0.fromArray(vertices[0]);
        for (let i = 1; i < vertices.length; i++) {
            pt1.fromArray(vertices[i]);

            const cylinder = new THREE.Mesh(cylinGeom, material);
            cylinder.scale.set(f.geom.r, pt0.distanceTo(pt1), f.geom.r);
            cylinder.position.set(
                (pt0.x + pt1.x) / 2,
                (pt0.y + pt1.y) / 2,
                (pt0.z + pt1.z) / 2
            );
            cylinder.quaternion.setFromUnitVectors(axis, sub.subVectors(pt1, pt0).normalize());

            group.add(cylinder);

            if (jointGeom && i < vertices.length - 1) {
                const joint = new THREE.Mesh(jointGeom, material);
                joint.scale.setScalar(f.geom.r);
                joint.position.copy(pt1);

                group.add(joint);
            }

            pt0.copy(pt1);
        }
        return group;
    }

}


class PipeBuilder extends CylinderBuilderBase {

    constructor(layer) {
        super("Pipe", layer);

        this.cylinGeom = new THREE.CylinderGeometry(1, 1, 1, 32);
        this.jointGeom = new THREE.SphereGeometry(1, 32, 32);
    }

}


class ConeBuilder extends CylinderBuilderBase {

    constructor(layer) {
        super("Cone", layer);

        this.cylinGeom = new THREE.CylinderGeometry(0, 1, 1, 32);
    }

}


class BoxBuilder extends Builder {

    constructor(layer) {
        super("Box", layer);

        // In this method, box corners are exposed near joint when both azimuth and slope of
        // the segments of both sides are different. Also, some unnecessary faces are created.
        this.jnt_idx = [
            0, 5, 4, 4, 5, 1,   // left turn - top, side, bottom
            3, 0, 7, 7, 0, 4,
            6, 3, 2, 2, 3, 7,
            4, 1, 0, 0, 1, 5,   // right turn - top, side, bottom
            1, 2, 5, 5, 2, 6,
            2, 7, 6, 6, 7, 3
        ];

        this.pt0 = new THREE.Vector3();
        this.pt1 = new THREE.Vector3();
        this.sub = new THREE.Vector3();
        this.pt = new THREE.Vector3();
        this.ptM = new THREE.Vector3();
        this.scale1 = new THREE.Vector3(1, 1, 1);
        this.matrix = new THREE.Matrix4();
        this.quat = new THREE.Quaternion();
    }

    createObject(f, vertices) {
        const { jnt_idx, pt0, pt1, sub, pt, ptM, scale1, matrix, quat } = this;
        const { w, h } = f.geom;

        const geometries = [];

        let vf4;
        pt0.fromArray(vertices[0]);

        for (let i = 1; i < vertices.length; i++) {
            pt1.fromArray(vertices[i]);

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

            // segment
            const boxGeom = new THREE.BoxGeometry(w, dist, h);
            boxGeom.deleteAttribute("normal");
            boxGeom.deleteAttribute("uv");
            boxGeom.applyMatrix4(matrix);
            geometries.push(boxGeom);

            // joint
            // backward side
            const wh4 = [
                [-w / 2, h / 2],
                [w / 2, h / 2],
                [w / 2, -h / 2],
                [-w / 2, -h / 2]
            ];

            const vb4 = [];

            for (let j = 0; j < 4; j++) {
                pt.set(wh4[j][0], -dist / 2, wh4[j][1]);
                pt.applyMatrix4(matrix);

                vb4.push(pt.x, pt.y, pt.z);
            }

            if (vf4) {
                const jntGeom = new THREE.BufferGeometry();
                jntGeom.setAttribute("position", new THREE.Float32BufferAttribute(vf4.concat(vb4), 3));
                jntGeom.setIndex(jnt_idx);
                geometries.push(jntGeom);
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
            this.materials.mtl(f.mtl.idx)
        );
    }

}


class WallBuilder extends Builder {

    constructor(layer) {
        super("Wall", layer);
    }

    createObject(f, vertices) {
        return new THREE.Mesh(
            createWallGeometry(vertices, () => f.geom.bh),
            this.materials.mtl(f.mtl.idx)
        );
    }

}
