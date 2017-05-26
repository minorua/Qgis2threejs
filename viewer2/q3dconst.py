# Layer type
TYPE_DEM = 0
TYPE_POINT = 1
TYPE_LINESTRING = 2
TYPE_POLYGON = 3
TYPE_IMAGE = 10

# Default layer properties
DEFAULT_PROPERTIES = {
  TYPE_DEM: '{"checkBox_Clip":false,"checkBox_Frame":false,"checkBox_Shading":true,"checkBox_Sides":true,"checkBox_Surroundings":false,"checkBox_TransparentBackground":false,"comboBox_ClipLayer":"####","comboBox_DEMLayer":"#####","comboBox_TextureSize":100,"horizontalSlider_DEMSize":2,"lineEdit_Color":"","lineEdit_ImageFile":"","lineEdit_centerX":"","lineEdit_centerY":"","lineEdit_rectHeight":"","lineEdit_rectWidth":"","radioButton_MapCanvas":true,"radioButton_Simple":true,"spinBox_Height":4,"spinBox_Roughening":4,"spinBox_Size":5,"spinBox_demtransp":0,"visible":true}',
  TYPE_POINT: '{"checkBox_Clip":true,"checkBox_ExportAttrs":false,"comboBox_Label":null,"comboBox_ObjectType":0,"heightWidget":{"comboData":2,"comboText":"Relative to DEM","editText":"0","type":4},"labelHeightWidget":{"comboData":2,"comboText":"Height from point","editText":"100.0","type":6},"radioButton_IntersectingFeatures":true,"styleWidget0":{"comboData":1,"comboText":"Feature style","editText":"","type":2},"styleWidget1":{"comboData":1,"comboText":"Feature style","editText":"","type":5},"styleWidget2":{"comboData":1,"comboText":"Fixed value","editText":"10.0","type":1},"styleWidget3":{},"styleWidget4":{},"styleWidget5":{},"visible":true}',
  TYPE_LINESTRING: '{"checkBox_Clip":true,"checkBox_ExportAttrs":false,"comboBox_Label":null,"comboBox_ObjectType":0,"heightWidget":{"comboData":2,"comboText":"Relative to DEM","editText":"0","type":4},"labelHeightWidget":{},"radioButton_IntersectingFeatures":true,"styleWidget0":{"comboData":1,"comboText":"Feature style","editText":"","type":2},"styleWidget1":{"comboData":1,"comboText":"Feature style","editText":"","type":5},"styleWidget2":{},"styleWidget3":{},"styleWidget4":{},"styleWidget5":{},"visible":true}',
  TYPE_POLYGON: '{"checkBox_Clip":true,"checkBox_ExportAttrs":false,"comboBox_Label":null,"comboBox_ObjectType":0,"heightWidget":{"comboData":2,"comboText":"Relative to DEM","editText":"0","type":4},"labelHeightWidget":{"comboData":3,"comboText":"Height from top","editText":"100.0","type":6},"radioButton_IntersectingFeatures":true,"styleWidget0":{"comboData":1,"comboText":"Feature style","editText":"","type":2},"styleWidget1":{"comboData":1,"comboText":"Feature style","editText":"","type":5},"styleWidget2":{"comboData":1,"comboText":"Fixed value","editText":"10.0","type":1},"styleWidget3":{},"styleWidget4":{},"styleWidget5":{},"visible":true}',
  TYPE_IMAGE: "{}"
}

# Notification type   #TODO: update comments
# Q3D -> QGIS (Live Exporter)
N_LAYER_DOUBLECLICKED = 1   # params: Layer properties
N_LAYER_CREATED = 2         # params: {"pyLayerId": int, "jsLayerId": int}

# QGIS -> Q3D (Live Exporter)
N_CANVAS_EXTENT_CHANGED = 10
N_CANVAS_IMAGE_UPDATED = 11
N_LAYER_PROPERTIES_CHANGED = 12

# QGIS -> Q3D (Plugin Layer)
N_RENDERING_CANCELED = 20   # params: {"renderId", int}

# Request/Response data type
# Q3D -> QGIS -> Q3D
JS_CREATE_LAYER = 1         # params: Layer properties
JS_UPDATE_LAYER = 2         # params: Layer properties
JSON_LAYER_LIST = 3         # params: None

# Q3D -> QGIS -> Q3D (Live Exporter)
JS_CREATE_PROJECT = 11      # params: None
JS_UPDATE_PROJECT = 12      # params: None
JS_START_APP = 13           # params: None

# Q3D -> QGIS -> Q3D (Plugin Layer)
JS_INITIALIZE = 21          # params: None
JS_SAVE_IMAGE = 22          # params: None

# QGIS -> Q3D -> QGIS (Plugin Layer)
BIN_SCENE_IMAGE = 51        # params: Layer properties

# Responce only
# Q3D -> QGIS (Plugin Layer)
BIN_INTERMEDIATE_IMAGE = 61

# Not used
BIN_CANVAS_IMAGE = 91       # params: None

# Response data format
FORMAT_JS = 0
FORMAT_JSON = 1
FORMAT_BINARY = 2
