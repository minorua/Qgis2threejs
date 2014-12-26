Qgis2threejs plugin - version 0.7.2
=====================================

Qgis2threejs plugin exports terrain data, map canvas image and vector data to your web browser. You can view 3D objects in web browser which supports WebGL. This plugin makes use of three.js library (http://threejs.org).


Check WebGL support
-------------------
Visit http://get.webgl.org/ to check whether your web browser supports WebGL.


Samples
-------
Visit [Samples](https://github.com/minorua/Qgis2threejs/wiki/Samples) page in GitHub Wiki.


Usage
=====

Short guide
-----------
Load a DEM layer and any other layers into QGIS, and set the project CRS to a projected coordinate system (the unit should be the same as that of DEM values). Next, zoom to your favorite place, and click the plugin button in the web toolbar. Select the DEM layer and click Run button in the dialog. Then 3D terrain appears in your web browser!


Export settings
---------------
Settings for DEM and Vector layers had been splitted into two tab pages until version 0.6. Since version 0.7, they have been integrated into a tree widget. You can change their properties with widgets displayed on the right side. There is a combo box to select a template at the top of the dialog. An edit box to select output HTML file path is above the buttons at the bottom. Exporting is done when you press the Run button.

* Template combo box  
There are three available templates:
 * Simple3D.html  
 * CustomPlane.html  
  A plane is added to scene. You can change elevation, color and opacity of the plane with the control panel on the web browser.
 * STLExport.html  
  This template builds 3D models on the web browser, but doesn't render them. Instead, it has ability to save 3D models in [STL format](http://en.wikipedia.org/wiki/STL_%28file_format%29). You can also save the texture image. The STL format is widely supported by 3DCG softwares such as [Blender](http://www.blender.org/).

* Tree for settings and property widgets  
Items with check box are optional. When the current item is optional and not checked, widgets on the right side are disabled. See "General settings and Layer settings" below for details.

* Output HTML file path  
Some JavaScript files will be output into the same directory as the HTML file. You can leave this empty to output into temporary directory.

### General settings and Layer settings
#### World
* Vertical exaggeration  
Exaggeration degree of terrain. This value also affects height of some 3D objects such as cylinder and extruded polygon. The default value is 1.5.

* Vertical shift  
Vertical shift for objects. If you want to export terrain of narrow area and high altitude, you should adjust the object positions to be displayed at the center of browser by changing this value. If you set the value to -1000, all objects are shifted down by 1000 (meters).

* Background  
Sky-like gradient background is selected by default. You can change it to a solid color.

#### Controls
There are two available controls: TrackballControls and OrbitControls. With OrbitControls, you can move and rotate the camera with arrow keys on keyboard. The usage of each control is displayed below the combo box. On the web browser showing exported page, clicking the i button on the bottom left corner or pressing i key shows the usage.

#### DEM
Selected DEM layer is used as a reference for z positions of vector objects. You can select DEM layer from 1-band rasters loaded in QGIS. You can also select a flat plane at zero altitude.

##### * Resampling
* Simple  
Select DEM resolution from several levels. This resolution is used to resample the DEM, but is not for texture.

 * Surroundings option  
This option enlarges output terrain by placing terrain blocks around the extent of the map canvas. Size can be selected from odd numbers in the range of 3 to 9. If you select 3, total 9 (=3x3) blocks (a center block and 8 surrounding blocks) will be output. Roughening can be selected from powers of 2 in the range of 1 to 64. If you select 2, grid point spacing is doubled. It means that the number of grid points in the same area becomes 1/4. If map canvas image is selected as the display type, texture image size of each block is maximum 256 x 256.

* Advanced (quad tree)  
Multiple resolution export of terrain and texture. Area you want to focus is output in high resolution and the surroundings are output in low resolution. Draw a rectangle on the map canvas to set focus area. Specifying a point is also possible. Resolution of the focus area varies depending on the value of QuadTree height. Grid size of each quadrangle is 64 x 64.

##### * Display type
You can choose from map canvas image, image file, solid color and wireframe.

* Map canvas image  
Map canvas image is used as it is to texture terrain of main block in simple resampling mode. Each block of surroundings (in simple resampling mode) and quads (in advanced resampling mode) is textured with image rendered with the current layer settings.

* Image file  
Existing image file such as PNG or JPEG file is used to texture DEM. To enable transmission of transparent PNG, the transparency value should be set to a small non-zero number (e.g. 1).

* Solid color or Wireframe  
Press the button on the right side of the color box and select a color.

You can set transparency with the transparency spinbox. 0 is opaque, and 100 is transparent.

##### * Sides and frame
Options to add sides and/or frame. Transparency can be changed. If you want to change their colors. please edit the output JS file directly.

#### Additional DEM
If you want to export more than one DEM, check the checkbox on the left of child items. For example of usage, it may be possible to cover the terrain with supposed terrain surface of a summit level map, or make a 3D heat map.
Some options that are available in (primary) DEM cannot be used. Resampling mode is limited to simple. Surroundings, sides and frame options are not available.

#### Point, Line and Polygon
Vector layers are grouped into three types: Point, Line and Polygon.

* Z coordinate  
Height from the surface and fixed value are selectable in all cases. In addition, z coordinate of geometry and field are selectable if available. Z coordinates of polygons cannot be used. The unit is that of the project CRS.

* Styles  
Select a object type from available types of each geometry type. There are some options to set color, transparency, size and so on. The unit of size is that of the project CRS.

* Attributes  
If the export attributes option is checked, attributes of each feature are exported. Attributes are displayed when you click an object on web browser.  
If a field in the label combobox is selected, a label is displayed above each object and is connected to the object with a line. On web browser, you can hide the labels by pressing L key.

Plugin settings
---------------
* Browser path  
If you want to open web browser other than default browser, use this option.


JavaScript libraries used by exported page
==========================================
* All exports use [three.js](http://threejs.org)
* Exports based on CustomPlane template use [dat-gui](https://code.google.com/p/dat-gui/)
* Exports based on STLExport template use [JSZip](http://stuk.github.io/jszip/) and [FileSaver.js](https://github.com/eligrey/FileSaver.js/)

License
=======
Python modules of Qgis2threejs are released under the GNU Public License (GPL) Version 2.

_Copyright (c) 2013 Minoru Akagi_
