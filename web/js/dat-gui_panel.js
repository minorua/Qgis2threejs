// (C) 2014 Minoru Akagi
// SPDX-License-Identifier: MIT

import * as THREE from "three";
import { Q3D, deg2rad } from "./Qgis2threejs.js";

const app = Q3D.application;
const gui = Q3D.gui;
const conf = Q3D.Config;

gui.dat = {

	type: "dat-gui",

	parameters: {

		lyr: {},
		cp: {
			c: "#ffffff",
			d: 0,
			o: 1,
			l: false
		},
		cmd: {         // commands for touch screen devices
			rot: false,  // auto rotation
			wf: false    // wireframe mode
		},
		i: gui.showInfo
	}
};

(function () {
	gui.modules.push(gui.dat);

	const d = gui.dat;
	let panel;

	// initialize gui
	// - setupDefaultItems: default is true
	// - params: parameter values to pass to dat.GUI constructor
	d.init = (setupDefaultItems, params) => {
		setupDefaultItems = (setupDefaultItems === undefined) ? true : setupDefaultItems;

		panel = new dat.GUI(params);
		panel.domElement.parentElement.style.zIndex = 2000;   // display the panel on the front of labels

		d.gui = panel;

		if (setupDefaultItems) {
			d.layersFolder = panel.addFolder('Layers');
			if (conf.gui.customPlane) d.customPlaneFolder = panel.addFolder('Custom Plane');
			if (conf.animation.enabled) d.addAnimationFolder();
			if (Q3D.isTouchDevice) d.addCommandsFolder();
			d.addHelpButton();
		}
	};

	d.initLayersFolder = (scene) => {
		const params = d.parameters;
		const layersFolder = d.layersFolder;
		scene.forEachLayer((layer, layerId) => {
			params.lyr[layerId] = {i: layerId, v: layer.visible, o: layer.opacity, m: 0};
			const p = layer.properties;

			const folder = layersFolder.addFolder(p.name);
			folder.add(params.lyr[layerId], 'v').name('Visible').onChange(function (value) {
				layer.visible = value;
			});

			let mtls;
			const mtlNames = p.mtlNames;
			if (mtlNames && mtlNames.length > 1) {
				const items = {};
				for (let i = 0; i < mtlNames.length; i++) {
					items[mtlNames[i]] = i;
				}
				mtls = folder.add(params.lyr[layerId], 'm', items).name('Material').setValue(p.mtlIdx);
			}

			const op = folder.add(params.lyr[layerId], 'o').min(0).max(1).name('Opacity').onChange(function (value) {
				layer.opacity = value;
			});

			if (mtls) {
				mtls.onChange((idx) => {
					layer.currentMtlIndex = idx;
					params.lyr[layerId].o = layer.opacity;
					op.updateDisplay();
				});
			}
		});
		return layersFolder;
	};

	d.customPlaneMaterial = (color) => {
		return new THREE.MeshLambertMaterial({color: color, transparent: true, side: THREE.DoubleSide});
	};

	d.initCustomPlaneFolder = (zMin, zMax) => {
		const scene = app.scene;
		const p = scene.userData;
		const params = d.parameters;

		if (zMin === undefined || zMax === undefined) {
			const box = new THREE.Box3().setFromObject(scene);
			if (zMin === undefined) zMin = scene.toMapCoordinates({x: 0, y: 0, z: box.min.z}).z;
			if (zMax === undefined) zMax = scene.toMapCoordinates({x: 0, y: 0, z: box.max.z}).z;
		}

		const addPlane = (color) => {
			// Add a new plane in the current scene
			const geometry = new THREE.PlaneGeometry(p.baseExtent.width, p.baseExtent.height, 1, 1);
			const material = d.customPlaneMaterial(color);
			d.customPlane = new THREE.Mesh(geometry, material);
			d.customPlane.rotation.z = p.baseExtent.rotation * deg2rad;
			scene.add(d.customPlane);
			app.render();
		};
		params.cp.d = zMin;

		// Plane color
		d.customPlaneFolder.addColor(params.cp, 'c').name('Color').onChange((value) => {
			if (d.customPlane === undefined) addPlane(params.cp.c);
			d.customPlane.material.color.setStyle(value);
			app.render();
		});

		// Plane altitude
		d.customPlaneFolder.add(params.cp, 'd').min(zMin).max(zMax).name('Altitude').onChange((value) => {
			if (d.customPlane === undefined) addPlane(params.cp.c);
			d.customPlane.position.z = value * p.zScale;
			d.customPlane.updateMatrixWorld();
			app.render();
		});

		// Plane opacity
		d.customPlaneFolder.add(params.cp, 'o').min(0).max(1).name('Opacity (0-1)').onChange((value) => {
			if (d.customPlane === undefined) addPlane(params.cp.c);
			d.customPlane.material.opacity = value;
			app.render();
		});

		// Enlarge plane option
		d.customPlaneFolder.add(params.cp, 'l').name('Enlarge').onChange((value) => {
			if (d.customPlane === undefined) addPlane(params.cp.c);
			if (value) d.customPlane.scale.set(80, 80, 1);
			else d.customPlane.scale.set(1, 1, 1);
			d.customPlane.updateMatrixWorld();
			app.render();
		});
	};

	d.addAnimationFolder = () => {
		const anim = app.animation.keyframes;
		const folder = panel.addFolder('Animation');
		let btn;

		d.parameters.anm = {
			p: function () {
				if (anim.isActive) {
					anim.pause();
					btn.name('Resume');
				}
				else if (anim.isPaused) {
					anim.resume();
					btn.name('Pause');
				}
				else {
					anim.start();
				}
		}};
		btn = folder.add(d.parameters.anm, 'p').name('Play');

		app.addEventListener('animationStarted', () => {
			btn.name('Pause');
		});

		app.addEventListener('animationStopped', () => {
			btn.name('Play');
		});
	};

	// add commands folder for touch screen devices
	d.addCommandsFolder = () => {
		const folder = panel.addFolder('Commands');
		folder.add(d.parameters.cmd, 'rot').name('Orbit Animation').onChange(app.setRotateAnimationMode);
		folder.add(d.parameters.cmd, 'wf').name('Wireframe Mode').onChange(app.setWireframeMode);
	};

	d.addHelpButton = () => {
		panel.add(d.parameters, 'i').name('Help');
	};
})();
