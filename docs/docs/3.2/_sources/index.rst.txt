*********************************
Qgis2threejs Plugin Documentation
*********************************

.. toctree::
   :maxdepth: 1
   :caption: Contents:
   :hidden:

   Examples
   Tutorial
   Exporter
   ShapeTypes
   3DViewer
   Development

:ref:`genindex`, :ref:`search`

.. image:: ./images/top.jpg

Qgis2threejs is a plugin for `QGIS <https://qgis.org/>`_ that uses `three.js <https://threejs.org/>`_ to visualize map data in 3D and
publish it on the web.

With this plugin, you can render DEM (Digital Elevation Model) raster layers and vector layers as 3D terrain and
objects in a web browser.


.. rubric:: Key Features:

Terrain visualization
   Create 3D terrain from GDAL-supported DEM data.

Flexible 3D object creation
   Create 3D objects from point, line, and polygon data using various three.js geometry types, and style them based on attribute values.

Animations
   Create animations such as camera movement, layer opacity transitions, and texture switching.

Web-ready export
   Publish interactive 3D maps as standalone HTML / JavaScript files through a simple workflow.

Interoperability
   Export your scenes in glTF / glb format for use in external 3D applications or 3D printing.
