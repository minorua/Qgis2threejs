Tutorial
========

Let's start using Qgis2threejs plugin!


Installing the plugin
---------------------

Open the QGIS plugin dialog (``Plugins > Manage and install plugins...``),
and then install Qgis2threejs plugin.

.. hint:: Need help? See the `10.1.2. Installing New Plugins`__ section of
   the QGIS training manual.

__ http://docs.qgis.org/2.8/en/docs/training_manual/qgis_plugins/fetching_plugins.html#basic-fa-installing-new-plugins


Obtaining elevation data
------------------------

If you already have raster DEM data, you can skip this step.

NASA released elevation data generated from NASA's
`Shuttle Radar Topography Mission`__ digital topographic data.
We can use the data freely. Elevation data version 2.1 can be
downloaded from the `distribution site`__.

__ http://www2.jpl.nasa.gov/srtm/index.html
__ https://dds.cr.usgs.gov/srtm/

Download a zip file that contains elevation data of the area you are
interested in from under the ``version2_1/SRTM3`` directory. The zip
file contains a ``.hgt`` file, which is readable by the GDAL.

.. tip:: If the area extends over two or more files, you might want to
   create a virtual mosaic using `Build Virtual Raster (Catalog)`__
   tool of GdalTools.

__ http://docs.qgis.org/2.8/en/docs/user_manual/plugins/plugins_gdaltools.html#miscellaneous

.. tip:: Do you have time to discover new high-resolution SRTM
   elevation data? You can download 1 arc-second SRTM data from
   the `EarthExplorer`__ (User registration and login are required).

__ http://earthexplorer.usgs.gov/


Loading DEM data
----------------

Drag & drop the downloaded zip file to QGIS window
(or load the file using ``Add Raster Layer`` dialog).
You don't need to unzip it.


CRS setting
-----------

Horizontal unit of SRTM data is degree, whereas vertical unit is meter.
For appropriate visualization, you need to transform the DEM data to
a projected CRS. QGIS can perform the CRS transformation on the fly.

So, let's enable the On The Fly CRS transformation and change the map CRS
to a projected CRS.

Click the |CRS icon| CRS status icon in the bottom-right corner of the window to
open the project properties dialog. Activate the ``Enable 'on the fly' CRS
transformation`` checkbox and then select a suitable CRS (i.e. UTM) for
the DEM extent. If you don't know which CRS is best suited, select the
Pseudo Mercator projection (``EPSG:3857``), which is adopted by many web maps.

.. note:: In the Mercator projection, size of every feature is horizontally
   larger than actual size except features on the equator.
   At latitude 40 degrees it is enlarged 1.3 times, at 60 degrees enlarged twice.


Layer styling
-------------

Open the raster properties dialog for the DEM layer and colorize the DEM layer
richly.

An example (``Singleband pseudocolor`` render type and inverted ``BrBG`` color map):

|map canvas1|


Exporting
---------

Zoom to a part of the DEM layer extent as the map canvas is filled by the colorized DEM.

Click the |plugin icon| plugin icon in the web toolbar.

Then, click ``Run`` button in the dialog.

|dialog image1|

3D terrain appears in your web browser!

|browser image1|


Adding shading effect
---------------------

Can't catch the shape of terrain from the view well?
OK, then let's add shading effect to the DEM.

Open the plugin dialog again, activate the ``Enable shading`` checkbox
in the ``Display type`` group and then do export.

|browser image2|


Conclusion
----------

Tutorial is over. 3D visualization is difficult? Do you see potential in
3D visualization with QGIS? If you can use high-quality data,
you can create beautiful 3D scenes!

.. tip:: Next, how about adding a background map layer to the map canvas.
   You can do it easily with `QuickMapServices plugin`__. Also, how about adding
   vector data to the scene. :doc:`ObjectTypes` page has example images of various
   object types. See :doc:`ExportSettings` for the detail.

__ https://plugins.qgis.org/plugins/quick_map_services/

.. tip:: You can publish the exported scene just by uploading the exported files to a web server.

.. note:: Please do not forget to ensure that you comply with
   the Terms and use for the data before publishing the scene to the web.
