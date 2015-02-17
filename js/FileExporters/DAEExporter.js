/**
 * @author olivier dalang / https://github.com/olivierdalang
 * based on STLExport.js by mrdoob / http://mrdoob.com/
 */

 
THREE.DAEExporter = function () {};

THREE.DAEExporter.prototype = {

	constructor: THREE.DAEExporter,

	parse: ( function ( scene ) {

			var vector = new THREE.Vector3();
			var normalMatrixWorld = new THREE.Matrix3();


			/*************************************/
			/* HEADER                            */
			/*************************************/

			var output = '<?xml version="1.0" encoding="utf-8"?>'+ '\n';
			output +=  	 '<COLLADA xmlns="http://www.collada.org/2005/11/COLLADASchema" version="1.4.1">'+ '\n';
			output +=  	 ' <asset>'+ '\n';
			//output +=  	 ' 	<created>2005-11-14T02:16:38Z</created>'+ '\n';
			//output +=  	 ' 	<modified>2005-11-15T11:36:38Z</modified>'+ '\n';
			//output +=  	 ' 	<revision>1.0</revision>'+ '\n';
			output +=  	 ' </asset>'+ '\n';



			/*************************************/
			/* MATERIALS                         */
			/*************************************/


			var obj_i = 0;

			var materials_hexstrings = [];
			output +=  	 '<library_effects>'+ '\n';

			scene.traverse( function ( object ) {

				if ( object instanceof THREE.Mesh ) {

					var geometry = object.geometry;
					var matrixWorld = object.matrixWorld;

					if ( geometry instanceof THREE.Geometry ) {

						obj_i += 1;

						var material = object.material;
						var hexString = material.color.getHexString();

						if( materials_hexstrings.indexOf(hexString)==-1 ){

							materials_hexstrings.push(hexString);

							output += '	<effect id="effect_'+hexString+'">' + '\n';
							output += '		<profile_COMMON>' + '\n';
							output += '			<technique sid="phong1">' + '\n';
							output += '				<phong>' + '\n';
							//output += '					<emission>' + '\n';
							//output += '						<color>1.0 1.0 1.0 1.0</color>' + '\n';
							//output += '					</emission>' + '\n';
							//output += '					<ambient>' + '\n';
							//output += '						<color>1.0 1.0 1.0 1.0</color>' + '\n';
							//output += '					</ambient>' + '\n';
							output += '					<diffuse>' + '\n';
							output += '						<color>'+(material.color.r)+' '+(material.color.g)+' '+(material.color.b)+' 1.0</color>' + '\n';
							output += '					</diffuse>' + '\n';
							//output += '					<specular>' + '\n';
							//output += '						<color>1.0 1.0 1.0 1.0</color>' + '\n';
							//output += '					</specular>' + '\n';
							//output += '					<shininess>' + '\n';
							//output += '						<float>20.0</float>' + '\n';
							//output += '					</shininess>' + '\n';
							//output += '					<reflective>' + '\n';
							//output += '						<color>1.0 1.0 1.0 1.0</color>' + '\n';
							//output += '					</reflective>' + '\n';
							//output += '					<reflectivity>' + '\n';
							//output += '						<float>0.5</float>' + '\n';
							//output += '					</reflectivity>' + '\n';
							//output += '					<transparent>' + '\n';
							//output += '						<color>1.0 1.0 1.0 1.0</color>' + '\n';
							//output += '					</transparent>' + '\n';
							output += '					<transparency>' + '\n';
							output += '						<float>'+(material.opacity)+'</float>' + '\n';
							output += '					</transparency>' + '\n';
							output += '				</phong>' + '\n';
							output += '			</technique>' + '\n';
							output += '		</profile_COMMON>' + '\n';
							output += '	</effect>' + '\n';

						}

					}
				}
			} );

			output +=  	 '</library_effects>'+ '\n';



			var obj_i = 0;

			output +=  	 '<library_materials>'+ '\n';

			for (var i = 0; i < materials_hexstrings.length; i++) {
				var hexString = materials_hexstrings[i]
				output += '		<material id="material_'+hexString+'">' + '\n';
				output += '			<instance_effect url="#effect_'+(hexString)+'"/>' + '\n';
				output += '		</material> ' + '\n';
			};

			output +=  	 '</library_materials>'+ '\n';



			/*************************************/
			/* GEOMETRIES                        */
			/*************************************/


			var obj_i = 0;
			output +=  	 '<library_geometries>'+ '\n';

			scene.traverse( function ( object ) {

				if ( object instanceof THREE.Mesh ) {

					var geometry = object.geometry;
					var matrixWorld = object.matrixWorld;

					if ( geometry instanceof THREE.Geometry ) {

						obj_i += 1;

						var vertices = geometry.vertices;
						var faces = geometry.faces;

						output += '	<geometry id="geometry_'+(obj_i)+'" name="object">' + '\n';
						output += '		<mesh>' + '\n';

						output += '			<source id="position_'+(obj_i)+'">' + '\n';
						output += '				<float_array id="position_array_'+(obj_i)+'" count="'+(vertices.length*3)+'">' + '\n';
						
						for ( var i = 0, l = vertices.length; i < l; i ++ ) {
							var vertex = vertices[ i ];
							vector.copy( vertex ).applyMatrix4( matrixWorld );
							output += '			' + vector.x + ' ' + vector.z + ' ' + vector.y + '\n';
						}
						output += '				</float_array>' + '\n';
						output += '				<technique_common>' + '\n';
						output += '					<accessor source="#position_array_'+(obj_i)+'" count="'+(faces.length*3)+'" stride="3">' + '\n';
						output += '						<param name="X" type="float" />' + '\n';
						output += '						<param name="Y" type="float" />' + '\n';
						output += '						<param name="Z" type="float" />' + '\n';
						output += '					</accessor>' + '\n';
						output += '				</technique_common>' + '\n';
						output += '			</source>' + '\n';



						output += '			<source id="normal_'+(obj_i)+'">' + '\n';
						output += '				<float_array id="normal_array_'+(obj_i)+'" count="'+(faces.length*3)+'">' + '\n';
						
						normalMatrixWorld.getNormalMatrix( matrixWorld );
						for ( var i = 0, l = faces.length; i < l; i ++ ) {
							var face = faces[ i ];

							vector.copy( face.normal ).applyMatrix3( normalMatrixWorld ).normalize();
							output += '			' + vector.x + ' ' + vector.z + ' ' + vector.y + '\n';
						}
						output += '				</float_array>' + '\n';
						output += '				<technique_common>' + '\n';
						output += '					<accessor source="#normal_array_'+(obj_i)+'" count="'+(faces.length)+'" stride="3">' + '\n';
						output += '						<param name="X" type="float" />' + '\n';
						output += '						<param name="Y" type="float" />' + '\n';
						output += '						<param name="Z" type="float" />' + '\n';
						output += '					</accessor>' + '\n';
						output += '				</technique_common>' + '\n';
						output += '			</source>' + '\n';

						output += '			<vertices id="vertex_'+(obj_i)+'" count="'+(faces.length*3)+'">' + '\n';
						output += '				<input semantic="POSITION" source="#position_'+(obj_i)+'" offset="0"/> ' + '\n';
						output += '			</vertices>' + '\n';

						output += '			<triangles count="'+(faces.length)+'" material="MATERIAL">' + '\n';
						output += '				<input semantic="VERTEX" source="#vertex_'+(obj_i)+'" offset="0"/> ' + '\n';
						output += '				<input semantic="NORMAL" source="#normal_'+(obj_i)+'" offset="1"/> ' + '\n';
						output += '				<p> ' + '\n';

						for ( var i = 0, l = faces.length; i < l; i ++ ) {
							var face = faces[ i ];
							var indices = [ face.a, face.b, face.c ];
							output += '			' + face.c + ' ' + i + ' ' + face.b + ' ' + i + ' ' + face.a + ' ' + i + '\n';
						}

						output += '				</p> ' + '\n';
						output += '			</triangles>' + '\n';

						output += '		</mesh>' + '\n';
						output += '	</geometry>' + '\n';

					}

				}

			} );

			output +=  	 '</library_geometries>'+ '\n';




			/*************************************/
			/* SCENE                             */
			/*************************************/


			var obj_i = 0;
			output +=  	 '<library_visual_scenes>'+ '\n';
			output +=  	 '	<visual_scene id="DefaultScene">'+ '\n';

			scene.traverse( function ( object ) {

				if ( object instanceof THREE.Mesh ) {

					var geometry = object.geometry;

					if ( geometry instanceof THREE.Geometry ) {

						obj_i += 1;

						var material = object.material;

						output +=  	 '		<node id="obj_'+(obj_i)+'" name="Object">'+ '\n';
						output +=  	 '			<translate> 0 0 0</translate>'+ '\n';
						output +=  	 ' 			<rotate> 0 0 1 0</rotate>'+ '\n';
						output +=  	 ' 			<rotate> 0 1 0 0</rotate>'+ '\n';
						output +=  	 ' 			<rotate> 1 0 0 0</rotate>'+ '\n';
						output +=  	 ' 			<scale> 1 1 1</scale>'+ '\n';

						output +=  	 '			<instance_geometry url="#geometry_'+(obj_i)+'">'+ '\n';
						output +=  	 '				<bind_material>'+ '\n';
						output +=  	 '					<technique_common>'+ '\n';
						output +=  	 '						<instance_material symbol="MATERIAL" target="#material_'+(material.color.getHexString())+'"/>'+ '\n';
						output +=  	 '					</technique_common>'+ '\n';
						output +=  	 '				</bind_material>'+ '\n';
						output +=  	 '			</instance_geometry>'+ '\n';

						output +=  	 ' 		</node>'+ '\n';

					}
				}

			} );

			output +=  	 ' </visual_scene>'+ '\n';
			output +=  	 '</library_visual_scenes>'+ '\n';


			output +=  	 '<scene>'+ '\n';
			output +=  	 ' <instance_visual_scene url="#DefaultScene"/>'+ '\n';
			output +=  	 '</scene>'+ '\n';
			output +=  	 '</COLLADA>';				

			return output;

		} )

};