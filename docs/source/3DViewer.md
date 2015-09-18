3D Viewer
=========

* [Controls](#Controls)
* [Identifying Features](#Identify)
* [Control Panel](#ControlPanel)
* [Rotate Animation](#RotateAnimation)
* [Save Image](#SaveImage)
* [URL Parameters](#URLParameters)  


## <a name="Controls"/> Controls

  Mouse and key controls depend on the control selected in the export settings. There is list of mouse buttons and keys in the about box. Press `I` key to show the box.


## <a name="Identify"/> Identifying Features

  When you click on an object, layer name that the feature (object) belongs to and the clicked coordinates (in order of x, y, z) are shown. If `Latitude and longitude (WGS84)` option (in `Display of coordinates` of World page) is selected, longitude and latitude are shown in DMS format (degrees, minutes and seconds). If `Export attributes` option of each vector layer is selected, attribute list of the clicked feature follows them.


## <a name="ControlPanel"/> Control Panel

  This feature is available with **3DViewer(dat-gui) template**.

The control panel has:

* layer sub menus

  Each sub menu has:

  * a check box to toggle layer visibility
  * a slider to adjust layer transparency

* sub menu to add a vertically movable plane
* help button to show the about box


## <a name="RotateAnimation"/> Rotate Animation

  This feature is available with **OrbitControls**.

Pressing `R` key starts/stops rotate animation. Camera rotates around the camera target clockwise.


## <a name="SaveImage"/> Save Image

  To save the canvas image, press `Shift + S` to show save image dialog, then enter image size and click the OK button. In addition, with some web browsers, you need to click a link to save image. The image file format is PNG. To change label color and/or adjust label size, edit `Qgis2threejs.css` (`print-label` class).

Known issue:

* Wrong image output if the size is too large https://github.com/minorua/Qgis2threejs/issues/42


## <a name="URLParameters"/> URL Parameters

You can get current view URL in the about box, and later restore the view by entering the URL in the URL box of web browser.

Parameters used in view URL:

* cx, cy, cz: camera position
* tx, ty, tz: camera target
* ux, uy, uz: camera up direction (TrackballControls)

e.g. file:///D:/example.html#cx=-64.8428840144039&cy=-40.75234765087484&cz=24.603200058346065


Other parameters:

* width: canvas width
* height: canvas height
* popup: pop up another window with specified width and height


<!-- TODO: images -->

***
Qgis2threejs plugin version 1.3
