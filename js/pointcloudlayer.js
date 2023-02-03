// (C) 2020 Minoru Akagi
// SPDX-License-Identifier: MIT

"use strict";

if (Q3D.Config.potree.basePath !== undefined) Potree.Global.workerPath = Q3D.Config.potree.basePath;
if (Q3D.Config.potree.maxNodesLoading !== undefined) Potree.Global.maxNodesLoading = Q3D.Config.potree.maxNodesLoading;

class Q3DPCGroup extends Potree.Group
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

class Q3DPCBBGroup extends Q3DGroup
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


class Q3DPointCloudLayer extends Q3DMapLayer {

	constructor() {
		super();
		this.type = Q3D.LayerType.PointCloud;
	}

	visibleObjects() {
		if (!this.visible) return [];

		var o = [];
		this.objectGroup.traverseVisible(function (obj) {
			o.push(obj);
		});
		return o;
	}

	loadJSONObject(jsonObject, scene) {

		var p = jsonObject.properties;
		var need_reload = (this.properties.colorType !== p.colorType);

		super.loadJSONObject(jsonObject, scene);

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

		this.pcg = new Q3DPCGroup(this);
		this.pcg.setPointBudget(10000000);
		this.addObject(this.pcg);

		var _this = this;

		Potree.loadPointCloud(p.url, p.name, function(e) {

			_this.pc = e.pointcloud;
			_this.pcg.add(e.pointcloud);
			_this.updatePosition(scene);

			_this.bbGroup = new Q3DPCBBGroup();
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
	}

	boundingBox() {
		return this.pcg.getBoundingBox();
	}

	updatePosition(scene) {
		var g = this.objectGroup,
			p = scene.userData;

		g.position.copy(scene.toWorldCoordinates({x: 0, y: 0, z: 0}));
		g.scale.z = p.zScale;
		g.updateMatrixWorld();
	}

	requestRepeatRender(interval, repeat, watch_loading) {

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
	}

	get visible() {
		return this.objectGroup.visible;
	}

	set visible(value) {
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

	loadedPointCount() {
		var c = 0;
		this.objectGroup.traverse(function (obj) {
			if (obj instanceof THREE.Points) {
				c += obj.geometry.getAttribute("position").count;
			}
		});
		return c;
	}

}

Q3D.PCGroup = Q3DPCGroup;
Q3D.PCBBGroup = Q3DPCBBGroup;
Q3D.PointCloudLayer = Q3DPointCloudLayer;
