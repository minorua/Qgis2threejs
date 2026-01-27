Object Types
============

.. contents::
   :depth: 1
   :local:

--------------

.. _object-types-point-layer:

Point Layer
-----------

`Sphere <#sphere>`__ \| `Cylinder <#cylinder>`__ \| `Cone <#cone>`__ \|
`Box <#box>`__ \| `Disk <#disk>`__ \| `Plane <#plane>`__ \| `Point <#point>`__ \|
`Billboard <#billboard>`__ \| `Model File <#model-file>`__


.. index:: Sphere

Sphere
~~~~~~

Sphere with specified radius, color and opacity

.. raw:: html

   <table><tr><td width="256">

.. image:: ./images/point/Sphere.jpg

.. raw:: html

   </td><td>

**Specific settings** :

* Radius
    Numerical value.

**Origin** :

    center of sphere

**three.js geometry class:**

    `SphereBufferGeoemtry <https://threejs.org/docs/#api/en/geometries/SphereBufferGeometry>`__

.. raw:: html

   </td></tr></table>


.. index:: Cylinder

Cylinder
~~~~~~~~

Cylinder with specified radius, height, color and opacity

.. raw:: html

   <table><tr><td width="256">

.. image:: ./images/point/Cylinder.jpg

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

    `CylinderBufferGeometry <https://threejs.org/docs/#api/en/geometries/CylinderBufferGeometry>`__

.. raw:: html

   </td></tr></table>


.. index:: Cone (Point Layer)

Cone
~~~~

Cone with specified radius, height, color and opacity

.. raw:: html

   <table><tr><td width="256">

.. image:: ./images/point/Cone.jpg

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

    `CylinderBufferGeometry <https://threejs.org/docs/#api/en/geometries/CylinderBufferGeometry>`__

.. raw:: html

   </td></tr></table>


.. index:: Box (Point Layer)

Box
~~~

Box with specified width, depth, height, color and opacity

.. raw:: html

   <table><tr><td width="256">

.. image:: ./images/point/Box.jpg

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

    `BoxBufferGeometry <https://threejs.org/docs/#api/en/geometries/BoxBufferGeometry>`__

.. raw:: html

   </td></tr></table>


.. index:: Disk

Disk
~~~~

Disk with specified radius, orientation, color and opacity

.. raw:: html

   <table><tr><td width="256">

.. image:: ./images/point/Disk.jpg

.. raw:: html

   </td><td>

**Specific settings** :

* Radius
    Numerical value.
* Dip
    Numerical value in degrees. See `Strike and dip - Wikipedia <https://en.wikipedia.org/wiki/Strike_and_dip>`__.
* Dip direction
    Numerical value in degrees.

**Origin** :

    center of disk

**three.js geometry class:**

    `CircleBufferGeometry <https://threejs.org/docs/#api/en/geometries/CircleBufferGeometry>`__

.. raw:: html

   </td></tr></table>


.. index:: Plane

Plane
~~~~~

Plane with specified length, width, orientation, color and opacity

.. raw:: html

   <table><tr><td width="256">

.. image:: ./images/no_image.png

.. raw:: html

   </td><td>

**Specific settings** :

* Width
    Numerical value.
* Length
    Numerical value.
* Dip
    Numerical value in degrees. See `Strike and dip - Wikipedia <https://en.wikipedia.org/wiki/Strike_and_dip>`__.
* Dip direction
    Numerical value in degrees.

**Origin** :

    center of plane

**three.js geometry class:**

    `PlaneBufferGeometry <https://threejs.org/docs/#api/en/geometries/PlaneBufferGeometry>`__

.. raw:: html

   </td></tr></table>


.. index:: Point

Point
~~~~~


.. raw:: html

   <table><tr><td width="256">

.. image:: ./images/no_image.png

.. raw:: html

   </td><td>

**Specific settings** :

* Radius
    Numerical value.

**Origin** :

    center of sprite

**three.js geometry class:**

    `SphereBufferGeoemtry <https://threejs.org/docs/#api/en/geometries/SphereBufferGeometry>`__

.. raw:: html

   </td></tr></table>


.. index:: Billboard

Billboard
~~~~~~~~~

Image which always faces towards the camera. When an image file on local file system is specified,
the image file is copied to the export destination. When an image file on a web server is
specified, the model file is not copied.

.. raw:: html

   <table><tr><td width="256">

.. image:: ./images/no_image.png

.. raw:: html

   </td><td>

**Specific settings** :

* Image file
    File path or URL.

* Scale
    Numerical value.

**Origin** :

    center of sprite

**three.js object class:**

    `Sprite <https://threejs.org/docs/#api/en/objects/Sprite>`__

.. raw:: html

   </td></tr></table>


.. index:: Model-File

Model File
~~~~~~~~~~

Load 3D model from supported format model file. ``COLLADA (*.dae)`` and ``glTF (*.gltf, *.glb)`` are supported.
When a model file on local file system is specified, the model file is copied to the export destination.
You need to copy the relevant files such as texture image after export. When a model file URL is
specified, the model file is not copied.

.. raw:: html

   <table><tr><td width="256">

.. image:: ./images/no_image.png

.. raw:: html

   </td><td>

**Specific settings** :

* Model file
    File path or URL.

* Scale
    Numerical value.

* Rotation (x)
    Numerical value in degrees.

* Rotation (y)
    Numerical value in degrees.

* Rotation (z)
    Numerical value in degrees.

* Rotation Order
    The options are XYZ, YZX, ZXY, XZY, YXZ and ZYX. See `Euler - three.js docs <https://threejs.org/docs/#api/en/math/Euler.order>`__.

**Origin** :

    origin of model

.. raw:: html

   </td></tr></table>


--------------

.. _object-types-line-layer:

Line Layer
----------

`Line <#line>`__ \| `Pipe <#pipe>`__ \| `Cone <#cone>`__ \|
`Box <#box>`__ \| `Wall <#wall>`__


.. index:: Line

Line
~~~~

.. raw:: html

   <table><tr><td width="256">

.. image:: ./images/line/Line.png

.. raw:: html

   </td><td>

**Specific settings** :

    no specific settings

**three.js object class:**

    `Line <https://threejs.org/docs/#api/en/objects/Line>`__

.. raw:: html

   </td></tr></table>

Image was created with `GSI
Tiles <https://maps.gsi.go.jp/development/ichiran.html>`__ (ort, dem).


.. index:: Pipe

Pipe
~~~~

Places a cylinder to each line segment and a sphere to each vertex.

.. raw:: html

   <table><tr><td width="256">

.. image:: ./images/line/Pipe.jpg

.. raw:: html

   </td><td>

**Specific settings** :

* Radius
    Numerical value.

**three.js geometry classes:**

    `CylinderBufferGeometry <https://threejs.org/docs/#api/en/geometries/CylinderBufferGeometry>`__
    and
    `SphereBufferGeoemtry <https://threejs.org/docs/#api/en/geometries/SphereBufferGeometry>`__

.. raw:: html

   </td></tr></table>

Image was created with `GSI
Tiles <https://maps.gsi.go.jp/development/ichiran.html>`__ (airphoto,
dem).


.. index:: Cone (Line Layer)

Cone
~~~~

Places a cone to each line segment. Heading of cone is forward
direction.

.. raw:: html

   <table><tr><td width="256">

.. image:: ./images/line/ConeL.jpg

.. raw:: html

   </td><td>

**Specific settings** :

* Radius
    Numerical value.

**three.js geometry class:**

    `CylinderBufferGeometry <https://threejs.org/docs/#api/en/geometries/CylinderBufferGeometry>`__

.. raw:: html

   </td></tr></table>

Image was created with `GSI
Tiles <https://maps.gsi.go.jp/development/ichiran.html>`__ (ort, dem) and
`National Land Numerical Information <http://nlftp.mlit.go.jp/ksj/>`__
(Rivers. MILT of Japan).


.. index:: Box (Line Layer)

Box
~~~

Places a box to each line segment.

.. raw:: html

   <table><tr><td width="256">

.. image:: ./images/line/Box.jpg

.. raw:: html

   </td><td>

**Specific settings** :

* Width
    Numerical value.
* Height
    Numerical value.

**three.js geometry class:**

    `BoxGeometry <https://threejs.org/docs/#api/en/geometries/BoxGeometry>`__

.. raw:: html

   </td></tr></table>

Image was created with `GSI
Tiles <https://maps.gsi.go.jp/development/ichiran.html>`__ (airphoto,
dem).


.. index:: Wall

Wall
~~~~

Makes a vertical wall under each line segment.

.. raw:: html

   <table><tr><td width="256">

.. image:: ./images/line/Wall.jpg

.. raw:: html

   </td><td>

**Specific settings** :

* Other side Z
    Z coordinate of the other side edge.

.. raw:: html

   </td></tr></table>

Image was created with SRTM3 elevation data.

--------------

.. _object-types-polygon-layer:

Polygon Layer
-------------

`Polygon <#polygon>`__ \| `Extruded <#extruded>`__ \| `Overlay <#overlay>`__


.. index:: Polygon

Polygon
~~~~~~~

.. raw:: html

   <table><tr><td width="256">

.. image:: ./images/no_image.png

.. raw:: html

   </td><td>

**Specific settings** :

.. raw:: html

   </td></tr></table>


.. index:: Extruded

Extruded
~~~~~~~~

Extruded polygon with specified height, color and opacity

.. raw:: html

   <table><tr><td width="256">

.. image:: ./images/polygon/Extruded.jpg

.. raw:: html

   </td><td>

**Specific settings** :

* Height
    Numerical value.

.. raw:: html

   </td></tr></table>

Image was created with `GSI
Tiles <https://maps.gsi.go.jp/development/ichiran.html>`__ (ort, dem) and
OpenStreetMap (© OpenStreetMap contributors,
`License <https://www.openstreetmap.org/copyright>`__).


.. index:: Overlay

Overlay
~~~~~~~

Overlay polygon draped on the main DEM with specified color, border color and
opacity. When the altitude mode is ``Relative to DEM layer``, each polygon is
located at the relative height from the DEM surface. Otherwise, creates a flat
polygon at specified altitude.

.. raw:: html

   <table><tr><td width="256">

.. image:: ./images/polygon/Overlay.jpg

.. raw:: html

   </td><td>

**Specific settings** :

* Border
    No border, feature style, random color or expression.

.. raw:: html

   </td></tr></table>

Image was created with `GSI
Tiles <https://maps.gsi.go.jp/development/ichiran.html>`__ (ort, dem) and
`National Land Numerical Information <http://nlftp.mlit.go.jp/ksj/>`__
(Sediment Disaster Hazard Area. Provided by Okayama prefecture, Japan).
