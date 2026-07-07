Qgis2threejs plugin
===================

  This is a [QGIS](https://qgis.org/) plugin which visualizes DEM and vector data in 3D on web browsers.
You can build various kinds of 3D objects and generate files for web publishing in simple procedure.
In addition, you can save the 3D model in glTF format for 3DCG or 3D printing.


Documentation
-------------

  Online documentation: https://minorua.github.io/Qgis2threejs/docs/


Browser Support
---------------

  See [plugin wiki page](https://github.com/minorua/Qgis2threejs/wiki/Browser-Support).


Dependencies
------------

This plugin is powered by the following JavaScript libraries:

| Library / Resource | Version | Purpose |
|----------|---------|---------|
| [three.js](https://threejs.org) | r184 | 3D rendering |
| [meshline](https://github.com/pmndrs/meshline) | 3.3.1 | Thick line rendering |
| [Proj4js](https://trac.osgeo.org/proj4js/) | 2.2.1 | Coordinate transformation |
| [tween.js](https://github.com/tweenjs/tween.js/) | 18.6.4 | Animation |
| [dat-gui](https://github.com/dataarts/dat.gui) | 0.5.0 | 3DViewer (dat-gui) template export |

JavaScript dependencies are listed in `package.json` to enable GitHub's dependency analysis.
The plugin itself uses vendored copies of these libraries.
