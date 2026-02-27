## CHANGELOG

### Version 2.9.4
- Fixed a regression in PointCloudLayerBuilder constructor and Potree base path
- Fixed script loading order to ensure dependencies are loaded correctly

### Version 2.9.3
- Refined tab and group box layout in vector layer properties dialog
- Fixed an issue preventing 3D model labels from being displayed

### Version 2.9.2
- Fixed vector properties dialog layout

### Version 2.9.1
- Fixed a f-strings syntax error caused by nested quotes in Python versions earlier than 3.12

### Version 2.9
#### Added
- Qt6 support
- TaskManager class for improved task management
- A queue for sequential web transmission of generated data
- An option to use original DEM values
#### Extensive Refactoring
- Reorganized directory structure and file layout
- Added and improved code comments
#### Improved Multithreading
- Task management is now handled in the UI thread
- Worker thread is now responsible only for data generation
#### Others
- Updated DEM geometry generation to skip faces with no-data vertices
- Improved progress bar in window to show task status, and web-side progress bar to show data loading status
- Renamed keyframe group to track
- Implemented chunked transfer for saving glTF data
- Fixed the "visible on load" option behavior when using the 3D Viewer template

### Version 2.8
- Added option to select either WebEngine or WebKit for preview from the menu
- WebEngine view is now preferred option when available
- Removed console panel
- Developer tools are now accessible even when not in debug mode
- Log python side warnings and errors also in the JavaScript console
- An icon will appear in the status bar to indicate warnings or errors
- Fixed a bug where labels were not displayed on Extruded/Overlay polygons
- Fixed a bug that prevented the plugin settings dialog from opening due to the deprecation of SafeConfigParser

### Version 2.7.3
- Fixed a regression related to vertical line
- Fixed a popup layout issue

### Version 2.7.2
- Fixed easing of sequential line growing
- Fixed URL of GSI elevation tile
- Fixed some other bugs
- Added some GUI tests
- Exporter can now work with Qt WebEngine view (Experimental. Needs some changes on QGIS code)
- Use JS class so that we can use a recent three.js version in the future
- Plugin document migrated to GitHub pages

### Version 2.7.1
- Added option to export DEM texture in JPEG format
- Bug fixes

### Version 2.7
#### Animation for Narratives
- Camera motion, growing line, opacity transition and texture change animations are now available
#### 3D Viewer
- Added measure distance tool
- Added action to zoom to layer objects
#### Exporter
- Added tabs to property dialogs and regrouped widgets in the dialogs
- Fixed cancellation of building 3D objects
#### Scene
- Units of 3D world space are same as map units
- Added option to add fog
- Added option to use point light above camera
#### DEM
- DEM can have multiple textures
- Added menu action to add a flat plane
- Renamed surrounding blocks to tiles
#### Vector
- Put labels into 3D world
- Added some labeling settings (color, font size, background color, etc.)
- Added Thick Line type for line layer
#### Others
- Fixed loading point cloud data
- Removed experimental ray tracing renderer template

### Version 2.6
- Added navigation widget
- Added fixed base extent option and 1:1 aspect ratio option
- Added outline effect option
- DEM texture width is now specifiable with a numerical value
- Added edge option and quad wireframe option to DEM
- Added Ray Tracing Renderer template (experimental)
- Added view menu
- Fixed DEM edge processing between central block and surrounding blocks
- Some other bug fixes

### Version 2.5
- Potree data support
- Bug fixes

### Version 2.4.2
- Fixed scene export with glTF/COLLADA model file (fix #193)
- Fixed AR camera background in Mobile template (fix #196)

### Version 2.4.1
- Fixed clipping self-crossing lines (fix #117)
- Fixed retrieving a symbol for a feature
- Renamed DEM roughening option to roughness

### Version 2.4
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

### Version 2.3.1
- Do not import Qt module from PyQt5.Qt (fix #162 and #134)
- Fixed initial camera target position (fix #163)

### Version 2.3
- Added export algorithms for Processing
- Added automatic z shift adjustment option
- Added Point type for point layer
- Fixed clipped DEM side (fix #159)
- Fixed Overlay
- Fixed model file load with Mobile template
- Fixed crash when continuously zooming map canvas with the exporter window open
- API and offscreen rendering

### Version 2.2
- Added Triangular Mesh type for polygon layer
- Added Plane type for point layer (width, height, orientation)
- Restored Icon type for point layer
- Added Model File type for point layer (COLLADA and glTF)
- Drag & drop model preview

### Version 2.1
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

### Version 2.0.1
- Bug fixes
- Improved DEM load performance

### Version 2.0
- Built for QGIS 3.x
- Improved GUI - new exporter with preview
- Save scene as glTF
- Using expression in vector layer properties
- Updated three.js library (r90)
- Disabled/removed these features: DEM advanced resampling mode, 3 object types (Icon, JSON/COLLADA Model), some object specific settings for Profile and Overlay, FileExporter (Save as STL, OBJ, COLLADA), GSIElevProvider.
    These features were available in version 1.4, but are not available in version 2.0.

### Version 1.4.2
- Fixed unicode decode error

### Version 1.4.1
- Rendering with antialias enabled (Thanks to @stefanocudini)
- Improved height range of custom plane (dat-gui, refs #53)
- Skip invalid polygons (fix #71)
- Fixed feature attribute writing (fix #73)

### Version 1.4
- Documentation improved and moved to readthedocs.org
- Activate DEM's shading by default to make it easy to create shaded 3D map
- Added menu commands for touch screen devices (dat-gui)
- Turn off scene.autoUpdate to reduce matrix calculation cost
- API for Python
- Added some basic test cases
- Fixed error while exporting with DEM's build frame option (fix #48)
- Fixed cone type object for point layer (fix #50)

### Version 1.3.1
- Fixed error on applying plugin settings

### Version 1.3
#### General
- Added object type for line: Box
- Added clear settings command to settings menu
- Automatically save settings near project file when exporting is done, and restore the settings next time
- Added GSIElevTilePlugin (DEM provider. Optional feature)
#### DEM
- Texture rendering with multiple selected layers
- Added option to clip DEM with polygon layer
- Added option to increase resolution of texture
#### Web page
- Added "save image" dialog in which image size can be entered
- Fixed bug of restoring view from URL parameters
#### Others
- Added lower Z option (Profile)
- Added texture option, side option and side lower Z option (Overlay)
- Takes map rotation into account (Disk, JSON, COLLADA)


### Version 1.2
- Map rotation support
- Added object type for point: COLLADA model (experimental)
- Added commands to save/load export settings
- Fixed 2.5D geometry export bug
- Fixed DEM layer export with FileExport template
- Updated three.js library (r70)


### Version 1.1.1
- Fixed bugs related to icon and attribute export

### Version 1.1
- Updated the STLExporter to support other file formats (collada, obj) and is easier to extend (by Olivier Dalang @olivierdalang)

### Version 1.0
#### General
- Added object types for point: Disk, Icon
- Added object type for polygon: Overlay
- Added base size option (World)
- Added option to display coordinates in WGS84 lat/lon (World)
- Added layer image option (DEM)
- Added clip geometries option (Vector)
- Code refactoring (more oo code)
#### Web page
- Added layer opacity sliders in dat-gui panel
- Added wireframe mode
- Updated popup style

### Version 0.7.2
- Added object type for line: Profile
- Added shading option (DEM)
- 3D print compatible STL export
- Bug fix for QGIS 2.5

### Version 0.7.1
- Added template: STLExport
- Added object types for line: Pipe, Cone
- Added URL parameters

### Version 0.7
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

### Version 0.6
- Fixed confusing GUI

### Version 0.5
- Vector layer feature export
- Added object types: Sphere, Cylinder, Cube, Cone, Line, (Extruded) Polygon

### Version 0.4
- Added advanced resampling mode (quad tree)
- Added vertical exaggeration option
- Added settings dialog and browser path option in it
- DEM reprojection in memory
