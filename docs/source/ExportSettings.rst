Export Settings
===============

Plugin Dialog
-------------

.. figure:: https://github.com/minorua/Qgis2threejs/wiki/images/dialog.png
   :alt: dialog image

In order from the top:

* Combo box to select a template

   Select one from templates with different functions. See
   `Template <#template>`__ section.

* Tree widget on the left side and panel with widgets on the right side

   Items with check box in the tree widget are optional. When the current
   item is optional and not checked, widgets on the right side are grayed
   out.

* Output HTML file path edit box

   Select output HTML file path. Usually, a js file with the same file
   title that contains whole data of geometries and images is output into
   the same directory, and some JavaScript library files are copied to
   under the directory. Leave this empty to output into temporary
   directory. Temporary files are removed when you close the QGIS
   application.

* Settings button

   Pop-up menu with the following menu items is shown:

   * Load Settings

      Loads export settings from a settings file.

   * Save Settings As

      Saves export settings to a settings file. Default file extension is
      ``.qto3settings``.

   * Clear Settings

      Clears current export settings.

   * Plugin Settings

      Shows :doc:`PluginSettings` dialog.

* Run, Close and Help buttons

   Exporting starts when you press the Run button. When the exporting has
   been done, the exported page will be opened in web browser. At this
   time, export settings are automatically saved to a file under the same
   directory as the project file if you are working with a project file.
   Later the export settings of the project will be automatically loaded
   into the plugin.

   Pressing the Help button will open the local document with default web
   browser.

General Settings
----------------

Template
~~~~~~~~

Available templates:

* 3DViewer.html

   This template is a 3D viewer without any additional UI library.

* 3DViewer(dat-gui).html

   This template has a `dat-gui <https://code.google.com/p/dat-gui/>`__
   panel, which makes it possible to toggle layer visibility, adjust layer
   opacity and add a horizontal plane movable in the vertical direction.

* FileExport.html

   This template builds 3D models on the web browser, but doesn't render
   them. Instead, it has some buttons to save 3D models in `STL
   format <http://en.wikipedia.org/wiki/STL_%28file_format%29>`__,
   `Wavrefront OBJ
   format <http://en.wikipedia.org/wiki/Wavefront_.obj_file>`__ or `COLLADA
   format <http://en.wikipedia.org/wiki/COLLADA>`__. It also has ability to
   save the texture image(s).

   Those formats are widely supported by 3DCG softwares such as
   `Blender <http://www.blender.org/>`__.

World
~~~~~

* Base size

   Enter a size in 3D world that corresponds to the map canvas width. The
   default value is 100.

* Vertical exaggeration

   Vertical exaggeration factor. This value affects terrain shape and z
   positions of all vector 3D objects. This also affects 3D object height
   of some object types with volume. Object types to be affected:

    | Point : Cylinder, Cube, Cone
    | Polygon : Extruded

   3D objects of the following types have volume, but their heights aren't
   affected by this factor:

    | Point : Sphere, JSON model, COLLADA model
    | Line : Pipe, Cone, Box

   The default value is 1.5.

* Vertical shift

   Vertical shift for all objects. If you want to export terrain of narrow
   area and high altitude, you should adjust the object positions to be
   displayed at the center of browser by changing this value. If you set
   the value to -1000, all objects are shifted down by 1000 in the unit of
   project CRS.

* Background

   Select either sky-like gradient or a solid color for the background of
   scene. Default is Sky.

* Display of coordinates

   If the ``Latitude and longitude (WGS84)`` option is selected,
   coordinates of clicked position on a 3D object are displayed in
   longitude and latitude (WGS84). If
   `Proj4js <https://github.com/proj4js/proj4js>`__ doesn't support current
   project CRS, this option is disabled.

Controls
~~~~~~~~

Two available controls:
`OrbitControls <https://raw.githubusercontent.com/minorua/Qgis2threejs/master/js/threejs/controls/OrbitControls.txt>`__,
`TrackballControls <https://raw.githubusercontent.com/minorua/Qgis2threejs/master/js/threejs/controls/TrackballControls.txt>`__.

The usage of each control is displayed below the combo box.

Layer Settings
--------------

DEM
~~~

You can select a DEM layer from 1-band rasters loaded in QGIS using
``Add Raster Layer`` (GDAL provider). Selected DEM layer is used as the
reference for z positions of vector objects. You can also select a flat
plane at zero altitude.

Resampling
^^^^^^^^^^

* Simple

   Select a DEM resolution from several levels. This resolution is used to
   resample the DEM, but is not for texture.

    * Surroundings option

      This option enlarges output DEM by placing DEM blocks around the main block of the map canvas extent. Size can be selected from odd numbers in the range of 3 to 9. If you select 3, total 9 (=3x3) blocks (a center block and 8 surrounding blocks) are output. Roughening can be selected from powers of 2 in the range of 1 to 64. If you select 2, grid point spacing is doubled. It means that the number of grid points in the same area becomes 1/4. If map canvas image is selected as the display type, texture image size for each block is maximum 256 x 256.

* Advanced (quad tree)

   Multiple resolution DEM export. Area you want to focus is output in high
   resolution and the surroundings are output in low resolution. Draw a
   rectangle on the map canvas to set focus area. Specifying a point is
   also possible. The higher QuadTree height, the higher resolution of the
   focus area. Grid size of each block is 64 x 64.

Display type
^^^^^^^^^^^^

You can choose from map canvas image, layer image, a image file or a
solid color.

* Map canvas image

   Map canvas image is used to texture the main DEM block in simple
   resampling mode. Each block of surroundings (in simple resampling mode)
   and quads (in advanced resampling mode) is textured with image rendered
   with the current map settings.

* Layer image

   Each block is textured with image rendered with the selected layer(s).

* Image file

   Texture with existing image file such as PNG and JPEG file. TIFF is not
   supported by some browser. See `Image format
   support <http://en.wikipedia.org/wiki/Comparison_of_web_browsers#Image_format_support>`__
   for details.

* Solid color

   To select a color, press the button on the right side.

**Options**

* Resolution

   Increases (or decreases) the size of image applied to each DEM block.
   This option is enabled when either ``Map canvas image`` or
   ``Layer image`` is selected. You can select a ratio to map canvas size
   from 50, 100, 200 and 400 (%). Image size in pixels follows the percent.

* Transparency

   Sets transparency for the DEM. 0 is opaque, and 100 is transparent.

* Transparent background / Enable transparency

   Makes transparent background of the image to be rendered (with map
   canvas image or layer image) or enables transparency of the image file
   effectively. Uncheckable with solid color.

* Enable shading

   Adds a shading effect to the DEM.

Clip
^^^^

Clips the DEM with a polygon layer. If you have polygon layer of the
area that elevation data exist or the area of a drainage basin, you
might want to use this option.

Sides and frame
^^^^^^^^^^^^^^^

* Build sides

   This option adds sides and bottom to the DEM. The z position of bottom
   in the 3D world is fixed. You can adjust the height of sides by changing
   the value of vertical shift option in the World panel. If you want to
   change color, please edit the output JS file directly.

* Build frame

   This option adds frame to the DEM. If you want to change color, please
   edit the output JS file directly.

Additional DEM
~~~~~~~~~~~~~~

If you want to export more than one DEM, check the checkbox on the left
of child item you want. For example of usage, it may be possible to
cover the terrain with supposed terrain surface of a summit level map,
or make a 3D heat map.

Some options that are available in main DEM panel cannot be used.
Resampling mode is limited to simple. Surroundings, sides and frame
options are not available.

Vector
~~~~~~

Vector layers are grouped into three types: Point, Line and Polygon.
Common settings for all vector layers:

* Z coordinate

    The mode combo box has these items:

    * Z value

      This doesn't appear if the geometries of the layer has no z coordinates or the layer type is polygon.

    * Relative to DEM

      `z = Elevation at vertex + addend`

    * +"field name"

      `z = Elevation at vertex + field value + addend`

      Only numeric fields are listed in the combo box.

    * Absolute value

      `z = value`

    * "field name"

      `z = field value + addend`

      Only numeric fields are listed in the combo box.

    The unit of the value is that of the project CRS.

* Style

   Usually, there are options to set object color and transparency. Refer
   to the links below for each object type specific settings. The unit of
   value for object size is that of the project CRS.

* Feature

   Select the features to be output.

    * All features

      All features of the layer are exported.

    * Features that intersect with map canvas extent

      Features displayed on the map canvas are exported.

        * Clip geometries

          This option is available with Line/Polygon layer. If checked, geometries are clipped by the extent of map canvas.

* Attribute and label

   If the export attributes option is checked, attributes are exported with
   feature geometries. Attributes are displayed when you click an object on
   web browser.

   If a field in the label combobox is selected, a label is displayed above
   each object and is connected to the object with a line. This combo box
   is not available when layer type is line.

Point
^^^^^

Point layers in the project are listed as the child items. The following
object types are available:

    Sphere, Cylinder, Cone, Box, Disk, Icon, JSON model, COLLADA model

See :ref:`object-types-point-layer` section in :doc:`ObjectTypes` page for each object type specific settings.

Line
^^^^

Line layers in the project are listed as the child items. The following
object types are available:

    Line, Pipe, Cone, Box, Profile

See :ref:`object-types-line-layer` section in :doc:`ObjectTypes` page for each object type specific settings.

Polygon
^^^^^^^

Polygon layers in the project are listed as the child items. The
following object types are available:

    Extruded, Overlay

See :ref:`object-types-polygon-layer` section in :doc:`ObjectTypes` page for each object type specific settings.
