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
![image01](https://github.com/minorua/Qgis2threejs/wiki/images/point/Sphere.png)
</td><td>

**Specific settings** :


* Radius  
  Numerical value.


**Origin** :

center of sphere

**three.js geometry class:**
[SphereGeoemtry](http://threejs.org/docs/#Reference/Extras.Geometries/SphereGeometry)

</td></tr></table>



### Cylinder

Cylinder with specified radius, height, color and transparency

<table><tr><td width="256">
![image02](https://github.com/minorua/Qgis2threejs/wiki/images/point/Cylinder.png)
</td><td>

**Specific settings** :


* Radius  
  Numerical value.
* Height  
  Numerical value.


**Origin** :

center of bottom (if height > 0)

**three.js geometry class:**
[CylinderGeometry](http://threejs.org/docs/#Reference/Extras.Geometries/CylinderGeometry)

</td></tr></table>



### Cone

Cone with specified radius, height, color and transparency

<table><tr><td width="256">
![image03](https://github.com/minorua/Qgis2threejs/wiki/images/point/Cone.png)
</td><td>

**Specific settings** :



* Radius  
  Numerical value.
* Height  
  Numerical value.


**Origin** :

center of bottom (if height > 0)

**three.js geometry class:**
[CylinderGeometry](http://threejs.org/docs/#Reference/Extras.Geometries/CylinderGeometry)

</td></tr></table>



### Box

Box with specified width, depth, height, color and transparency

<table><tr><td width="256">
![image04](https://github.com/minorua/Qgis2threejs/wiki/images/point/Cube.png)
</td><td>

**Specific settings** :


* Width  
  Numerical value.
* Depth  
  Numerical value.
* Height  
  Numerical value.


**Origin** :

center of bottom (if height > 0)

**three.js geometry class:**
[BoxGeometry](http://threejs.org/docs/#Reference/Extras.Geometries/BoxGeometry)

</td></tr></table>



### Disk

Disk with specified radius, orientation, color and transparency

<table><tr><td width="256">
![image05](https://github.com/minorua/Qgis2threejs/wiki/images/point/Disk.png)
</td><td>

**Specific settings** :


* Radius  
  Numerical value.
* Dip  
  In degrees. See [Strike and dip - Wikipedia](http://en.wikipedia.org/wiki/Strike_and_dip).
* Dip direction  
  In degrees.


**Origin** :

center of disk  

**three.js geometry class:**
[CylinderGeometry](http://threejs.org/docs/#Reference/Extras.Geometries/CylinderGeometry)

</td></tr></table>

Image was created with [GSI Tiles](http://portal.cyberjapan.jp/help/development/) (gazo1, dem).



### Icon

Image which always faces towards the camera

<table><tr><td width="256">
![image06](https://github.com/minorua/Qgis2threejs/wiki/images/no_image.png)
</td><td>

**Specific settings** :


* Image file  
  File path.
* Scale  
  Numerical value.


**Origin** :

center of image

**three.js object class:**
[Sprite](http://threejs.org/docs/#Reference/Objects/Sprite)

</td></tr></table>



### JSON model

<table><tr><td width="256">
![image07](https://github.com/minorua/Qgis2threejs/wiki/images/no_image.png)
</td><td>

**Specific settings** :


* JSON file  
  File path.
* Scale  
  Numerical value.
* Rotation (x)  
  In degrees.
* Rotation (y)  
  In degrees.
* Rotation (z)  
  In degrees.


**Origin** :

origin of model

</td></tr></table>



### COLLADA model

<table><tr><td width="256">
![image08](https://github.com/minorua/Qgis2threejs/wiki/images/no_image.png)
</td><td>

**Specific settings** :


* COLLADA file  
  File path (.dae). If the model has texture images, they need to be copied to the destination directory manually.
* Scale  
  Numerical value.
* Rotation (x)  
  In degrees.
* Rotation (y)  
  In degrees.
* Rotation (z)  
  In degrees.


**Origin** :

origin of model

</td></tr></table>

***
## Line Layer

[Line](#line) | [Pipe](#pipe) | [Cone](#cone) | [Box](#box) | [Profile](#profile)

### Line

<table><tr><td width="256">
![image11](https://github.com/minorua/Qgis2threejs/wiki/images/line/Line.png)
</td><td>

**Specific settings** :

no specific settings

**three.js object class:**
[Line](http://threejs.org/docs/#Reference/Objects/Line)

</td></tr></table>

Image was created with [GSI Tiles](http://portal.cyberjapan.jp/help/development/) (ort, dem).


### Pipe

Places a cylinder to each line segment and a sphere to each joint.

<table><tr><td width="256">
![image12](https://github.com/minorua/Qgis2threejs/wiki/images/line/Pipe.png)
</td><td>

**Specific settings** :


* Radius  
  Numerical value.


**three.js geometry classes:**
[CylinderGeometry](http://threejs.org/docs/#Reference/Extras.Geometries/CylinderGeometry) and
  [SphereGeoemtry](http://threejs.org/docs/#Reference/Extras.Geometries/SphereGeometry)

</td></tr></table>

Image was created with [GSI Tiles](http://portal.cyberjapan.jp/help/development/) (airphoto, dem).



### Cone

Places a cone to each line segment. Heading of cone is forward direction.

<table><tr><td width="256">
![image13](https://github.com/minorua/Qgis2threejs/wiki/images/line/Cone.png)
</td><td>

**Specific settings** :


* Radius  
  Numerical value.


**three.js geometry class:**
[CylinderGeometry](http://threejs.org/docs/#Reference/Extras.Geometries/CylinderGeometry)

</td></tr></table>

Image was created with [GSI Tiles](http://portal.cyberjapan.jp/help/development/) (ort, dem) and [National Land Numerical Information](http://nlftp.mlit.go.jp/ksj/) (Rivers. MILT of Japan).



### Box

Places a box to each line segment.

<table><tr><td width="256">
![image14](https://github.com/minorua/Qgis2threejs/wiki/images/line/Box.png)
</td><td>

**Specific settings** :


* Width  
  Numerical value.
* Height  
  Numerical value.


**three.js geometry class:**
[BoxGeometry](http://threejs.org/docs/#Reference/Extras.Geometries/BoxGeometry) and
[Geometry](http://threejs.org/docs/#Reference/Core/Geometry)

</td></tr></table>

Image was created with [GSI Tiles](http://portal.cyberjapan.jp/help/development/) (airphoto, dem).



### Profile

Makes a vertical plane between each line segment and zero elevation. If altitude mode of z coordinate is `Relative to DEM` or `+ "field name"`, each linestring is split into segments using triangles of DEM and every upper edge is located at the relative height from triangle surface of DEM.

<table><tr><td width="256">
![image15](https://github.com/minorua/Qgis2threejs/wiki/images/line/Profile.png)
</td><td>

**Specific settings** :


* Lower Z  
  Z coordinate of lower edge.


**three.js geometry class:**
[PlaneGeometry](http://threejs.org/docs/#Reference/Extras.Geometries/PlaneGeometry)

</td></tr></table>

Image was created with SRTM3 elevation data.


***
## Polygon Layer

[Extruded](#extruded) | [Overlay](#overlay)

### Extruded

Extruded polygon with specified height, color and transparency

<table><tr><td width="256">
![image21](https://github.com/minorua/Qgis2threejs/wiki/images/polygon/Extruded.png)
</td><td>

**Specific settings** :


* Height  
  Numerical value.


**three.js geometry class:**
[ExtrudeGeometry](http://threejs.org/docs/#Reference/Extras.Geometries/ExtrudeGeometry)

</td></tr></table>

Image was created with [GSI Tiles](http://portal.cyberjapan.jp/help/development/) (ort, dem) and OpenStreetMap (© OpenStreetMap contributors, [License](http://www.openstreetmap.org/copyright)).



### Overlay

Overlay of main DEM with specified color, border color and transparency. If altitude mode of z coordinate is `Relative to DEM` or `+ "field name"`, each polygon is split into triangles using triangles of DEM, and is located at the relative height from triangle surface of DEM. You can add side to each polygon if you want.

<table><tr><td width="256">
![image22](https://github.com/minorua/Qgis2threejs/wiki/images/polygon/Overlay.png)
</td><td>

**Specific settings** :


* Border color  
* Side  
  Check this option to add side to each polygon.
* Side color  
* Side lower Z  
  Z coordinate of lower edge of side.


**three.js classes:**
[Geometry](http://threejs.org/docs/#Reference/Core/Geometry),
[Line](http://threejs.org/docs/#Reference/Objects/Line) and 
[PlaneGeometry](http://threejs.org/docs/#Reference/Extras.Geometries/PlaneGeometry)


</td></tr></table>

Image was created with [GSI Tiles](http://portal.cyberjapan.jp/help/development/) (ort, dem) and [National Land Numerical Information](http://nlftp.mlit.go.jp/ksj/) (Sediment Disaster Hazard Area. Provided by Okayama prefecture, Japan).
