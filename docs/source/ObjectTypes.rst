Object Types
============

* `Point Layer <#point-layer>`__
* `Line Layer <#line-layer>`__
* `Polygon Layer <#polygon-layer>`__

--------------

.. _object-types-point-layer:

Point Layer
-----------

`Sphere <#sphere>`__ \| `Cylinder <#cylinder>`__ \| `Cone <#cone>`__ \|
`Box <#box>`__ \| `Disk <#disk>`__ \| `Icon <#icon>`__ \| `JSON
model <#json-model>`__ \| `COLLADA model <#collada-model>`__

Sphere
~~~~~~

Sphere with specified radius, color and transparency

.. raw:: html

   <table><tr><td width="256">

|image01|

.. raw:: html

   </td><td>

**Specific settings** :

* Radius
    Numerical value.

**Origin** :

    center of sphere

**three.js geometry class:**

    `SphereGeoemtry <http://threejs.org/docs/#Reference/Extras.Geometries/SphereGeometry>`__

.. raw:: html

   </td></tr></table>


Cylinder
~~~~~~~~

Cylinder with specified radius, height, color and transparency

.. raw:: html

   <table><tr><td width="256">

|image02|

.. raw:: html

   </td><td>

**Specific settings** :

* Radius
    Numerical value.
* Height
    Numerical value.

**Origin** :

    center of bottom (if height > 0)

**three.js geometry class:**

    `CylinderGeometry <http://threejs.org/docs/#Reference/Extras.Geometries/CylinderGeometry>`__

.. raw:: html

   </td></tr></table>


Cone
~~~~

Cone with specified radius, height, color and transparency

.. raw:: html

   <table><tr><td width="256">

|image03|

.. raw:: html

   </td><td>

**Specific settings** :

* Radius
    Numerical value.
* Height
    Numerical value.

**Origin** :

    center of bottom (if height > 0)

**three.js geometry class:**

    `CylinderGeometry <http://threejs.org/docs/#Reference/Extras.Geometries/CylinderGeometry>`__

.. raw:: html

   </td></tr></table>


Box
~~~

Box with specified width, depth, height, color and transparency

.. raw:: html

   <table><tr><td width="256">

|image04|

.. raw:: html

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

    `BoxGeometry <http://threejs.org/docs/#Reference/Extras.Geometries/BoxGeometry>`__

.. raw:: html

   </td></tr></table>


Disk
~~~~

Disk with specified radius, orientation, color and transparency

.. raw:: html

   <table><tr><td width="256">

|image05|

.. raw:: html

   </td><td>

**Specific settings** :

* Radius
    Numerical value.
* Dip
    In degrees. See `Strike and dip - Wikipedia <http://en.wikipedia.org/wiki/Strike_and_dip>`__.
* Dip direction
    In degrees.

**Origin** :

    center of disk

**three.js geometry class:**

    `CylinderGeometry <http://threejs.org/docs/#Reference/Extras.Geometries/CylinderGeometry>`__

.. raw:: html

   </td></tr></table>

Image was created with `GSI
Tiles <http://portal.cyberjapan.jp/help/development/>`__ (gazo1, dem).

Icon
~~~~

Image which always faces towards the camera

.. raw:: html

   <table><tr><td width="256">

|image06|

.. raw:: html

   </td><td>

**Specific settings** :

* Image file
    File path.
* Scale
    Numerical value.

**Origin** :

    center of image

**three.js object class:**

    `Sprite <http://threejs.org/docs/#Reference/Objects/Sprite>`__

.. raw:: html

   </td></tr></table>


JSON model
~~~~~~~~~~

.. raw:: html

   <table><tr><td width="256">

|image07|

.. raw:: html

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

.. raw:: html

   </td></tr></table>


COLLADA model
~~~~~~~~~~~~~

.. raw:: html

   <table><tr><td width="256">

|image08|

.. raw:: html

   </td><td>

**Specific settings** :

* COLLADA file
    File path (.dae). If the model has texture images, they need to be
    copied to the destination directory manually.
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

.. raw:: html

   </td></tr></table>

--------------

.. _object-types-line-layer:

Line Layer
----------

`Line <#line>`__ \| `Pipe <#pipe>`__ \| `Cone <#cone>`__ \|
`Box <#box>`__ \| `Profile <#profile>`__

Line
~~~~

.. raw:: html

   <table><tr><td width="256">

|image11|

.. raw:: html

   </td><td>

**Specific settings** :

    no specific settings

**three.js object class:**

    `Line <http://threejs.org/docs/#Reference/Objects/Line>`__

.. raw:: html

   </td></tr></table>

Image was created with `GSI
Tiles <http://portal.cyberjapan.jp/help/development/>`__ (ort, dem).

Pipe
~~~~

Places a cylinder to each line segment and a sphere to each joint.

.. raw:: html

   <table><tr><td width="256">

|image12|

.. raw:: html

   </td><td>

**Specific settings** :

* Radius
    Numerical value.

**three.js geometry classes:**

    `CylinderGeometry <http://threejs.org/docs/#Reference/Extras.Geometries/CylinderGeometry>`__
    and
    `SphereGeoemtry <http://threejs.org/docs/#Reference/Extras.Geometries/SphereGeometry>`__

.. raw:: html

   </td></tr></table>

Image was created with `GSI
Tiles <http://portal.cyberjapan.jp/help/development/>`__ (airphoto,
dem).

Cone
~~~~

Places a cone to each line segment. Heading of cone is forward
direction.

.. raw:: html

   <table><tr><td width="256">

|image13|

.. raw:: html

   </td><td>

**Specific settings** :

* Radius
    Numerical value.

**three.js geometry class:**

    `CylinderGeometry <http://threejs.org/docs/#Reference/Extras.Geometries/CylinderGeometry>`__

.. raw:: html

   </td></tr></table>

Image was created with `GSI
Tiles <http://portal.cyberjapan.jp/help/development/>`__ (ort, dem) and
`National Land Numerical Information <http://nlftp.mlit.go.jp/ksj/>`__
(Rivers. MILT of Japan).

Box
~~~

Places a box to each line segment.

.. raw:: html

   <table><tr><td width="256">

|image14|

.. raw:: html

   </td><td>

**Specific settings** :

* Width
    Numerical value.
* Height
    Numerical value.

**three.js geometry class:**

    `BoxGeometry <http://threejs.org/docs/#Reference/Extras.Geometries/BoxGeometry>`__
    and
    `Geometry <http://threejs.org/docs/#Reference/Core/Geometry>`__

.. raw:: html

   </td></tr></table>

Image was created with `GSI
Tiles <http://portal.cyberjapan.jp/help/development/>`__ (airphoto,
dem).

Profile
~~~~~~~

Makes a vertical plane between each line segment and zero elevation. If
altitude mode of z coordinate is ``Relative to DEM`` or
``+ "field name"``, each linestring is split into segments using
triangles of DEM and every upper edge is located at the relative height
from triangle surface of DEM.

.. raw:: html

   <table><tr><td width="256">

|image15|

.. raw:: html

   </td><td>

**Specific settings** :

* Lower Z
    Z coordinate of lower edge.

**three.js geometry class:**

    `PlaneGeometry <http://threejs.org/docs/#Reference/Extras.Geometries/PlaneGeometry>`__

.. raw:: html

   </td></tr></table>

Image was created with SRTM3 elevation data.

--------------

.. _object-types-polygon-layer:

Polygon Layer
-------------

`Extruded <#extruded>`__ \| `Overlay <#overlay>`__

Extruded
~~~~~~~~

Extruded polygon with specified height, color and transparency

.. raw:: html

   <table><tr><td width="256">

|image21|

.. raw:: html

   </td><td>

**Specific settings** :

* Height
    Numerical value.

**three.js geometry class:**

    `ExtrudeGeometry <http://threejs.org/docs/#Reference/Extras.Geometries/ExtrudeGeometry>`__

.. raw:: html

   </td></tr></table>

Image was created with `GSI
Tiles <http://portal.cyberjapan.jp/help/development/>`__ (ort, dem) and
OpenStreetMap (© OpenStreetMap contributors,
`License <http://www.openstreetmap.org/copyright>`__).

Overlay
~~~~~~~

Overlay of main DEM with specified color, border color and transparency.
If altitude mode of z coordinate is ``Relative to DEM`` or
``+ "field name"``, each polygon is split into triangles using triangles
of DEM, and is located at the relative height from triangle surface of
DEM. You can add side to each polygon if you want.

.. raw:: html

   <table><tr><td width="256">

|image22|

.. raw:: html

   </td><td>

**Specific settings** :

* Border color
* Side
    Check this option to add side to each polygon.
* Side color
* Side lower Z
    Z coordinate of lower edge of side.

**three.js classes:**

    `Geometry <http://threejs.org/docs/#Reference/Core/Geometry>`__,
    `Line <http://threejs.org/docs/#Reference/Objects/Line>`__
    and
    `PlaneGeometry <http://threejs.org/docs/#Reference/Extras.Geometries/PlaneGeometry>`__

.. raw:: html

   </td></tr></table>

Image was created with `GSI
Tiles <http://portal.cyberjapan.jp/help/development/>`__ (ort, dem) and
`National Land Numerical Information <http://nlftp.mlit.go.jp/ksj/>`__
(Sediment Disaster Hazard Area. Provided by Okayama prefecture, Japan).

.. |image01| image:: https://github.com/minorua/Qgis2threejs/wiki/images/point/Sphere.png
.. |image02| image:: https://github.com/minorua/Qgis2threejs/wiki/images/point/Cylinder.png
.. |image03| image:: https://github.com/minorua/Qgis2threejs/wiki/images/point/Cone.png
.. |image04| image:: https://github.com/minorua/Qgis2threejs/wiki/images/point/Cube.png
.. |image05| image:: https://github.com/minorua/Qgis2threejs/wiki/images/point/Disk.png
.. |image06| image:: https://github.com/minorua/Qgis2threejs/wiki/images/no_image.png
.. |image07| image:: https://github.com/minorua/Qgis2threejs/wiki/images/no_image.png
.. |image08| image:: https://github.com/minorua/Qgis2threejs/wiki/images/no_image.png
.. |image11| image:: https://github.com/minorua/Qgis2threejs/wiki/images/line/Line.png
.. |image12| image:: https://github.com/minorua/Qgis2threejs/wiki/images/line/Pipe.png
.. |image13| image:: https://github.com/minorua/Qgis2threejs/wiki/images/line/Cone.png
.. |image14| image:: https://github.com/minorua/Qgis2threejs/wiki/images/line/Box.png
.. |image15| image:: https://github.com/minorua/Qgis2threejs/wiki/images/line/Profile.png
.. |image21| image:: https://github.com/minorua/Qgis2threejs/wiki/images/polygon/Extruded.png
.. |image22| image:: https://github.com/minorua/Qgis2threejs/wiki/images/polygon/Overlay.png
