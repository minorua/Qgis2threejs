Export Scenes Programmatically using Python
===========================================

You can also export many scenes programmatically using Python!

Step 1
~~~~~~

You need to prepare an export settings file. The export settings
contains various settings, so you might want to create the settings file
using the Qgis2threejs exporter.

1. Open a QGIS project and click the Qgis2threejs icon in the web tool bar
   to open the Qgis2threejs exporter.

2. Add layers to scene, configure their settings, scene settings and decorations.

3. Click on the ``File - Export Settings - Save...`` menu entry, and then select a filename
   to save the export settings (file extension is ``.qto3settings``).

Step 2
~~~~~~

You are ready to play with Python. Let's open the QGIS Python console.

.. code:: Python

    from PyQt5.QtCore import QSize
    from Qgis2threejs.export import ThreeJSExporter, ImageExporter    # or ModelExporter
    from Qgis2threejs.rotatedrect import RotatedRect

    # texture base size
    TEX_WIDTH, TEX_HEIGHT = (1024, 1024)

    path_to_settings = None    # path to .qto3settings file

    # get map settings from current map canvas
    mapSettings = iface.mapCanvas().mapSettings()

    # extent to export
    center = mapSettings.extent().center()
    width = mapSettings.extent().width()
    height = width * TEX_HEIGHT / TEX_WIDTH
    rotation = 0

    # apply the above extent to map settings
    RotatedRect(center, width, height, rotation).toMapSettings(mapSettings)

    # texture base size
    mapSettings.setOutputSize(QSize(TEX_WIDTH, TEX_HEIGHT))

    #
    # 1. export scene as web page
    #

    filename = "D:/export/html_filename.html"

    exporter = ThreeJSExporter()
    exporter.loadSettings(path_to_settings)     # export settings (for scene, layers, decorations and so on)
    exporter.setMapSettings(mapSettings)        # extent, texture size, layers to be rendered and so on
    exporter.export(filename)

    #
    # 2. export scene as image
    #

    filename = "D:/export/image_filename.png"

    # camera position and camera target in world coordinate system (y-up)
    CAMERA = {"position": {"x": -50, "y": 30, "z": 50},   # above left front of (central) DEM block
              "target": {"x": 0, "y": 0, "z": 0}}         # below (or above) center of (central) DEM block

    exporter = ImageExporter()
    exporter.loadSettings(path_to_settings)
    exporter.setMapSettings(mapSettings)

    exporter.initWebPage(1024, 768)                       # output image size
    exporter.export(filename, cameraState=CAMERA)
