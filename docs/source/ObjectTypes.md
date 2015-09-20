Object Types
============

* [Point Layer](#point-layer)
* [Line Layer](#line-layer)
* [Polygon Layer](#polygon-layer)

***
## Point Layer

[Sphere](#sphere) | [Cylinder](#cylinder) | [Cone](#cone) | [Box](#box) | [Disk](#disk) | [Icon](#icon) | [JSON model](#json-model) | [COLLADA model](#collada-model)

### Sphere

Sphere with specified radius, color and transparency

<table><tr><td width="256">
<img src="https://github.com/minorua/Qgis2threejs/wiki/images/point/Sphere.png">
</td><td>

<p><strong>Specific settings</strong>:</p>
<ul>
<li><p>Radius</p>
<p>Numerical value.</p></li>
</ul>

<p><strong>Origin</strong>:</p>
<p>center of sphere</p>

<p><strong>three.js geometry class:</strong></p>
<p><a href="http://threejs.org/docs/#Reference/Extras.Geometries/SphereGeometry">SphereGeoemtry</a></p>

</td></tr></table>



### Cylinder

Cylinder with specified radius, height, color and transparency

<table><tr><td width="256">
<img src="https://github.com/minorua/Qgis2threejs/wiki/images/point/Cylinder.png">
</td><td>

<p><strong>Specific settings</strong>:</p>
<ul>
<li><p>Radius</p>
<p>Numerical value.</p></li>
<li><p>Height</p>
<p>Numerical value.</p></li>
</ul>

<p><strong>Origin</strong>:</p>
<p>center of bottom (if height > 0)</p>

<p><strong>three.js geometry class:</strong></p>
<p><a href="http://threejs.org/docs/#Reference/Extras.Geometries/CylinderGeometry">CylinderGeometry</a></p>

</td></tr></table>



### Cone

Cone with specified radius, height, color and transparency

<table><tr><td width="256">
<img src="https://github.com/minorua/Qgis2threejs/wiki/images/point/Cone.png">
</td><td>

<p><strong>Specific settings</strong>:</p>

<ul>
<li><p>Radius</p>
<p>Numerical value.</p></li>
<li><p>Height</p>
<p>Numerical value.</p></li>
</ul>

<p><strong>Origin</strong>:</p>
<p>center of bottom (if height > 0)</p>

<p><strong>three.js geometry class:</strong></p>
<p><a href="http://threejs.org/docs/#Reference/Extras.Geometries/CylinderGeometry">CylinderGeometry</a></p>

</td></tr></table>



### Box

Box with specified width, depth, height, color and transparency

<table><tr><td width="256">
<img src="https://github.com/minorua/Qgis2threejs/wiki/images/point/Cube.png">
</td><td>

<p><strong>Specific settings</strong>:</p>
<ul>
<li><p>Width</p>
<p>Numerical value.</p></li>
<li><p>Depth</p>
<p>Numerical value.</p></li>
<li><p>Height</p>
<p>Numerical value.</p></li>
</ul>

<p><strong>Origin</strong>:</p>
<p>center of bottom (if height > 0)</p>

<p><strong>three.js geometry class:</strong></p>
<p><a href="http://threejs.org/docs/#Reference/Extras.Geometries/BoxGeometry">BoxGeometry</a></p>

</td></tr></table>



### Disk

Disk with specified radius, orientation, color and transparency

<table><tr><td width="256">
<img src="https://github.com/minorua/Qgis2threejs/wiki/images/point/Disk.png">
</td><td>

<p><strong>Specific settings</strong>:</p>
<ul>
<li><p>Radius</p>
<p>Numerical value.</p></li>
<li><p>Dip</p>
<p>In degrees. See <a href="http://en.wikipedia.org/wiki/Strike_and_dip">Strike and dip - Wikipedia</a>.</p></li>
<li><p>Dip direction</p>
<p>In degrees.</p></li>
</ul>

<p><strong>Origin</strong>:</p>
<p>center of disk  </p>

<p><strong>three.js geometry class:</strong></p>
<p><a href="http://threejs.org/docs/#Reference/Extras.Geometries/CylinderGeometry">CylinderGeometry</a></p>

</td></tr></table>

Image was created with [GSI Tiles](http://portal.cyberjapan.jp/help/development/) (gazo1, dem).



### Icon

Image which always faces towards the camera

<table><tr><td width="256">
<img src="https://github.com/minorua/Qgis2threejs/wiki/images/no_image.png">
</td><td>

<p><strong>Specific settings</strong>:</p>
<ul>
<li><p>Image file</p>
<p>File path.</p></li>
<li><p>Scale</p>
<p>Numerical value.</p></li>
</ul>

<p><strong>Origin</strong>:</p>
<p>center of image</p>

<p><strong>three.js object class:</strong></p>
<p><a href="http://threejs.org/docs/#Reference/Objects/Sprite">Sprite</a></p>

</td></tr></table>



### JSON model

<table><tr><td width="256">
<img src="https://github.com/minorua/Qgis2threejs/wiki/images/no_image.png">
</td><td>

<p><strong>Specific settings</strong>:</p>
<ul>
<li><p>JSON file</p>
<p>File path.</p></li>
<li><p>Scale</p>
<p>Numerical value.</p></li>
<li><p>Rotation (x)</p>
<p>In degrees.</p></li>
<li><p>Rotation (y)</p>
<p>In degrees.</p></li>
<li><p>Rotation (z)</p>
<p>In degrees.</p></li>
</ul>

<p><strong>Origin</strong>:</p>
<p>origin of model</p>

</td></tr></table>



### COLLADA model

<table><tr><td width="256">
<img src="https://github.com/minorua/Qgis2threejs/wiki/images/no_image.png">
</td><td>

<p><strong>Specific settings</strong>:</p>
<ul>
<li><p>COLLADA file</p>
<p>File path (.dae). If the model has texture images, they need to be copied to the destination directory manually.</p></li>
<li><p>Scale</p>
<p>Numerical value.</p></li>
<li><p>Rotation (x)</p>
<p>In degrees.</p></li>
<li><p>Rotation (y)</p>
<p>In degrees.</p></li>
<li><p>Rotation (z)</p>
<p>In degrees.</p></li>
</ul>

<p><strong>Origin</strong>:</p>
<p>origin of model</p>

</td></tr></table>

***
## Line Layer

[Line](#line) | [Pipe](#pipe) | [Cone](#cone) | [Box](#box) | [Profile](#profile)

### Line

<table><tr><td width="256">
<img src="https://github.com/minorua/Qgis2threejs/wiki/images/line/Line.png">
</td><td>

<p><strong>Specific settings</strong>:</p>
<p>no specific settings</p>

<p><strong>three.js object class:</strong></p>
<p><a href="http://threejs.org/docs/#Reference/Objects/Line">Line</a></p>

</td></tr></table>

Image was created with [GSI Tiles](http://portal.cyberjapan.jp/help/development/) (ort, dem).


### Pipe

Places a cylinder to each line segment and a sphere to each joint.

<table><tr><td width="256">
<img src="https://github.com/minorua/Qgis2threejs/wiki/images/line/Pipe.png">
</td><td>

<p><strong>Specific settings</strong>:</p>
<ul>
<li><p>Radius</p>
<p>Numerical value.</p></li>
</ul>

<p><strong>three.js geometry classes:</strong></p>
<p><a href="http://threejs.org/docs/#Reference/Extras.Geometries/CylinderGeometry">CylinderGeometry</a> and
  <a href="http://threejs.org/docs/#Reference/Extras.Geometries/SphereGeometry">SphereGeoemtry</a></p>

</td></tr></table>

Image was created with [GSI Tiles](http://portal.cyberjapan.jp/help/development/) (airphoto, dem).



### Cone

Places a cone to each line segment. Heading of cone is forward direction.

<table><tr><td width="256">
<img src="https://github.com/minorua/Qgis2threejs/wiki/images/line/Cone.png">
</td><td>

<p><strong>Specific settings</strong>:</p>
<ul>
<li><p>Radius</p>
<p>Numerical value.</p></li>
</ul>

<p><strong>three.js geometry class:</strong></p>
<p><a href="http://threejs.org/docs/#Reference/Extras.Geometries/CylinderGeometry">CylinderGeometry</a></p>

</td></tr></table>

Image was created with [GSI Tiles](http://portal.cyberjapan.jp/help/development/) (ort, dem) and [National Land Numerical Information](http://nlftp.mlit.go.jp/ksj/) (Rivers. MILT of Japan).



### Box

Places a box to each line segment.

<table><tr><td width="256">
<img src="https://github.com/minorua/Qgis2threejs/wiki/images/line/Box.png">
</td><td>

<p><strong>Specific settings</strong>:</p>
<ul>
<li><p>Width</p>
<p>Numerical value.</p></li>
<li><p>Height</p>
<p>Numerical value.</p></li>
</ul>

<p><strong>three.js geometry class:</strong></p>
<p><a href="http://threejs.org/docs/#Reference/Extras.Geometries/BoxGeometry">BoxGeometry</a> and
<a href="http://threejs.org/docs/#Reference/Core/Geometry">Geometry</a></p>

</td></tr></table>

Image was created with [GSI Tiles](http://portal.cyberjapan.jp/help/development/) (airphoto, dem).



### Profile

Makes a vertical plane between each line segment and zero elevation. If altitude mode of z coordinate is `Relative to DEM` or `+ "field name"`, each linestring is split into segments using triangles of DEM and every upper edge is located at the relative height from triangle surface of DEM.

<table><tr><td width="256">
<img src="https://github.com/minorua/Qgis2threejs/wiki/images/line/Profile.png">
</td><td>

<p><strong>Specific settings</strong>:</p>
<ul>
<li><p>Lower Z</p>
<p>Z coordinate of lower edge.</p></li>
</ul>

<p><strong>three.js geometry class:</strong></p>
<p><a href="http://threejs.org/docs/#Reference/Extras.Geometries/PlaneGeometry">PlaneGeometry</a></p>

</td></tr></table>

Image was created with SRTM3 elevation data.


***
## Polygon Layer

[Extruded](#extruded) | [Overlay](#overlay)

### Extruded

Extruded polygon with specified height, color and transparency

<table><tr><td width="256">
<img src="https://github.com/minorua/Qgis2threejs/wiki/images/polygon/Extruded.png">
</td><td>

<p><strong>Specific settings</strong>:</p>
<ul>
<li><p>Height</p>
<p>Numerical value.</p></li>
</ul>

<p><strong>three.js geometry class:</strong></p>
<p><a href="http://threejs.org/docs/#Reference/Extras.Geometries/ExtrudeGeometry">ExtrudeGeometry</a></p>

</td></tr></table>

Image was created with [GSI Tiles](http://portal.cyberjapan.jp/help/development/) (ort, dem) and OpenStreetMap (© OpenStreetMap contributors, [License](http://www.openstreetmap.org/copyright)).



### Overlay

Overlay of main DEM with specified color, border color and transparency. If altitude mode of z coordinate is `Relative to DEM` or `+ "field name"`, each polygon is split into triangles using triangles of DEM, and is located at the relative height from triangle surface of DEM. You can add side to each polygon if you want.

<table><tr><td width="256">
<img src="https://github.com/minorua/Qgis2threejs/wiki/images/polygon/Overlay.png">
</td><td>

<p><strong>Specific settings</strong>:</p>
<ul>
<li>Border color</li>
<li><p>Side</p>
<p>Check this option to add side to each polygon.</p></li>
<li><p>Side color</p></li>
<li><p>Side lower Z</p>
<p>Z coordinate of lower edge of side.</p></li>
</ul>

<p><strong>three.js classes:</strong></p>
<p><a href="http://threejs.org/docs/#Reference/Core/Geometry">Geometry</a>,
<a href="http://threejs.org/docs/#Reference/Objects/Line">Line</a> and 
<a href="http://threejs.org/docs/#Reference/Extras.Geometries/PlaneGeometry">PlaneGeometry</a>
</p>

</td></tr></table>

Image was created with [GSI Tiles](http://portal.cyberjapan.jp/help/development/) (ort, dem) and [National Land Numerical Information](http://nlftp.mlit.go.jp/ksj/) (Sediment Disaster Hazard Area. Provided by Okayama prefecture, Japan).
