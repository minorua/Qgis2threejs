// (C) 2020 Minoru Akagi
// SPDX-License-Identifier: MIT

"use strict";

(function () {
	if (Q3D.Config.potree.basePath !== undefined) Potree.Global.workerPath = Q3D.Config.potree.basePath;
	if (Q3D.Config.potree.maxNodesLoading !== undefined) Potree.Global.maxNodesLoading = Q3D.Config.potree.maxNodesLoading;

	class Q3DGRP extends Potree.Group
	{
		constructor(layer)
		{
			super();
			this.layer = layer;
			this.timerId = null;
		}

		onBeforeRender(renderer, scene, camera, geometry, material, group)
		{
			super.onBeforeRender(renderer, scene, camera, geometry, material, group);

			if (this.layer.bbGroup !== undefined) this.layer.bbGroup.setParent();
		}

		onAfterRender(renderer, scene, camera, geometry, material, group)
		{
			super.onAfterRender(renderer, scene, camera, geometry, material, group);

			// repeat rendering as long as there are loading nodes
			if (Potree.Global.numNodesLoading && this.timerId === null) {
				var _this = this;
				_this.timerId = window.setTimeout(function () {
					_this.timerId = null;
					_this.layer.requestRender();
				}, 10);
			}
		}
	}

	class Q3DBBGRP extends Q3D.Group
	{
		constructor()
		{
			super();
			this.orphanIndex = 0;
		}

		setParent()
		{
			var c;
			for (var i = this.orphanIndex; i < this.children.length; i++) {
				c = this.children[i];
				c.parent = this;
				c.matrixAutoUpdate = true;
				c.updateMatrixWorld();
			}
			this.orphanIndex = i;
		}

	}

	Q3D.PCGroup = Q3DGRP;
	Q3D.PCBBGroup = Q3DBBGRP;
})();


/*
Q3D.PointCloudLayer --> Q3D.MapLayer
*/
Q3D.PointCloudLayer = function () {
	Q3D.MapLayer.call(this);
	this.type = Q3D.LayerType.PointCloud;
};

Q3D.PointCloudLayer.prototype = Object.create(Q3D.MapLayer.prototype);
Q3D.PointCloudLayer.prototype.constructor = Q3D.PointCloudLayer;

Q3D.PointCloudLayer.prototype.visibleObjects = function () {
	if (!this.visible) return [];

	var o = [];
	this.objectGroup.traverseVisible(function (obj) {
		o.push(obj);
	});
	return o;
};

Q3D.PointCloudLayer.prototype.loadJSONObject = function (jsonObject, scene) {

	var p = jsonObject.properties;
	var need_reload = (this.properties.colorType !== p.colorType);

	Q3D.MapLayer.prototype.loadJSONObject.call(this, jsonObject, scene);

	if (this.pcg !== undefined) {
		if (!need_reload) {
			this.updatePosition(scene);

			if (this.pc !== undefined) {
				this.pc.showBoundingBox = p.boxVisible;
			}

			if (p.color !== undefined) this.materials.mtl(0).color = new THREE.Color(p.color);
			return;
		}

		this.clearObjects();

		var g = this.objectGroup;
		g.position.set(0, 0, 0);
		g.rotation.set(0, 0, 0);
		g.scale.set(1, 1, 1);
		g.updateMatrixWorld();
	}

	this.pcg = new Q3D.PCGroup(this);
	this.pcg.setPointBudget(10000000);
	this.addObject(this.pcg);

	var _this = this;

	Potree.loadPointCloud(p.url, p.name, function(e) {

		_this.pc = e.pointcloud;
		_this.pcg.add(e.pointcloud);
		_this.updatePosition(scene);

		_this.bbGroup = new Q3D.PCBBGroup();
		_this.bbGroup.position.copy(_this.pc.position);
		_this.bbGroup.children = _this.pc.boundingBoxNodes;
		_this.addObject(_this.bbGroup);

		_this.pc.showBoundingBox = p.boxVisible;

		var mtl = _this.pc.material;
		mtl.pointColorType = Potree.PointColorType[p.colorType];

		if (p.color !== undefined) mtl.color = new THREE.Color(p.color);

		if (p.colorType == "HEIGHT") {
			var box = _this.boundingBox();
			mtl.elevationRange = [box.min.z, box.max.z];
		}
		_this.materials.add(mtl);

		_this.requestRepeatRender(300, 60, true);
	});
};

Q3D.PointCloudLayer.prototype.boundingBox = function () {
	return this.pcg.getBoundingBox();
};

Q3D.PointCloudLayer.prototype.updatePosition = function (scene) {
	var g = this.objectGroup,
		p = scene.userData;

	g.position.copy(scene.toWorldCoordinates({x: 0, y: 0, z: 0}));
	g.scale.z = p.zScale;
	g.updateMatrixWorld();
};

Q3D.PointCloudLayer.prototype.requestRepeatRender = function (interval, repeat, watch_loading) {

	if (repeat == 0) return;

	var _this = this, count = 0, timer_id = null;

	var tick_func = function () {

		_this.requestRender();

		if (++count > repeat || (watch_loading && !Potree.Global.numNodesLoading)) {
			if (timer_id !== null) window.clearInterval(timer_id);
			return false;
		}
		return true;
	};

	if (tick_func()) timer_id = window.setInterval(tick_func, interval);
};

Object.defineProperty(Q3D.PointCloudLayer.prototype, "visible", {
	get: function () {
		return this.objectGroup.visible;
	},
	set: function (value) {
		this.objectGroup.visible = value;

		if (this.pcg === undefined) return;

		if (value) {
			this.objectGroup.add(this.pcg);
		}
		else {
			this.objectGroup.remove(this.pcg);
		}

		this.requestRender();
	}
});

Q3D.PointCloudLayer.prototype.loadedPointCount = function () {
	var c = 0;
	this.objectGroup.traverse(function (obj) {
		if (obj instanceof THREE.Points) {
			c += obj.geometry.getAttribute("position").count;
		}
	});
	return c;
};
