# CHANGELOG

## [3.1] - 2026-07-02
- Updated three.js library to r184
- Replaced meshline library with pmndrs/meshline v3.3.1
- Switched polygon triangulation to QgsTessellator using the Earcut algorithm
- Removed Potree data support
- Removed local mode option from export dialog
- Removed Mobile template
- Removed browser path setting from plugin settings dialog

## [3.0] - 2026-05-18
- The preview now runs in a separate process
- Dropped support for QWebView (WebKit) and PyQt5
- The minimum supported version of QGIS is now 4.0
- Fixed a preview freeze caused by data loading errors
- Fixed an error that occurred when interrupting the layer build process

## [2.10] - 2026-04-13
- Added a button to launch the Qgis2OnlineMap plugin from the export dialog
- Use timestamp-based subdirectories for the default export output directory
- Improved DEM NoData handling (#407)
- Set transparent to false when opacity is 1 to ensure opaque objects are rendered before transparent ones (#408)
- Fixed the sceneLoaded event being dispatched twice (#409)
- Fixed label opacity being affected by layer opacity (#411)

## [2.9.4] - 2026-03-04
- Fixed a regression in PointCloudLayerBuilder constructor and Potree base path
- Fixed script loading order to ensure dependencies are loaded correctly
- Fixed array type check for data received via Qt WebKit Bridge
- Prevent unsupported point cloud layers from being added to the layer tree

## [2.9.3] - 2026-02-23
- Refined tab and group box layout in vector layer properties dialog
- Fixed an issue preventing 3D model labels from being displayed

## [2.9.2] - 2026-02-15
- Fixed vector properties dialog layout

## [2.9.1] - 2026-02-12
- Fixed a f-strings syntax error caused by nested quotes in Python versions earlier than 3.12

## [2.9] - 2026-02-06
### Added
- Qt6 support
- TaskManager class for improved task management
- A queue for sequential web transmission of generated data
- An option to use original DEM values
### Extensive Refactoring
- Reorganized directory structure and file layout
- Added and improved code comments
### Improved Multithreading
- Task management is now handled in the UI thread
- Worker thread is now responsible only for data generation
### Others
- Updated DEM geometry generation to skip faces with no-data vertices
- Improved progress bar in window to show task status, and web-side progress bar to show data loading status
- Renamed keyframe group to track
- Implemented chunked transfer for saving glTF data
- Fixed the "visible on load" option behavior when using the 3D Viewer template

## [2.8] - 2024-10-30
- Added option to select either WebEngine or WebKit for preview from the menu
- WebEngine view is now preferred option when available
- Removed console panel
- Developer tools are now accessible even when not in debug mode
- Log python side warnings and errors also in the JavaScript console
- An icon will appear in the status bar to indicate warnings or errors
- Fixed a bug where labels were not displayed on Extruded/Overlay polygons
- Fixed a bug that prevented the plugin settings dialog from opening due to the deprecation of SafeConfigParser

## [2.7.3] - 2024-01-31
- Fixed a regression related to vertical line
- Fixed a popup layout issue

## [2.7.2] - 2024-01-16
- Fixed easing of sequential line growing
- Fixed URL of GSI elevation tile
- Fixed some other bugs
- Added some GUI tests
- Exporter can now work with Qt WebEngine view (Experimental. Needs some changes on QGIS code)
- Use JS class so that we can use a recent three.js version in the future
- Plugin document migrated to GitHub pages

## [2.7.1] - 2022-04-07
- Added option to export DEM texture in JPEG format
- Bug fixes

## [2.7] - 2022-03-22
### Animation for Narratives
- Camera motion, growing line, opacity transition and texture change animations are now available
### 3D Viewer
- Added measure distance tool
- Added action to zoom to layer objects
### Exporter
- Added tabs to property dialogs and regrouped widgets in the dialogs
- Fixed cancellation of building 3D objects
### Scene
- Units of 3D world space are same as map units
- Added option to add fog
- Added option to use point light above camera
### DEM
- DEM can have multiple textures
- Added menu action to add a flat plane
- Renamed surrounding blocks to tiles
### Vector
- Put labels into 3D world
- Added some labeling settings (color, font size, background color, etc.)
- Added Thick Line type for line layer
### Others
- Fixed loading point cloud data
- Removed experimental ray tracing renderer template

## [2.6] - 2021-02-12
- Added navigation widget
- Added fixed base extent option and 1:1 aspect ratio option
- Added outline effect option
- DEM texture width is now specifiable with a numerical value
- Added edge option and quad wireframe option to DEM
- Added Ray Tracing Renderer template (experimental)
- Added view menu
- Fixed DEM edge processing between central block and surrounding blocks
- Some other bug fixes

## [2.5] - 2020-06-24
- Potree data support
- Bug fixes

## [2.4.2] - 2020-01-23
- Fixed scene export with glTF/COLLADA model file (#193)
- Fixed AR camera background in Mobile template (#196)

## [2.4.1] - 2019-10-29
- Fixed clipping self-crossing lines (#117)
- Fixed retrieving a symbol for a feature
- Renamed DEM roughening option to roughness

## [2.4] - 2019-09-24
- Build data to load into preview in background
- Added preserve current viewpoint option to web export
- Added side color option to DEM
- Added rotation order option to Model File
- Triangulate polygons using QgsTessellator for Polygon
- Triangulate polygons using earcut for Overlay
- Restored Overlay border option
- Fixed dat-gui panel for mobile device
- Renamed scene block size (width) option to base width
- Renamed Extruded border color option to edge color
- Renamed Profile type to Wall
- Renamed Triangular Mesh type to Polygon
- Updated three.js library to r108
- Bumped QGIS minimum version to 3.4

## [2.3.1] - 2019-02-20
- Do not import Qt module from PyQt5.Qt (#162, #134)
- Fixed initial camera target position (#163)

## [2.3] - 2018-12-06
- Added export algorithms for Processing
- Added automatic z shift adjustment option
- Added Point type for point layer
- Fixed clipped DEM side (#159)
- Fixed Overlay
- Fixed model file load with Mobile template
- Fixed crash when continuously zooming map canvas with the exporter window open
- API and offscreen rendering

## [2.2] - 2018-10-31
- Added Triangular Mesh type for polygon layer
- Added Plane type for point layer (width, height, orientation)
- Restored Icon type for point layer
- Added Model File type for point layer (COLLADA and glTF)
- Drag & drop model preview

## [2.1] - 2018-10-17
- Added a new template for mobile device with experimental AR feature
- Added North arrow inset (Thanks to @DigDigDig)
- Accelerate building objects by caching last created geometry
- Added basic material type option to scene settings - Lambert/Phong/Toon shading
- Added visible on load option
- Added dashed option to Line type
- Added page load progress bar
- Restored GSI elevation tile DEM provider
- Use transform CSS property to position labels
- Fixed crash on closing exporter in Linux

## [2.0.1] - 2018-04-19
- Bug fixes
- Improved DEM load performance

## [2.0] - 2018-04-12
- Built for QGIS 3.x
- Improved GUI - new exporter with preview
- Save scene as glTF
- Using expression in vector layer properties
- Updated three.js library (r90)
- Disabled/removed these features: DEM advanced resampling mode, 3 object types (Icon, JSON/COLLADA Model), some object specific settings for Profile and Overlay, FileExporter (Save as STL, OBJ, COLLADA), GSIElevProvider.
    These features were available in version 1.4, but are not available in version 2.0.

## [1.4.2] - 2016-07-14
- Fixed unicode decode error

## [1.4.1] - 2016-07-01
- Rendering with antialias enabled (Thanks to @stefanocudini)
- Improved height range of custom plane (dat-gui, #53)
- Skip invalid polygons (#71)
- Fixed feature attribute writing (#73)

## [1.4] - 2015-10-02
- Documentation improved and moved to readthedocs.org
- Activate DEM's shading by default to make it easy to create shaded 3D map
- Added menu commands for touch screen devices (dat-gui)
- Turn off scene.autoUpdate to reduce matrix calculation cost
- API for Python
- Added some basic test cases
- Fixed error while exporting with DEM's build frame option (#48)
- Fixed cone type object for point layer (#50)

## [1.3.1] - 2015-06-19
- Fixed error on applying plugin settings

## [1.3] - 2015-05-29
### General
- Added object type for line: Box
- Added clear settings command to settings menu
- Automatically save settings near project file when exporting is done, and restore the settings next time
- Added GSIElevTilePlugin (DEM provider. Optional feature)
### DEM
- Texture rendering with multiple selected layers
- Added option to clip DEM with polygon layer
- Added option to increase resolution of texture
### Web page
- Added "save image" dialog in which image size can be entered
- Fixed bug of restoring view from URL parameters
### Others
- Added lower Z option (Profile)
- Added texture option, side option and side lower Z option (Overlay)
- Takes map rotation into account (Disk, JSON, COLLADA)


## [1.2] - 2015-03-28
- Map rotation support
- Added object type for point: COLLADA model (experimental)
- Added commands to save/load export settings
- Fixed 2.5D geometry export bug
- Fixed DEM layer export with FileExport template
- Updated three.js library (r70)


## [1.1.1] - 2015-02-27
- Fixed bugs related to icon and attribute export

## [1.1] - 2015-02-17
- Updated the STLExporter to support other file formats (collada, obj) and is easier to extend (by Olivier Dalang @olivierdalang)

## [1.0] - 2015-02-07
### General
- Added object types for point: Disk, Icon
- Added object type for polygon: Overlay
- Added base size option (World)
- Added option to display coordinates in WGS84 lat/lon (World)
- Added layer image option (DEM)
- Added clip geometries option (Vector)
- Code refactoring (more oo code)
### Web page
- Added layer opacity sliders in dat-gui panel
- Added wireframe mode
- Updated popup style

## [0.7.2] - 2014-10-01
- Added object type for line: Profile
- Added shading option (DEM)
- 3D print compatible STL export
- Bug fix for QGIS 2.5

## [0.7.1] - 2014-05-16
- Added template: STLExport
- Added object types for line: Pipe, Cone
- Added URL parameters

## [0.7] - 2014-04-30
- Export with no DEM and multiple DEMs
- Added DEM options: display type, transparency, frame, surroundings and vertical shift
- Added DEM sides option (Thanks to @kostar111)
- Added template: custom plane (Thanks to @lucacasagrande)
- Added controls: OrbitControls
- Added object type for point: JSON model (experimental)
- Integrated DEM and Vector tabs
- Moved plugin items into web menu/toolbar

- Attribute export and labeling
- Queryable objects
- Fixed texture loading

## [0.6] - 2014-02-28
- Fixed confusing GUI

## [0.5] - 2014-01-22
- Vector layer feature export
- Added object types: Sphere, Cylinder, Cube, Cone, Line, (Extruded) Polygon

## [0.4] - 2014-01-11
- Added advanced resampling mode (quad tree)
- Added vertical exaggeration option
- Added settings dialog and browser path option in it
- DEM reprojection in memory

## [0.3] - 2013-12-23

## [0.2] - 2013-12-23

## [0.1] - 2013-12-21
