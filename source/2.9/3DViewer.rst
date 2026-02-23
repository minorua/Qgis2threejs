*********
3D Viewer
*********


3D Viewer Controls
==================

Customized OrbitControls for Qgis2threejs are available.


Basic Controls
--------------

======================= =====================================
Mouse / Key             Control
======================= =====================================
Left button + drag      Orbit (rotate around the focal point)
Scroll wheel            Zoom
Right button + drag     Pan (move horizontally)
Arrow keys              Pan (move horizontally)
======================= =====================================


Additional Controls
-------------------

========================== ==========================================
Mouse / Key                Control
========================== ==========================================
Shift + Left button + drag Move perpendicular to the camera direction
========================== ==========================================


Keyboard Shortcuts
------------------

========== ============================
Key        Control
========== ============================
I          Show 3D viewer controls
R          Start / Stop orbit animation
W          Toggle wireframe mode
Shift + S  Save Image
========== ============================


Orbit Animation
^^^^^^^^^^^^^^^

Camera rotates around the focal location clockwise.


Identifying Features
--------------------

When you click on a 3D object, layer name that the object belongs to
and the clicked coordinates (in order of x, y, z) are displayed.
If ``Latitude and longitude (WGS84)`` option in World Settings is
selected, longitude and latitude are in DMS format (degrees, minutes
and seconds). If ``Export attributes`` option of each vector layer
is selected, attribute values of the clicked feature follows them.


3D Viewer Templates
===================

In Export to Web dialog, you can choose one from following available
3D viewer templates:

* 3D Viewer
* 3D Viewer(dat-gui)
* Mobile

For details, see :ref:`export-to-web-dialog`.


URL Parameters
==============

You can get current view URL in the about box, and later restore the
view by entering the URL in the URL box of web browser.

Parameters used in view URL:

* cx, cy, cz: camera position
* tx, ty, tz: camera target

For example,
file:///D:/example.html#cx=-64.8428840144039&cy=-40.75234765087484&cz=24.603200058346065

Other parameters:

* width: canvas width (pixels)
* height: canvas height (pixels)
* popup: pop up another window with specified width and height
