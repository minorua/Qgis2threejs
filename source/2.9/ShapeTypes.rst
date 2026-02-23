Shape Types
===========


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
            Radius of the sphere (numeric value).

       **Origin**
         The center of the sphere

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
            Radius of the cylinder (numeric value).

         * Height
            Height of the cylinder (numeric value).

       **Origin**
         The bottom center of the cylinder (when height > 0)

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
            Radius of the cone (numeric value).

         * Height
            Height of the cone (numeric value).

       **Origin**
         The bottom center of the cone (when height > 0)

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
            Width of the box (size in the X axis, numeric value).

         * Depth
            Depth of the box (size in the Y axis, numeric value).

         * Height
            Height of the box (size in the Z axis, numeric value).

       **Origin**
         The bottom center of the box (when height > 0)

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
            Radius of the disk (numeric value).

         * Dip
            Dip angle in degrees. See |WIKI_STRIKE_DIP|.

         * Dip direction
            Azimuth of the maximum dip direction (clockwise from north, degrees).

       **Origin**
         The center of the disk

       **three.js geometry class**
         `CircleGeometry <https://threejs.org/docs/#CircleGeometry>`__


.. index:: Plane (Point Layer)

Plane
~~~~~

.. list-table::
   :widths: 1 2
   :align: left
   :class: valign-top

   * - .. image:: ./images/point/Plane.jpg
     - **Specific settings**
         * Width
            Width of the plane in strike direction (numeric value).

         * Length
            Length of the plane in dip direction (numeric value).

         * Dip
            Dip angle in degrees. See |WIKI_STRIKE_DIP|.

         * Dip direction
            Azimuth of the maximum dip direction (clockwise from north, degrees).

       **Origin**
         The center of the plane

       **three.js geometry class**
         `PlaneGeometry <https://threejs.org/docs/#PlaneGeometry>`__


.. index:: Point (Point Layer)

Point
~~~~~


.. list-table::
   :widths: 1 2
   :align: left
   :class: valign-top

   * - .. figure:: ./images/point/Point.jpg

         100,000 randomly generated 3D points colored by their Z values

     - **Specific settings**
         * Size (in Material tab)
            Size of the points in pixels.

       **Origin**
         The center of the object.

       **three.js object class**
         `Points <https://threejs.org/docs/#Points>`__


.. index:: Billboard (Point Layer)

Billboard
~~~~~~~~~

An image that always faces the camera. When an image file on local file system is specified,
the image file is copied to the export destination. When an image file on a web server is
specified, the image file is not copied.

.. list-table::
   :widths: 1 2
   :align: left
   :class: valign-top

   * - .. image:: ./images/no_image.png
     - **Specific settings**
         * Image file
            File path or URL. If you enter a file path or URL directly, enclose it in single quotation marks.

         * Scale
            Width of the sprite in world units (same units as map coordinates). The height is automatically calculated from this value to preserve the aspect ratio of the image.

       **Origin**
         The center of the sprite.

       **three.js object class**
         `Sprite <https://threejs.org/docs/#Sprite>`__


.. index:: Model-File (Point Layer)

Model File
~~~~~~~~~~

Load a 3D model from a supported model file format. ``COLLADA (*.dae)`` and ``glTF (*.gltf, *.glb)`` are supported.
When a model file on the local file system is specified, the model file is copied to the export destination.
After export, you need to copy any associated files such as texture image. When a model file URL is
specified, the model file is referenced and not copied.

.. list-table::
   :widths: 1 2
   :align: left
   :class: valign-top

   * - .. image:: ./images/no_image.png
     - **Specific settings**
         * Model file
            File path or URL. If you enter a file path or URL directly, enclose it in single quotation marks.

         * Scale
            A numeric value.

         * Rotation (x)
            Rotation around the X axis in degrees. Positive values rotate the model according to the right-hand rule.

         * Rotation (y)
            Rotation around the Y axis in degrees. Positive values rotate the model according to the right-hand rule.

         * Rotation (z)
            Rotation around the Z axis in degrees. Positive values rotate the model according to the right-hand rule.

         * Rotation Order
            The options are XYZ, YZX, ZXY, XZY, YXZ and ZYX. See `Euler - three.js docs <https://threejs.org/docs/#Euler.order>`__.

       **Origin**

         The origin of the model


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

         Image created using |GSI_TILES| (ort, dem).

     - **Specific settings**
         None

       **three.js object class:**
         `Line <https://threejs.org/docs/#Line>`__


.. index:: Pipe (Line Layer)

Pipe
~~~~

Places a cylinder along each line segment and a sphere to each vertex.

.. list-table::
   :widths: 1 2
   :align: left
   :class: valign-top

   * - .. figure:: ./images/line/Pipe.jpg

         Image created using |GSI_TILES| (airphoto, dem).

     - **Specific settings**
         * Radius
            Radius of the pipe (numeric value).

       **three.js geometry classes:**
         `CylinderGeometry <https://threejs.org/docs/#CylinderGeometry>`__
         and
         `SphereGeoemtry <https://threejs.org/docs/#SphereGeometry>`__


.. index:: Cone (Line Layer)

Cone
~~~~

Places a cone along each line segment. The cone is oriented in the forward direction of the line.

.. list-table::
   :widths: 1 2
   :align: left
   :class: valign-top

   * - .. figure:: ./images/line/ConeL.jpg

         Image created using |GSI_TILES| (ort, dem) and
         `National Land Numerical Information <http://nlftp.mlit.go.jp/ksj/>`__ (Rivers. MILT of Japan).

     - **Specific settings**
         * Radius
            Radius of the cone (numeric value).

       **three.js geometry class**
         `CylinderGeometry <https://threejs.org/docs/#CylinderGeometry>`__


.. index:: Box (Line Layer)

Box
~~~

Places a box along each line segment.

.. list-table::
   :widths: 1 2
   :align: left
   :class: valign-top

   * - .. figure:: ./images/line/Box.jpg

         Image created using |GSI_TILES| (airphoto, dem).

     - **Specific settings**
         * Width
            Width of the box (numeric value).

         * Height
            Height of the box (numeric value).

       **three.js geometry class**
         `BoxGeometry <https://threejs.org/docs/#BoxGeometry>`__


.. index:: Wall (Line Layer)

Wall
~~~~

Creates a vertical wall from each line segment down to a specified Z value.

.. list-table::
   :widths: 1 2
   :align: left
   :class: valign-top

   * - .. figure:: ./images/line/Wall.jpg

         Image created using SRTM3 elevation data.

     - **Specific settings**
         * Other side Z
            The Z coordinate of the opposite edge of the wall (numeric value).


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
         None


.. index:: Extruded (Polygon Layer)

Extruded
~~~~~~~~

Extrudes the polygon vertically to create a 3D object.

.. list-table::
   :widths: 1 2
   :align: left
   :class: valign-top

   * - .. figure:: ./images/polygon/Extruded.jpg

         Image created using |GSI_TILES| (ort, dem) and
         OpenStreetMap (© OpenStreetMap contributors, `License <https://www.openstreetmap.org/copyright>`__).

     - **Specific settings**
         * Height
            The extrusion height of the polygon (numeric value).


.. index:: Overlay (Polygon Layer)

Overlay
~~~~~~~

Overlays the polygon on the main DEM with a specified fill color, border color and opacity.
When the altitude mode is ``Relative to DEM layer``, the polygon is placed at a height relative to the DEM surface.
Otherwise, a flat polygon is created at the specified altitude.

.. list-table::
   :widths: 1 2
   :align: left
   :class: valign-top

   * - .. figure:: ./images/polygon/Overlay.jpg

         Image created using |GSI_TILES| (ort, dem) and
         `National Land Numerical Information <http://nlftp.mlit.go.jp/ksj/>`__ (Sediment Disaster Hazard Area. Provided by Okayama prefecture, Japan).

     - **Specific settings**
         * Border
            No border, feature style, random color, or expression.
