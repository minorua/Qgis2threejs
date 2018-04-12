Object Types
============

.. note:: Now being updated for Qgis2threejs version 2.0.

.. contents::
   :depth: 1
   :local:

--------------

.. _object-types-point-layer:

Point Layer
-----------

`Sphere <#sphere>`__ \| `Cylinder <#cylinder>`__ \| `Cone <#cone>`__ \|
`Box <#box>`__ \| `Disk <#disk>`__


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

    `SphereGeoemtry <http://threejs.org/docs/#Reference/Extras.Geometries/SphereGeometry>`__

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

    `CylinderGeometry <http://threejs.org/docs/#Reference/Extras.Geometries/CylinderGeometry>`__

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

    `CylinderGeometry <http://threejs.org/docs/#Reference/Extras.Geometries/CylinderGeometry>`__

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

    `BoxGeometry <http://threejs.org/docs/#Reference/Extras.Geometries/BoxGeometry>`__

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
    In degrees. See `Strike and dip - Wikipedia <http://en.wikipedia.org/wiki/Strike_and_dip>`__.
* Dip direction
    In degrees.

**Origin** :

    center of disk

**three.js geometry class:**

    `CylinderGeometry <http://threejs.org/docs/#Reference/Extras.Geometries/CylinderGeometry>`__

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

    `Line <http://threejs.org/docs/#Reference/Objects/Line>`__

.. raw:: html

   </td></tr></table>

Image was created with `GSI
Tiles <http://portal.cyberjapan.jp/help/development/>`__ (ort, dem).


.. index:: Pipe

Pipe
~~~~

Places a cylinder to each line segment and a sphere to each point.

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

    `CylinderGeometry <http://threejs.org/docs/#Reference/Extras.Geometries/CylinderGeometry>`__

.. raw:: html

   </td></tr></table>

Image was created with `GSI
Tiles <http://portal.cyberjapan.jp/help/development/>`__ (ort, dem) and
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

    `BoxGeometry <http://threejs.org/docs/#Reference/Extras.Geometries/BoxGeometry>`__
    and
    `Geometry <http://threejs.org/docs/#Reference/Core/Geometry>`__

.. raw:: html

   </td></tr></table>

Image was created with `GSI
Tiles <http://portal.cyberjapan.jp/help/development/>`__ (airphoto,
dem).


.. index:: Profile

Profile
~~~~~~~

Makes a vertical plane under each line segment. When
the altitude mode of z coordinate is ``Relative to DEM`` or
``+ "field name"``, each linestring is split into segments using
a triangle mesh generated from DEM and every upper edge is located
at the relative height from the mesh surface.

.. raw:: html

   <table><tr><td width="256">

|image15|

.. raw:: html

   </td><td>

**Specific settings** :

* Other side Z
    Z coordinate of the other side edge.

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

    `ExtrudeGeometry <http://threejs.org/docs/#Reference/Extras.Geometries/ExtrudeGeometry>`__

.. raw:: html

   </td></tr></table>

Image was created with `GSI
Tiles <http://portal.cyberjapan.jp/help/development/>`__ (ort, dem) and
OpenStreetMap (© OpenStreetMap contributors,
`License <http://www.openstreetmap.org/copyright>`__).


.. index:: Overlay

Overlay
~~~~~~~

Overlay polygon draped on the main DEM with specified color, border color and
transparency. When the altitude mode of z coordinate is ``Relative to DEM`` or
``+ "field name"``, each polygon is split into triangles using a triangle
mesh generated from DEM, and is located at the relative height from
the mesh surface. Otherwise, creates a flat polygon at a specified altitude.
You can add side to each polygon if you want.

.. raw:: html

   <table><tr><td width="256">

|image22|

.. raw:: html

   </td><td>

**Specific settings** :


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
