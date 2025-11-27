Qgis2threejs Plugin
===================

Qgis2threejs is a plugin for [QGIS](https://qgis.org/) that provides 3D map visualization and web publishing functionality using the [three.js](https://threejs.org) JavaScript library. It allows you to render both DEM (digital elevation model) raster layers and vector layers (points, lines, polygons) as 3D terrain and objects inside a web browser. You can configure various object types (e.g., extruded polygons, 3D-shaped points/lines) and export the result via a simple workflow to a web-ready format. In addition to HTML/JavaScript output for interactive web maps, the plugin supports exporting the 3D model to glTF (or glb) format, enabling further use in 3D graphics applications or 3D printing pipelines.

Documentation
-------------

Online documentation: https://minorua.github.io/Qgis2threejs/docs/


Browser Support
---------------

See the [plugin wiki page](https://github.com/minorua/Qgis2threejs/wiki/Browser-Support).


Dependencies
------------

The plugin uses the following JavaScript libraries and resources:

* [three.js](https://threejs.org)

* [Proj4js](https://trac.osgeo.org/proj4js/)

* [tween.js](https://github.com/tweenjs/tween.js/) – animation support

* [Potree Core](https://github.com/tentone/potree-core) – point cloud (Potree) data support

* [dat-gui](https://github.com/dataarts/dat.gui) – 3DViewer (dat-gui) export template UI

* [Font Awesome](https://fontawesome.com/) – icons used by the Mobile export template

* Python port of [earcut](https://github.com/mapbox/earcut) – overlay polygon triangulation

* [unfetch](https://github.com/developit/unfetch) – fetch API polyfill
