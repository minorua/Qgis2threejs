Qgis2threejs plugin
===================

  This is a [QGIS](https://qgis.org/) plugin which visualizes DEM and vector data in 3D on web browsers.
You can build various kinds of 3D objects and generate files for web publishing in simple procedure.
In addition, you can save the 3D model in glTF format for 3DCG or 3D printing.


Document
--------

  Online document: https://minorua.github.io/Qgis2threejs/docs/


Browser Support
---------------

  See [plugin wiki page](https://github.com/minorua/Qgis2threejs/wiki/Browser-Support).


Dependencies
------------

This plugin is powered by the following JavaScript libraries and resources:

* [three.js](https://threejs.org)

* [Proj4js](https://trac.osgeo.org/proj4js/)

* [tween.js](https://github.com/tweenjs/tween.js/) for animation

* [Potree Core](https://github.com/tentone/potree-core) for Potree data support

* [dat-gui](https://github.com/dataarts/dat.gui) for export based on 3DViewer(dat-gui) template

* [Font Awesome](https://fontawesome.com/) icons for export based on Mobile template

* Python ported version of [earcut](https://github.com/mapbox/earcut) for Overlay polygon triangulation

* [unfetch](https://github.com/developit/unfetch) fetch polyfill
