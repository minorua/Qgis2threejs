Object Types for Polygon Layer
==============================

[Extruded](#Extruded) | [Overlay](#Overlay)

***
## <a name="Extruded"/> Extruded

Extruded polygon with specified height, color and transparency

<table><tr><td width="256">
<img src="images/polygon/Extruded.png">
</td><td>

<p><strong>Specific settings</strong>:</p>
<ul>
<li><p>Height</p>
<p>Numerical value.</p></li>
</ul>

<p><strong>three.js geometry class:</strong></p>
<p><a href="http://threejs.org/docs/#Reference/Extras.Geometries/ExtrudeGeometry">ExtrudeGeometry</a></p>

</td></tr></table>



## <a name="Overlay"/> Overlay

Overlay of main DEM with specified color, border color and transparency. If altitude mode of z coordinate is `Relative to DEM` or `+ "field name"`, each polygon is split into triangles using triangles of DEM, and is located at the relative height from triangle surface of DEM. You can add side to each polygon if you want.

<table><tr><td width="256">
<img src="images/polygon/Overlay.png">
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


Images were created with [GSI Tiles](http://portal.cyberjapan.jp/help/development/) (ort, dem), OpenStreetMap (© OpenStreetMap contributors, [License](http://www.openstreetmap.org/copyright)) and [National Land Numerical Information](http://nlftp.mlit.go.jp/ksj/) (Sediment Disaster Hazard Area. Provided by Okayama prefecture, Japan).


***
Back to [Export Settings](ExportSettings) | Qgis2threejs plugin version 1.3
