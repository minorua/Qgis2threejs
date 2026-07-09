// (C) 2022 Minoru Akagi
// SPDX-License-Identifier: MIT

import { THREE } from "./three.js";
import { app, conf, tweens, KeyframeType } from "./core.js";
import { E } from "./utils.js";


app.animation = {

	isActive: false,

	start: function () {
		this.isActive = true;
		app.animate();
	},

	stop: function () {
		this.isActive = false;
	},

	keyframes: {

		isActive: false,

		isPaused: false,

		curveFactor: 0,

		easingFunction: function (easing) {
			if (easing == 1) return TWEEN.Easing.Linear.None;
			if (easing > 1) {
				const f = TWEEN.Easing[conf.animation.easingCurve];
				if (easing == 2) return f["InOut"];
				else if (easing == 3) return f["In"];
				else return f["Out"];   // easing == 4
			}
		},

		tracks: [],

		clear: function () {
			this.tracks = [];
		},

		load: function (track) {
			if (!Array.isArray(track)) track = [track];

			this.tracks = this.tracks.concat(track);
		},

		start: function () {

			const narBox = E("narrativebox");
			const btn = E("nextbtn");
			let currentNarElem;

			this.tracks.forEach((track) => {

				let tween;
				for (const p in tweens) {
					if (tweens[p].type == track.type) {
						tween = tweens[p];
						break;
					}
				}
				if (tween === undefined) {
					console.warn("unknown animation type: " + track.type);
					return;
				}

				const layer = (track.layerId !== undefined) ? app.scene.mapLayers[track.layerId] : undefined;

				track.completed = false;
				track.currentIndex = 0;
				track.prop_list = [];

				tween.init(track, layer);

				const keyframes = track.keyframes;

				const showNBox = (idx) => {
					// narrative box
					const n = keyframes[idx].narration;
					if (n && narBox) {
						if (currentNarElem) {
							currentNarElem.classList.remove("visible");
						}

						currentNarElem = E(n.id);
						if (currentNarElem) {
							currentNarElem.classList.add("visible");
						}
						else {    // preview
							E("narbody").innerHTML = n.text;
						}

						if (btn) {
							if (idx < keyframes.length - 1) {
								btn.className = "nextbtn";
								btn.innerHTML =  "";
							}
							else {
								btn.className = "";
								btn.innerHTML = "Close";
							}
						}

						setTimeout(() => {
							this.pause();
							narBox.classList.add("visible");
						}, 0);
					}
				};

				const onStart = () => {
					if (track.onStart) track.onStart();

					app.dispatchEvent({type: "tweenStarted", index: track.currentIndex});

					// pause if narrative box is shown
					if (narBox && narBox.classList.contains("visible")) {
						narBox.classList.remove("visible");
					}
				};

				const onComplete = (obj) => {
					if (!keyframes[track.currentIndex].easing) {
						track.onUpdate(obj, 1);
					}

					if (track.onComplete) track.onComplete(obj);

					const index = ++track.currentIndex;
					if (index == keyframes.length - 1) {
						track.completed = true;

						let completed = true;
						for (const t of this.tracks) {
							if (!t.completed) completed = false;
						}

						if (completed) {
							if (currentNarElem) {
								currentNarElem.classList.remove("visible");
							}

							if (conf.animation.repeat) {
								setTimeout(() => {
									this.start();
								}, 0);
							}
							else {
								this.stop();
							}
						}
					}

					// show narrative box if the current keyframe has a narrative content
					showNBox(index);
				};

				let t0, t1, t2;
				for (let i = 0; i < keyframes.length - 1; i++) {

					t2 = new TWEEN.Tween(track.prop_list[i]).delay(keyframes[i].delay).onStart(onStart)
										.to(track.prop_list[i + 1], keyframes[i].duration).onComplete(onComplete);

					if (keyframes[i].easing) {
						t2.easing(this.easingFunction(keyframes[i].easing)).onUpdate(track.onUpdate);
					}

					if (i == 0) {
						t0 = t2;
					}
					else {
						t1.chain(t2);
					}
					t1 = t2;
				}

				showNBox(0);

				t0.start();
			});

			app.animation.isActive = this.isActive = true;
			app.dispatchEvent({type: "animationStarted"});
			app.animate();
		},

		stop: function () {

			TWEEN.removeAll();

			app.animation.isActive = this.isActive = this.isPaused = false;
			this._pausedTweens = null;

			app.dispatchEvent({type: "animationStopped"});
		},

		pause: function () {

			if (this.isPaused) return;

			this._pausedTweens = TWEEN.getAll();

			if (this._pausedTweens.length) {
				for (const pt of this._pausedTweens) {
					pt.pause();
				}
				this.isPaused = true;
			}
			app.animation.isActive = this.isActive = false;
		},

		resume: function () {

			const box = E("narrativebox");
			if (box && box.classList.contains("visible")) {
				box.classList.remove("visible");
			}

			if (!this.isPaused) return;

			for (const pt of this._pausedTweens) {
				pt.resume();
			}
			this._pausedTweens = null;

			app.animation.isActive = this.isActive = true;
			this.isPaused = false;

			app.animate();
		}
	},

	orbit: {      // orbit animation

		isActive: false,

		start: function () {

			app.controls.autoRotate = true;
			app.animation.isActive = this.isActive = true;

			app.animate();
		},

		stop: function () {

			app.controls.autoRotate = false;
			app.animation.isActive = this.isActive = false;
		}
	}
};


tweens.cameraMotion = {

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

tweens.opacity = {

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

tweens.texture = {

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

tweens.lineGrowing = {

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
