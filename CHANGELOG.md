## CHANGELOG

### Version 1.1
* updated the STLExporter to support other file formats (collada, obj) and is easier to extend (by Olivier Dalang)

### Version 1.0
* layer opacity sliders in dat-gui panel
* wireframe mode
* popup style update
* new object types: Disk (Point), Icon (Point), Overlay (Polygon)
* base size option (World)
* option to display coordinates in WGS84 lat/lon (World)
* layer image option (DEM)
* clip geometries option (Vector)
* code refactoring (more oo code)

### Version 0.7.2

* add object type: Profile (line)
* add shading option to DEM
* 3D print compatible STL export
* fix for QGIS 2.5

### Version 0.7.1

* add template: STLExport
* add object type: Pipe and Cone (line)
* add URL parameters

### Version 0.7

* export with no DEM and multiple DEMs
* add options for DEM: vertical shift, sides, frame, transparency, display type and surroundings
* add template: custom plane
* add controls: OrbitControls
* attribute export and labeling
* make objects queryable
* integrate DEM and Vector tabs
* fix texture loading
* move plugin items into web menu/toolbar
* add object type: JSON model (experimental)

### Version 0.6

* fix confusing GUI

### Version 0.5

* object export based on vector layers
* add object type: Sphere, Cylinder, Cube, Cone, Line, (Extruded) Polygon

### Version 0.4

* advanced resampling mode (quad tree)
* vertical exaggeration
* reproject DEM in memory
* settings dialog (browser path)
