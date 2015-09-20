Object Types for Point Layer
============================

[Sphere](#sphere) | [Cylinder](#cylinder) | [Cone](#cone) | [Box](#box) | [Disk](#disk) | [Icon](#icon) | [JSON model](#json-model) | [COLLADA model](#collada-model)

***
## Sphere

Sphere with specified radius, color and transparency

<table><tr><td width="256">
<img src="images/point/Sphere.png">
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



## Cylinder

Cylinder with specified radius, height, color and transparency

<table><tr><td width="256">
<img src="images/point/Cylinder.png">
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



## Cone

Cone with specified radius, height, color and transparency

<table><tr><td width="256">
<img src="images/point/Cone.png">
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



## Box

Box with specified width, depth, height, color and transparency

<table><tr><td width="256">
<img src="images/point/Cube.png">
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



## Disk

Disk with specified radius, orientation, color and transparency

<table><tr><td width="256">
<img src="images/point/Disk.png">
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



## Icon

Image which always faces towards the camera

<table><tr><td width="256">
<img src="images/no_image.png">
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



## JSON model

<table><tr><td width="256">
<img src="images/no_image.png">
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



## COLLADA model

<table><tr><td width="256">
<img src="images/no_image.png">
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
