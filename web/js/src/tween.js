// (C) 2022 Minoru Akagi
// SPDX-License-Identifier: MIT

import { THREE } from "./three.js";
import { app, KeyframeType, Tweens } from "./core.js";

Tweens.cameraMotion = {

	type: KeyframeType.CameraMotion,

	curveFactor: 0,

	init: function (track) {
		const { origin, zScale } = app.scene.userData;
		const { keyframes } = track;
		const propList = [];
		const distList = [];

		const curveFactor = this.curveFactor;
		const vec3 = new THREE.Vector3();

		let prevCamera;

		for (let i = 0; i < keyframes.length; i++) {
			const camera = keyframes[i].camera;

			vec3.set(
				camera.x - camera.fx,
				camera.y - camera.fy,
				(camera.z - camera.fz) * zScale
			);

			const dist = vec3.length();
			const theta = Math.acos(vec3.z / dist);
			const phi = Math.atan2(vec3.y, vec3.x);

			camera.phi = phi;

			propList.push({
				p: i,
				fx: camera.fx - origin.x,
				fy: camera.fy - origin.y,
				fz: (camera.fz - origin.z) * zScale,
				d: dist,
				theta
			});

			if (prevCamera) {
				distList.push(
					Math.hypot(
						camera.x - prevCamera.x,
						camera.y - prevCamera.y
					)
				);
			}

			prevCamera = camera;
		}

		track.prop_list = propList;

		track.onUpdate = (obj, elapsed, isFirst) => {
			const p = obj.p - track.currentIndex;

			const phi0 = keyframes[track.currentIndex].camera.phi;
			let phi1 = isFirst ? phi0 : keyframes[track.currentIndex + 1].camera.phi;

			if (Math.abs(phi1 - phi0) > Math.PI) {
				// Take the shortest orbiting path.
				phi1 += Math.PI * (phi1 > phi0 ? -2 : 2);
			}

			const phi = phi0 * (1 - p) + phi1 * p;

			vec3.set(
				Math.cos(phi) * Math.sin(obj.theta),
				Math.sin(phi) * Math.sin(obj.theta),
				Math.cos(obj.theta)
			).setLength(obj.d);

			const dz = curveFactor ? (1 - (2 * p - 1) ** 2) * distList[track.currentIndex] * curveFactor : 0;

			app.camera.position.set(
				obj.fx + vec3.x,
				obj.fy + vec3.y,
				obj.fz + vec3.z + dz
			);

			app.camera.lookAt(obj.fx, obj.fy, obj.fz);
			app.controls.target.set(obj.fx, obj.fy, obj.fz);
		};

		// initial position
		track.onUpdate(track.prop_list[0], 1, true);
	}

};

Tweens.opacity = {

	type: KeyframeType.Opacity,

	init: function (track, layer) {

		for (const keyframe of track.keyframes) {
			track.prop_list.push({opacity: keyframe.opacity});
		}

		track.onUpdate = (obj, elapsed) => {
			layer.opacity = obj.opacity;
		};

		// initial opacity
		track.onUpdate(track.prop_list[0]);
	}

};

Tweens.texture = {

	type: KeyframeType.Texture,

	init: function (track, layer) {
		const { keyframes } = track;

		let effect;

		track.onStart = () => {
			const i = track.currentIndex;
			const from = keyframes[i].mtlIndex;
			const to = keyframes[i + 1].mtlIndex;

			effect = keyframes[i].effect;

			layer.prepareTexAnimation(from, to);
			layer.setTextureAt(null, effect);
		};

		track.onUpdate = (obj, elapsed) => {
			layer.setTextureAt(obj.p - track.currentIndex, effect);
		};

		for (let i = 0; i < keyframes.length; i++) {
			track.prop_list.push({ p: i });
		}
	}
};

Tweens.lineGrowing = {

	type: KeyframeType.GrowingLine,

	init: function (track, layer) {
		if (track._keyframes === undefined) {
			track._keyframes = track.keyframes;
		}

		const effectItem = track._keyframes[0];

		if (effectItem.sequential) {
			track.keyframes = [];
			track.prop_list = [];

			for (let i = 0; i < layer.features.length; i++) {
				const item = layer.features[i].anim;

				item.easing = effectItem.easing;
				track.keyframes.push(item);
				track.prop_list.push({ p: i });
			}

			track.keyframes.push({});
			track.prop_list.push({ p: layer.features.length });

			track.onUpdate = (obj, elapsed) => {
				layer.setLineLength(obj.p - track.currentIndex, track.currentIndex);
			};
		}
		else {
			track.keyframes = [effectItem, {}];
			track.prop_list = [{ p: 0 }, { p: 1 }];

			track.onUpdate = (obj, elapsed) => {
				layer.setLineLength(obj.p);
			};
		}

		layer.prepareAnimation(effectItem.sequential);
		layer.setLineLength(0);
	}

};
