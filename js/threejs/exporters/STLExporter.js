/**
 * @author kovacsv / http://kovacsv.hu/
 * @author minorua / http://github.com/minorua
 */
 
THREE.STLExporter = function () {
	this.stlContent = '';
	this.isBinary = false;
	this.header = '';
	this.binTriangleList = [];
};

THREE.STLExporter.prototype = {
	constructor: THREE.STLExporter,

	parse : function (scene) {

		return this.exportScene (scene);

	},
	
	exportScene : function (scene) {
		var meshes = [];
		
		var current;
		scene.traverse (function (current) {
			if (current instanceof THREE.Mesh) {
				meshes.push (current);
			}
		});
		
		return this.exportMeshes (meshes);
	},
	
	exportMesh : function (mesh) {
		return this.exportMeshes ([mesh]);
	},
	
	exportMeshes : function (meshes) {
		this.addLineToContent ('solid exported');
		
		var i, j, mesh, geometry, face, matrix, position;
		var m = new THREE.Matrix4(), m1 = new THREE.Matrix4(), m2 = new THREE.Matrix4(), m3 = new THREE.Matrix4();
		var normal, vertex1, vertex2, vertex3;
		for (i = 0; i < meshes.length; i++) {
			mesh = meshes[i];
			if (mesh.rotation.x || mesh.rotation.y || mesh.rotation.z) {
				geometry = mesh.geometry.clone();
				m1.makeRotationX(mesh.rotation.x);
				m2.makeRotationY(mesh.rotation.y);
				m3.makeRotationZ(mesh.rotation.z);
				m.multiplyMatrices(m1, m2);
				m.multiply(m3);
				geometry.applyMatrix(m);
			}
			else {
				geometry = mesh.geometry;
			}
			matrix = mesh.matrixWorld;
			position = mesh.position;
			
			for (j = 0; j < geometry.faces.length; j++) {
				face = geometry.faces[j];
				normal = face.normal;
				vertex1 = this.getTransformedPosition (geometry.vertices[face.a], matrix, position);
				vertex2 = this.getTransformedPosition (geometry.vertices[face.b], matrix, position);
				vertex3 = this.getTransformedPosition (geometry.vertices[face.c], matrix, position);
				this.addTriangleToContent (normal, vertex1, vertex2, vertex3);
			}
		};
		
		this.addLineToContent ('endsolid exported');

		if (this.isBinary) {
			var buf = new ArrayBuffer(84 + 50 * this.binTriangleList.length);
			var ui8 = new Uint8Array(buf, 0, 80);
			for (var i = 0; i < this.header.length; i++) {
				ui8[i] = this.header.charCodeAt(i);
			}
			var numTriangles = new Uint32Array(buf, 80, 1);
			numTriangles[0] = this.binTriangleList.length;
			for (var i = 0; i < this.binTriangleList.length; i++) {
				var src = new Uint8Array(this.binTriangleList[i]);
				var dst = new Uint8Array(buf, 84 + 50 * i, 50);
				dst.set(src)
			}
			return buf;
		} else {
			return this.stlContent;
		}
	},
	
	clearContent : function ()
	{
		this.stlContent = '';
		this.binTriangleList = [];
	},
	
	addLineToContent : function (line) {
		if (!this.isBinary) this.stlContent += line + '\n';
	},
	
	addTriangleToContent : function (normal, vertex1, vertex2, vertex3) {
		if (this.isBinary) {
			var buf = new ArrayBuffer(50);
			var f32 = new Float32Array(buf, 0, 3 * 4);
			var i16 = new Uint16Array(buf, 48, 1);
			var lst = [normal, vertex1, vertex2, vertex3];
			for (var i = 0; i < 4; i++) {
				f32[i * 3] = lst[i].x;
				f32[i * 3 + 1] = lst[i].y;
				f32[i * 3 + 2] = lst[i].z;
			}
			i16[0] = 0;
			this.binTriangleList.push(buf);
		} else {
			this.addLineToContent ('\tfacet normal ' + normal.x + ' ' + normal.y + ' ' + normal.z);
			this.addLineToContent ('\t\touter loop');
			this.addLineToContent ('\t\t\tvertex ' + vertex1.x + ' ' + vertex1.y + ' ' + vertex1.z);
			this.addLineToContent ('\t\t\tvertex ' + vertex2.x + ' ' + vertex2.y + ' ' + vertex2.z);
			this.addLineToContent ('\t\t\tvertex ' + vertex3.x + ' ' + vertex3.y + ' ' + vertex3.z);
			this.addLineToContent ('\t\tendloop');
			this.addLineToContent ('\tendfacet');
		}
	},
	
	getTransformedPosition : function (vertex, matrix, position) {
		var result = vertex.clone ();
		if (matrix !== undefined) {
			result.applyMatrix4 (matrix);
		}
		if (position !== undefined) {
			result.add (position);
		}
		return result;
	}
};
