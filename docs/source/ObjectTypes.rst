Object Types
============

.. note:: Now being updated for Qgis2threejs version 2.3.

.. contents::
   :depth: 1
   :local:

--------------

.. _object-types-point-layer:

Point Layer
-----------

`Sphere <#sphere>`__ \| `Cylinder <#cylinder>`__ \| `Cone <#cone>`__ \|
`Box <#box>`__ \| `Disk <#disk>`__ \| `Plane <#plane>`__ \| `Point <#point>`__ \|
`Icon <#icon>`__ \| `Model File <#model-file>`__


.. index:: Sphere

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

    `SphereBufferGeoemtry <https://threejs.org/docs/#api/en/geometries/SphereBufferGeometry>`__

.. raw:: html

   </td></tr></table>


.. index:: Cylinder

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

    `CylinderBufferGeometry <https://threejs.org/docs/#api/en/geometries/CylinderBufferGeometry>`__

.. raw:: html

   </td></tr></table>


.. index:: Cone (Point Layer)

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

    `CylinderBufferGeometry <https://threejs.org/docs/#api/en/geometries/CylinderBufferGeometry>`__

.. raw:: html

   </td></tr></table>


.. index:: Box (Point Layer)

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

    `BoxBufferGeometry <https://threejs.org/docs/#api/en/geometries/BoxBufferGeometry>`__

.. raw:: html

   </td></tr></table>


.. index:: Disk

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

Plane with specified length, width, orientation, color and transparency

.. raw:: html

   <table><tr><td width="256">

|image06|

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

|image09|

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


.. index:: Icon

Icon
~~~~

Image which always faces towards the camera. When an image file on local file system is specified,
the image file is copied to the export destination. When an image file on a web server is
specified, the model file is not copied.

.. raw:: html

   <table><tr><td width="256">

|image07|

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
You need to copy the relevant files such as texture image after export. When a model file on a web server is
specified, the model file is not copied.

.. raw:: html

   <table><tr><td width="256">

|image08|

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


.. index:: Line

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

|image12|

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

|image13|

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

|image14|

.. raw:: html

   </td><td>

**Specific settings** :

* Width
    Numerical value.
* Height
    Numerical value.

**three.js geometry class:**

    `BoxGeometry <https://threejs.org/docs/#api/en/geometries/BoxGeometry>`__
    and
    `Geometry <https://threejs.org/docs/#api/en/core/Geometry>`__

.. raw:: html

   </td></tr></table>

Image was created with `GSI
Tiles <https://maps.gsi.go.jp/development/ichiran.html>`__ (airphoto,
dem).


.. index:: Profile

Profile
~~~~~~~

Makes a vertical plane under each line segment.

.. raw:: html

   <table><tr><td width="256">

|image15|

.. raw:: html

   </td><td>

**Specific settings** :

* Other side Z
    Z coordinate of the other side edge.

**three.js geometry class:**

    `Geometry <https://threejs.org/docs/#api/en/core/Geometry>`__

.. raw:: html

   </td></tr></table>

Image was created with SRTM3 elevation data.

--------------

.. _object-types-polygon-layer:

Polygon Layer
-------------

`Extruded <#extruded>`__ \| `Overlay <#overlay>`__ \| `Triangular Mesh <#triangular-mesh>`__

.. index:: Extruded

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

    `ExtrudeBufferGeometry <https://threejs.org/docs/#api/en/geometries/ExtrudeBufferGeometry>`__

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
transparency. When the altitude mode is ``Relative to DEM layer``, each polygon
is split into triangles using a triangle mesh generated from the DEM, and is
located at the relative height from the mesh surface. Otherwise, creates a flat
polygon at a specified altitude.

.. raw:: html

   <table><tr><td width="256">

|image22|

.. raw:: html

   </td><td>

**Specific settings** :


**three.js classes:**

    `Geometry <https://threejs.org/docs/#api/en/core/Geometry>`__

.. raw:: html

   </td></tr></table>

Image was created with `GSI
Tiles <https://maps.gsi.go.jp/development/ichiran.html>`__ (ort, dem) and
`National Land Numerical Information <http://nlftp.mlit.go.jp/ksj/>`__
(Sediment Disaster Hazard Area. Provided by Okayama prefecture, Japan).


.. index:: Triangular-Mesh

Triangular Mesh
~~~~~~~~~~~~~~~

Build 3D objects from 3D triangular geometries. All layer geometries are assumed to be triangles.
If you want to use polygon data that doesn't consist of triangles, perform triangulation
using tessellation algorithm of Processing first.

.. raw:: html

   <table><tr><td width="256">

|image23|

.. raw:: html

   </td><td>

**Specific settings** :


**three.js classes:**

    `Geometry <https://threejs.org/docs/#api/en/core/Geometry>`__

.. raw:: html

   </td></tr></table>
