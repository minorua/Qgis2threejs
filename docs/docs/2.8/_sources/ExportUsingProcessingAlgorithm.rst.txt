Export Scenes using Processing Algorithm
========================================

Do you want to export many scenes as web pages, image files or 3D model files?
You can do them using Qgis2threejs algorithms in Processing tool box.
Qgis2threejs provides three algorithms - "Export as Web Page", "Export as Image"
and "Export as 3D Model".


Step 1
~~~~~~

Add a DEM layer that covers the whole area you are going to export, a vector layer
to point out area of interest for each scene and any other layers to project.
The vector layer is called as coverage layer and should have title field that contains
string used as title of file to export.


Step 2
~~~~~~

Open Qgis2threejs exporter and set up a scene.


Step 3
~~~~~~

1. Open one of the Qgis2threejs algorithms from Processing toolbox.

2. Select the coverage layer and the title field, and configure other parameters.
   Coverage layer must be visible in QGIS project when "Current Feature Filter" option is checked.

3. Click on Run button.


|processing_export_web_dialog|


Algorithm Parameters
~~~~~~~~~~~~~~~~~~~~

Common Parameters
-----------------

* Coverage Layer

   A vector layer. Creates and exports scenes focused on each feature of this layer.

* Title Field

   A field that contains string used as title of file to export.

* Current Feature Filter

   Hides coverage layer features other than currently focused feature from texture image to be rendered.

* Output Directory

   Path to output directory.

**Advanced Parameters**

* Scale Mode

   * Fit to Geometry

      Zoom to current feature geometry.

   * Fixed scale (based on map canvas)

      Use current map canvas scale.

* Buffer (%)

   Default value is 10.

* Texture base width (px)

   Default value is 1024.

* Texture base height (px)

   In "Fit to Geometry" scale mode, leave this zero to respect aspect
   ratio of buffered geometry bounding box. In "Fixed scale" scale mode,
   aspect ratio of map canvas size is respected when this is set to zero.
   Default value is 0.

* Header Label

   An expression which represents header label in HTML.

* Footer Label

   An expression which represents footer label in HTML.

* Export Settings File (.qto3settings)

   Optional. Path to export settings file. Leave this empty to use current export settings.


Export as Web Page
------------------

* Template

   Select one of web page templates. See :ref:`export_web_dialog` in :doc:`Exporter` page
   and :doc:`WebViewerTemplates`.


Export as Image
---------------

* Image width

   Output image width in pixel. Default value is 2480.

* Image height

   Output image height in pixel. Default value is 1748.


Export as 3D Model
------------------

No specific settings.
