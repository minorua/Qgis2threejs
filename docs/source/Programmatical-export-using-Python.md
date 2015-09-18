**This feature will be added in version 1.4**

Do you want to export many scenes to web? You can do it programmatically using Python!

### Step 1
You need to prepare an export settings file. The export settings contains various items, so you might want to create the settings file using the plugin dialog.

Procedure:

1. Open a project and click the Qgis2threejs button in the web tool bar to open the plugin dialog.
2. Configure the export settings.
3. Click the Run button to see the export on the web browser and check that the the settings are good.
4. Open the plugin dialog again. Click the settings button at the bottom-left corner, and then save the export settings to a file (file extension is `.qto3settings`).

### Step 2
You are ready to play with Python. Let's open the QGIS Python console (you need QGIS version 2.4 or later).

```Python
from PyQt4.QtCore import QSize
from qgis.core import QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsPoint
from Qgis2threejs.api import Exporter

# Path to the prepared .qto3settings file
settingsPath = "D:/pref_offices.qto3settings"

# Places to export (in WGS 84)
places = [(u"Kyoto", QgsPoint(135.7555, 35.0210)),
          (u"Osaka", QgsPoint(135.5199, 34.6863)),
          (u"Nara", QgsPoint(135.8329, 34.6852)),
          (u"Ehime", QgsPoint(132.7657, 33.8416))]

# Output filename template
path_tmpl = "D:/output_scenes/{0}.html"

# Coordinate transformer: WGS 84 to JGD2000 / UTM zone 53N 
wgs84 = QgsCoordinateReferenceSystem(4326, QgsCoordinateReferenceSystem.EpsgCrsId)
utm53 = QgsCoordinateReferenceSystem(3099, QgsCoordinateReferenceSystem.EpsgCrsId)
transform = QgsCoordinateTransform(wgs84, utm53)

# Make sure that map canvas CRS is EPSG:3099
canvas = iface.mapCanvas()
canvas.setCrsTransformEnabled(True)
canvas.setDestinationCrs(utm53)

# Get map settings from the map canvas
mapSettings = canvas.mapSettings()

# Canvas size (base image size)
canvasSize = QSize(600, 600)
mapSettings.setOutputSize(canvasSize)

# Size of extent, and rotation
width = 10000.
height = width * canvasSize.height() / canvasSize.width()
rotation = 0

# Create an exporter
exporter = Exporter(iface, settingsPath)
exporter.setMapSettings(mapSettings)

for name, point in places:
  # Coordinate transform
  center = transform.transform(point)
  # Set extent
  exporter.setExtent(center, width, height, rotation)
  # Output HTML file path
  filepath = path_tmpl.format(name)
  # Export
  err = exporter.export(filepath, openBrowser=False)
  if err == Exporter.NO_ERROR:
    print "{0} has been exported to {1}".format(name, filepath)
  else:
    print "Failed to export {0}: {1}".format(name, err)
```

Exported scene examples:

* [Kyoto](https://dl.dropboxusercontent.com/u/21526091/qgis-plugins/samples/python_export/pref_offices/Kyoto.html), 
[Osaka](https://dl.dropboxusercontent.com/u/21526091/qgis-plugins/samples/python_export/pref_offices/Osaka.html), 
[Nara](https://dl.dropboxusercontent.com/u/21526091/qgis-plugins/samples/python_export/pref_offices/Nara.html), 
[Ehime](https://dl.dropboxusercontent.com/u/21526091/qgis-plugins/samples/python_export/pref_offices/Ehime.html)

Sources: Geospatial Information Authority of Japan. [GSI Tiles](http://portal.cyberjapan.jp/help/development/) (Orthophoto and elevation tile)  
