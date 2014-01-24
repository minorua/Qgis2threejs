# Qgis2threejs plugin
**version 0.06**

Qgis2threejs plugin exports terrain data, map canvas image and optionally vector data into your web browser. You can view 3D map image in web browser which supports WebGL. This plugin makes use of Three.js library (http://threejs.org)

# Usage

## Short guide
Load a DEM layer and any other layers into QGIS, and set the project CRS to a projected coordinate system (the unit should be the same as that of DEM values). Next, zoom to your favorite place, and click the button in the plugin toolbar. Select the DEM layer and click Run button in the dialog. Then 3D terrain appears in your web browser!

## Export settings
### General
* Output HTML file path  
Some JavaScript files will be output into the same directory as the HTML file. You can leave this empty to output into temporary directory.

### DEM tab
* DEM Layer  
Select a DEM layer for terrain data from 1-band rasters.

* Vertical exaggeration  
Vertical exaggeration of terrain. This will also affect height of some vector objects.

##### Resampling
* Simple  
Select DEM resolution from several levels. This resolution is used to resample the DEM, but is not for texture. The map canvas image is used as it is for texture.

* Advanced (multiple resolutions)  
Multiple resolution export of terrain and texture. Area you want to focus is output in high resolution and the surroundings are output in low resolution. Draw a rectangle on the map canvas to set focus area. Specifying with a point is also possible. Resolution of the focus area varies depending on the QuadTree height. DEM grid size of each quadrangle will be 65 x 65.

### Vector tab
There is a list of layers, which are grouped into three: point, line and polygon. The right-side setting widgets get enabled when you select a layer item. Checked layers will be exported.

* Z coordinate  
Height from the surface and fixed value are selectable in all cases. In addition, z coordinate of geometry and field are selectable if available. Z coordinate of geometry cannot be used for polygon layer. The unit is that of the project CRS.

* Styles  
Select a object type from available types for each geometry type. There are some options to set color, size and so on. The unit of size is that of the project CRS. Vertical exggeration in DEM tab will apply for height of object (size).


## Plugin settings
* Browser path  
If you want to open web browser other than default browser, use this option.


# Sample
* [Mt.Fuji](https://dl.dropboxusercontent.com/u/21526091/qgis-plugins/samples/threejs/mt_fuji.html) (Color relief map made with SRTM3 data) 

# License
Three.js is MIT licensed JavaScript library. See threejs/LICENSE.

Qgis2threejs is free software; you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation; either version 2 of the License, or (at your option) any later version.

_Copyright (c) 2013 Minoru Akagi_
