Shape Types
===========

.. warning::

   This page has not been updated for a while and may contain outdated information.
   Please wait while we update it.


Point Layer
-----------

`Sphere <#sphere>`__ \| `Cylinder <#cylinder>`__ \| `Cone <#cone>`__ \|
`Box <#box>`__ \| `Disk <#disk>`__ \| `Plane <#plane>`__ \| `Point <#point>`__ \|
`Billboard <#billboard>`__ \| `Model File <#model-file>`__


.. index:: Sphere (Point Layer)

Sphere
~~~~~~

.. list-table::
   :widths: 1 2
   :align: left
   :class: valign-top

   * - .. image:: ./images/point/Sphere.jpg
     - **Specific settings**

         * Radius
            Radius of sphere (numeric value).

       **Origin**

         Sphere center

       **three.js geometry class**

         `SphereGeometry <https://threejs.org/docs/#SphereGeometry>`__


.. index:: Cylinder (Point Layer)

Cylinder
~~~~~~~~

.. list-table::
   :widths: 1 2
   :align: left
   :class: valign-top

   * - .. image:: ./images/point/Cylinder.jpg
     - **Specific settings**

         * Radius
            Radius of cylinder (numeric value).

         * Height
            Height of cylinder (numeric value).

       **Origin**

        Bottom center (when height > 0)

       **three.js geometry class**

         `CylinderGeometry <https://threejs.org/docs/#CylinderGeometry>`__


.. index:: Cone (Point Layer)

Cone
~~~~

.. list-table::
   :widths: 1 2
   :align: left
   :class: valign-top

   * - .. image:: ./images/point/Cone.jpg
     - **Specific settings**

         * Radius
            Radius of cone (numeric value).

         * Height
            Height of cone (numeric value).

       **Origin**

         Bottom center (when height > 0)

       **three.js geometry class**

         `CylinderGeometry <https://threejs.org/docs/#CylinderGeometry>`__



.. index:: Box (Point Layer)

Box
~~~

.. list-table::
   :widths: 1 2
   :align: left
   :class: valign-top

   * - .. image:: ./images/point/Box.jpg
     - **Specific settings**

         * Width
            Width of box (size in X direction, numeric value).

         * Depth
            Depth of box (size in Y direction, numeric value).

         * Height
            Height of box (size in Z direction, numeric value).

       **Origin**

         Bottom center (when height > 0)

       **three.js geometry class**

         `BoxGeometry <https://threejs.org/docs/#BoxGeometry>`__

       **Note**

         In three.js, height is along the Y axis.
         Qgis2threejs uses the Z axis for height.


.. index:: Disk (Point Layer)

Disk
~~~~

.. list-table::
   :widths: 1 2
   :align: left
   :class: valign-top

   * - .. image:: ./images/point/Disk.jpg
     - **Specific settings**

         * Radius
            Radius of disk (numeric value).

         * Dip
            Dip angle in degrees. See `Strike and dip - Wikipedia <https://en.wikipedia.org/wiki/Strike_and_dip>`__.

         * Dip direction
            Azimuth of the maximum dip direction (clockwise from north, degrees).

       **Origin**

        Disk center

       **three.js geometry class**

        `CircleGeometry <https://threejs.org/docs/#CircleGeometry>`__


.. index:: Plane (Point Layer)

Plane
~~~~~

.. list-table::
   :widths: 1 2
   :align: left
   :class: valign-top

   * - .. image:: ./images/no_image.png
     - **Specific settings**

         * Width
            Numerical value.

         * Length
            Numerical value.

         * Dip
            Numerical value in degrees. See `Strike and dip - Wikipedia <https://en.wikipedia.org/wiki/Strike_and_dip>`__.

         * Dip direction
            Numerical value in degrees.

        ✏

       **Origin**

        Plane center

       **three.js geometry class**

        `PlaneGeometry <https://threejs.org/docs/#PlaneGeometry>`__


.. index:: Point (Point Layer)

Point
~~~~~


.. list-table::
   :widths: 1 2
   :align: left
   :class: valign-top

   * - .. image:: ./images/no_image.png
     - **Specific settings**

         * Size (in Material tab)
            Numerical value.

       **Origin**

         Sprite center

       **three.js object class**

         `Sprite <https://threejs.org/docs/#Sprite>`__


.. index:: Billboard (Point Layer)

Billboard
~~~~~~~~~

Image which always faces towards the camera. When an image file on local file system is specified,
the image file is copied to the export destination. When an image file on a web server is
specified, the model file is not copied.

.. list-table::
   :widths: 1 2
   :align: left
   :class: valign-top

   * - .. image:: ./images/no_image.png
     - **Specific settings**

         * Image file
            File path or URL. If you enter a file path or URL directly, enclose it in single quotation marks.

         * Scale
            Numerical value.

       **Origin**

         Sprite center

       **three.js object class**

         `Sprite <https://threejs.org/docs/#Sprite>`__


.. index:: Model-File (Point Layer)

Model File
~~~~~~~~~~

Load 3D model from supported format model file. ``COLLADA (*.dae)`` and ``glTF (*.gltf, *.glb)`` are supported.
When a model file on local file system is specified, the model file is copied to the export destination.
You need to copy the relevant files such as texture image after export. When a model file URL is
specified, the model file is not copied.

.. list-table::
   :widths: 1 2
   :align: left
   :class: valign-top

   * - .. image:: ./images/no_image.png
     - **Specific settings**

         * Model file
            File path or URL. If you enter a file path or URL directly, enclose it in single quotation marks.

         * Scale
            Numerical value.

         * Rotation (x)
            Numerical value in degrees.

         * Rotation (y)
            Numerical value in degrees.

         * Rotation (z)
            Numerical value in degrees.

         * Rotation Order
            The options are XYZ, YZX, ZXY, XZY, YXZ and ZYX. See `Euler - three.js docs <https://threejs.org/docs/#Euler.order>`__.

       **Origin**

         Model origin


--------------


Line Layer
----------

`Line <#line>`__ \| `Pipe <#pipe>`__ \| `Cone <#cone>`__ \|
`Box <#box>`__ \| `Wall <#wall>`__


.. index:: Line (Line Layer)

Line
~~~~

.. list-table::
   :widths: 1 2
   :align: left
   :class: valign-top

   * - .. figure:: ./images/line/Line.png

         Image was created with `GSI Tiles <https://maps.gsi.go.jp/development/ichiran.html>`__ (ort, dem).

     - **Specific settings**

         no specific settings

       **three.js object class:**

         `Line <https://threejs.org/docs/#Line>`__




.. index:: Pipe (Line Layer)

Pipe
~~~~

Places a cylinder to each line segment and a sphere to each vertex.

.. list-table::
   :widths: 1 2
   :align: left
   :class: valign-top

   * - .. figure:: ./images/line/Pipe.jpg

         Image was created with `GSI Tiles <https://maps.gsi.go.jp/development/ichiran.html>`__ (airphoto, dem).

     - **Specific settings**

        * Radius
            Radius of pipe (numeric value).

       **three.js geometry classes:**

         `CylinderGeometry <https://threejs.org/docs/#CylinderGeometry>`__
         and
         `SphereGeoemtry <https://threejs.org/docs/#SphereGeometry>`__


.. index:: Cone (Line Layer)

Cone
~~~~

Places a cone to each line segment. Heading of cone is forward
direction.

.. list-table::
   :widths: 1 2
   :align: left
   :class: valign-top

   * - .. figure:: ./images/line/ConeL.jpg

         Image was created with `GSI Tiles <https://maps.gsi.go.jp/development/ichiran.html>`__ (ort, dem) and
         `National Land Numerical Information <http://nlftp.mlit.go.jp/ksj/>`__ (Rivers. MILT of Japan).

     - **Specific settings**

        * Radius
            Radius of cone (numeric value).

       **Origin**

         Sphere center (point feature position)

       **three.js geometry class**

         `CylinderGeometry <https://threejs.org/docs/#CylinderGeometry>`__


.. index:: Box (Line Layer)

Box
~~~

Places a box to each line segment.

.. list-table::
   :widths: 1 2
   :align: left
   :class: valign-top

   * - .. figure:: ./images/line/Box.jpg

         Image was created with `GSI Tiles <https://maps.gsi.go.jp/development/ichiran.html>`__ (airphoto, dem).

     - **Specific settings**


        * Width
            Numerical value.

        * Height
            Numerical value.

       **three.js geometry class**

         `BoxGeometry <https://threejs.org/docs/#BoxGeometry>`__


.. index:: Wall (Line Layer)

Wall
~~~~

Makes a vertical wall under each line segment.

.. list-table::
   :widths: 1 2
   :align: left
   :class: valign-top

   * - .. figure:: ./images/line/Wall.jpg

         Image was created with SRTM3 elevation data.

     - **Specific settings**

        * Other side Z
            Z coordinate of the other side edge.

--------------


Polygon Layer
-------------

`Polygon <#polygon>`__ \| `Extruded <#extruded>`__ \| `Overlay <#overlay>`__


.. index:: Polygon (Polygon Layer)

Polygon
~~~~~~~

.. list-table::
   :widths: 1 2
   :align: left
   :class: valign-top

   * - .. image:: ./images/no_image.png
     - **Specific settings**


.. index:: Extruded (Polygon Layer)

Extruded
~~~~~~~~

.. list-table::
   :widths: 1 2
   :align: left
   :class: valign-top

   * - .. figure:: ./images/polygon/Extruded.jpg

         Image was created with `GSI Tiles <https://maps.gsi.go.jp/development/ichiran.html>`__ (ort, dem) and
         OpenStreetMap (© OpenStreetMap contributors, `License <https://www.openstreetmap.org/copyright>`__).

     - **Specific settings**

        * Height
            Numerical value.


.. index:: Overlay (Polygon Layer)

Overlay
~~~~~~~

Overlay polygon draped on the main DEM with specified color, border color and
opacity. When the altitude mode is ``Relative to DEM layer``, each polygon is
located at the relative height from the DEM surface. Otherwise, creates a flat
polygon at specified altitude.

.. list-table::
   :widths: 1 2
   :align: left
   :class: valign-top

   * - .. figure:: ./images/polygon/Overlay.jpg

         Image was created with `GSI Tiles <https://maps.gsi.go.jp/development/ichiran.html>`__ (ort, dem) and
         `National Land Numerical Information <http://nlftp.mlit.go.jp/ksj/>`__ (Sediment Disaster Hazard Area. Provided by Okayama prefecture, Japan).

     - **Specific settings**

        * Border
            No border, feature style, random color or expression.
