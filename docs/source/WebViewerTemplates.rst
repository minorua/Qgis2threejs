Web Viewer Templates
====================

.. 
  .. note:: Now being updated for Qgis2threejs version 2.3.

In Export to Web dialog, you can choose one from following available
web viewer templates:

* :ref:`3dviewer-template`
* :ref:`3dviewer-dat-gui-template`
* :ref:`mobile-template`


Common Functions
----------------

There is a list of mouse/keyboard controls in about box.
Press ``I`` key to show the box.

Identifying Features
^^^^^^^^^^^^^^^^^^^^

When you click on a 3D object, layer name that the object belongs to
and the clicked coordinates (in order of x, y, z) are displayed.
If ``Latitude and longitude (WGS84)`` option in World Settings is
selected, longitude and latitude are in DMS format (degrees, minutes
and seconds). If ``Export attributes`` option of each vector layer
is selected, attribute values of the clicked feature follows them.


Rotate Animation (Orbiting)
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Pressing ``R`` key starts/stops rotate animation. Camera rotates around
the camera target clockwise.

Save Image
^^^^^^^^^^

Press ``Shift + S`` to show save image dialog, then enter image size and
click the OK button. In addition, with some web browsers, you need to
click a link to save image. The image file format is PNG. To change label
color and/or adjust label size, edit ``Qgis2threejs.css`` (``print-label`` class).

.. note:: A known issue: Wrong image output if the size is too large (`issue #42`__)

__ https://github.com/minorua/Qgis2threejs/issues/42


URL Parameters
^^^^^^^^^^^^^^

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


.. _3dviewer-template:

3D Viewer Template
------------------

This template is a simple 3D viewer.
Ragardless of "Visible on load" layer setting, all exported layers are displayed on page load.

.. 
   [TODO] image

.. _3dviewer-dat-gui-template:

3D Viewer(dat-gui) Template
---------------------------

This template has a dat-gui panel, which allows changing layer visibility and opacity, and adding a horizontal plane.

.. 
   [TODO] image

Controls Box
^^^^^^^^^^^^
The controls box has:

* layer sub menus

   Each sub menu has:

   * a check box to toggle layer visibility
   * a slider to change layer opacity

* sub menu to control a vertically movable plane
* help button to show the about box


.. _mobile-template:

Mobile Template
---------------

This is a template for mobile devices, which has mobile friendly GUI, device orientation controls and AR feature.
In order to use the AR feature (Camera and GPS), you need to upload exported files to a web server supporting SSL.

.. 
   [TODO] image
