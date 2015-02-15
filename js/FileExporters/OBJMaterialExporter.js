/**
 * @author olivier dalang / https://github.com/olivierdalang
 * based on STLExport.js by mrdoob / http://mrdoob.com/
 */
 
THREE.OBJMaterialExporter = function () {};

THREE.OBJMaterialExporter.prototype = {

	constructor: THREE.OBJMaterialExporter,

	parse: ( function ( scene ) {

			var vector = new THREE.Vector3();
			var normalMatrixWorld = new THREE.Matrix3();

			var output = '';
			var v_index = 1;
			var o_index = 1;

			var materials_hexstrings = [];

			scene.traverse( function ( object ) {

				if ( object instanceof THREE.Mesh ) {

					var geometry = object.geometry;
					var matrixWorld = object.matrixWorld;
					
					var material = object.material;
					var hexString = material.color.getHexString();

					if ( geometry instanceof THREE.Geometry ) {

						var material = object.material;
						var hexString = material.color.getHexString();

						if( materials_hexstrings.indexOf(hexString)==-1 ){

							materials_hexstrings.push(hexString);
							output += 'newmtl Mat_' + (hexString) + '\n';
							output += 'Kd ' + (material.color.r)+' '+(material.color.g)+' '+(material.color.b) + '\n';
							output += 'Tr ' + (material.opacity) + '\n';//# some implementations use tr for transparency
							output += 'd ' + (material.opacity) + '\n';//# some implementations use d for transparency

						}

					}

				}

			} );

			return output;

		} )

};