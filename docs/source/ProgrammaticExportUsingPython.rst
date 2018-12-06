Programmatic Export Using Python
==================================

Do you want to export many scenes as web pages? Or you want to export many scenes as image files?
You can do them programmatically using Python!

Step 1
~~~~~~

You need to prepare an export settings file. The export settings
contains various settings, so you might want to create the settings file
using the plugin dialog.

Procedure:

1. Open a QGIS project and click the Qgis2threejs icon in the web tool bar
   to open the Qgis2threejs exporter.
2. Configure the export settings.
4. Click on the ``File - Export Settings - Save...`` menu entry, and then select a filename
   to save the export settings (file extension is ``.qto3settings``).

Step 2
~~~~~~

You are ready to play with Python. Let's open the QGIS Python console.

.. code:: Python

    from PyQt5.QtCore import QSize
    from Qgis2threejs.export import ThreeJSExporter, ImageExporter, ModelExporter
    from Qgis2threejs.rotatedrect import RotatedRect

    from qgis.core import QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsPoint

    # texture base size
    TEX_WIDTH, TEX_HEIGHT = (1024, 1024)

    path_to_settings = None    # path to .qto3settings file

    mapSettings = iface.mapCanvas().mapSettings()

    # extent
    center = mapSettings.extent().center()
    width = mapSettings.extent().width()
    height = width * TEX_HEIGHT / TEX_WIDTH
    rotation = 0

    RotatedRect(center, width, height, rotation).toMapSettings(mapSettings)

    # texture base size
    mapSettings.setOutputSize(QSize(TEX_WIDTH, TEX_HEIGHT))

    #
    # 1. export scene as web page

    filename = "D:/export/html_filename.html"

    exporter = ThreeJSExporter()
    exporter.loadSettings(path_to_settings)
    exporter.setMapSettings(mapSettings)
    exporter.export(filename)

    #
    # 2. export scene as image

    filename = "D:/export/image_filename.png"

    # output image size
    OUT_WIDTH, OUT_HEIGHT = (1024, 768)

    # camera position and camera target
    # this coordinate system is y-up!
    CAMERA = {"position": {"x": -50, "y": 30, "z": 50},   # above left front of DEM block
              "target": {"x": 0, "y": 0, "z": 0}}         # below (or above) center of DEM block

    exporter = ImageExporter()
    exporter.loadSettings(path_to_settings)
    exporter.setMapSettings(mapSettings)

    exporter.initWebPage(OUT_WIDTH, OUT_HEIGHT)
    exporter.export(filename, cameraState=CAMERA)
