Object Types for Line Layer
============================

[Line](#Line) | [Pipe](#Pipe) | [Cone](#Cone) | [Box](#Box) | [Profile](#Profile)

***
## <a name="Line"/> Line

<table><tr><td width="256">
<img src="images/line/Line.png">
</td><td>

<p><strong>Specific settings</strong>:</p>
<p>no specific settings</p>

<p><strong>three.js object class:</strong></p>
<p><a href="http://threejs.org/docs/#Reference/Objects/Line">Line</a></p>

</td></tr></table>



## <a name="Pipe"/> Pipe

Places a cylinder to each line segment and a sphere to each joint.

<table><tr><td width="256">
<img src="images/line/Pipe.png">
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



## <a name="Cone"/> Cone

Places a cone to each line segment. Heading of cone is forward direction.

<table><tr><td width="256">
<img src="images/line/Cone.png">
</td><td>

<p><strong>Specific settings</strong>:</p>
<ul>
<li><p>Radius</p>
<p>Numerical value.</p></li>
</ul>

<p><strong>three.js geometry class:</strong></p>
<p><a href="http://threejs.org/docs/#Reference/Extras.Geometries/CylinderGeometry">CylinderGeometry</a></p>

</td></tr></table>



## <a name="Box"/> Box

Places a box to each line segment.

<table><tr><td width="256">
<img src="images/line/Box.png">
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



## <a name="Profile"/> Profile

Makes a vertical plane between each line segment and zero elevation. If altitude mode of z coordinate is `Relative to DEM` or `+ "field name"`, each linestring is split into segments using triangles of DEM and every upper edge is located at the relative height from triangle surface of DEM.

<table><tr><td width="256">
<img src="images/line/Profile.png">
</td><td>

<p><strong>Specific settings</strong>:</p>
<ul>
<li><p>Lower Z</p>
<p>Z coordinate of lower edge.</p></li>
</ul>

<p><strong>three.js geometry class:</strong></p>
<p><a href="http://threejs.org/docs/#Reference/Extras.Geometries/PlaneGeometry">PlaneGeometry</a></p>

</td></tr></table>


Images were created with [GSI Tiles](http://portal.cyberjapan.jp/help/development/) (ort, airphoto, dem) and [National Land Numerical Information](http://nlftp.mlit.go.jp/ksj/) (Rivers. MILT of Japan).


***
Back to [Export Settings](ExportSettings) | Qgis2threejs plugin version 1.3
