# Test Data and Resource Inventory

This directory contains QGIS projects, Qgis2threejs scene settings, raster/vector/point-cloud input data, and some supporting files. Paths in the tables are relative to this README. For explanations of the tests that use these resources, see [`../README.md`](../README.md).

## testproject1

`testproject1.qgs` is a QGIS project whose project CRS is **EPSG:2450 — JGD2000 / Japan Plane Rectangular CS VIII**. It combines point, line, and polygon samples with elevation rasters to test layer settings, click/attribute queries, visibility toggles, 3D object geometry, and web/image/glTF exports.

### Project and Scene Settings

- **File:** `testproject1/testproject1.qgs`
  - **Format and metadata:** QGIS XML project. Project CRS: EPSG:2450. Registers points, lines, polygons, Natural Earth railroads, rasters, and other layers.
  - **Use:** Project used by default in `cli/test_11_export.py` and `cli/test_20_bridge.py`, and by `gui/test_gui1.py`.

- **File:** `testproject1/scene1.qto3settings`
  - **Format and metadata:** Qgis2threejs scene settings in JSON format.
  - **Use:** Used for basic CLI web/image/glTF exports.

- **File:** `testproject1/scene1_g1.qto3settings`
  - **Format and metadata:** Qgis2threejs scene settings in JSON format.
  - **Use:** Scene 1 settings used by GUI scene, widget, and layer tests.

- **File:** `testproject1/scene1_g2.qto3settings`
  - **Format and metadata:** Alternate Qgis2threejs scene settings in JSON format.
  - **Use:** Used by the GUI dialog layout checks for scene/layer settings.

### Raster Data

- **File:** `testproject1/dem_srtm30.tif`
  - **File-level metadata:** GeoTIFF. According to the README, made from SRTM 30 data. Specific GDAL tags and resolution have not been re-read for this inventory.
  - **Association and use:** `dem_srtm30` elevation layer in the project. Relevant to GUI sea-surface click and DEM dialog checks.

- **File:** `testproject1/shadedrelief_srtm3.tif`
  - **File-level metadata:** GeoTIFF. According to the README, made from SRTM 3 data, with small voids filled using `gdal_fillnodata.py` and the resolution reduced.
  - **Association and use:** Shaded-relief background raster in the project.

### Vector Data

- **File:** `testproject1/pt1.csv`
  - **File-level metadata:** 5 rows. Columns: `pk,r,WKT`. Sample `POINT Z` geometries with a radius attribute.
  - **Association and use:** Column types are specified by `pt1.csvt`. Data for 3D point-symbol settings.

- **File:** `testproject1/pt1.csvt`
  - **File-level metadata:** OGR CSV type descriptor: `Integer,Integer,String`.
  - **Association and use:** Specifies the types of `pk`, `r`, and WKT in `pt1.csv`.

- **File:** `testproject1/pt2.csv`
  - **File-level metadata:** 5 rows. Columns: `pk,w,h,d,WKT`. `POINT Z` geometries with width, height, and depth attributes.
  - **Association and use:** Column types are specified by `pt2.csvt`.

- **File:** `testproject1/pt2.csvt`
  - **File-level metadata:** OGR CSV type descriptor: `Integer,Integer,Integer,Integer,String`.
  - **Association and use:** Type definition for `pt2.csv`.

- **File:** `testproject1/pt3.csv`
  - **File-level metadata:** 5 rows. Columns: `pk,r,h,WKT`. `POINT Z` geometries with radius and height attributes.
  - **Association and use:** Column types are specified by `pt3.csvt`. The GUI click test clicks an object in `pt3`.

- **File:** `testproject1/pt3.csvt`
  - **File-level metadata:** OGR CSV type descriptor: `Integer,Integer,Integer,String`.
  - **Association and use:** Type definition for `pt3.csv`.

- **File:** `testproject1/pt4.csv`
  - **File-level metadata:** 6 rows. Columns: `pk,label,r,h,WKT`. Points for `cone 1` through `cone 5` and Mount Fuji (Z=3776). The fifth cone has empty radius and height values.
  - **Association and use:** Types are specified by `pt4.csvt`. Used for attribute display, layer visibility toggling, and the scene's maximum Z-range check.

- **File:** `testproject1/pt4.csvt`
  - **File-level metadata:** OGR CSV type descriptor: `Integer,String,Integer,Integer,String`.
  - **Association and use:** Type definition for `pt4.csv`.

- **File:** `testproject1/pt5.csv`
  - **File-level metadata:** 5 rows. Columns: `pk,r,dip,direction,WKT`. 2D points with radius, dip, and direction attributes. Directions are 0, 90, 180, 270, and 315 degrees.
  - **Association and use:** Column types are specified by `pt5.csvt`. Data for directional/tilted point representations.

- **File:** `testproject1/pt5.csvt`
  - **File-level metadata:** OGR CSV type descriptor: `Integer,Integer,Integer,Integer,String`.
  - **Association and use:** Type definition for `pt5.csv`.

- **File:** `testproject1/pt6.csv`
  - **File-level metadata:** 2 rows. Columns: `pk,name,url,scale,rz,WKT`. 2D points with an external glTF binary model URL, scale, and rotation attributes. The URL points to KhronosGroup glTF Sample Models' `2CylinderEngine.glb`.
  - **Association and use:** Column types are specified by `pt6.csvt`. Data for placing external 3D models.

- **File:** `testproject1/pt6.csvt`
  - **File-level metadata:** OGR CSV type descriptor: `Integer,String,String,Integer,Integer,String`.
  - **Association and use:** Type definition for `pt6.csv`.

- **File:** `testproject1/line1.csv`
  - **File-level metadata:** 1 row. Columns: `id,WKT`. `LINESTRING Z` with elevation values.
  - **Association and use:** Column types are specified by `line1.csvt`. Line representation sample.

- **File:** `testproject1/line1.csvt`
  - **File-level metadata:** OGR CSV type descriptor: `Integer,String`.
  - **Association and use:** Type definition for `line1.csv`.

- **File:** `testproject1/line2.csv`
  - **File-level metadata:** 1 row. Columns: `id,WKT`. Elevation-bearing `LINESTRING Z` polyline.
  - **Association and use:** Column types are specified by `line2.csvt`.

- **File:** `testproject1/line2.csvt`
  - **File-level metadata:** OGR CSV type descriptor: `Integer,String`.
  - **Association and use:** Type definition for `line2.csv`.

- **File:** `testproject1/line3.csv`
  - **File-level metadata:** 1 row. Columns: `id,WKT`. Elevation-bearing `LINESTRING Z` polyline.
  - **Association and use:** Column types are specified by `line3.csvt`.

- **File:** `testproject1/line3.csvt`
  - **File-level metadata:** OGR CSV type descriptor: `Integer,String`.
  - **Association and use:** Type definition for `line3.csv`.

- **File:** `testproject1/line4.csv`
  - **File-level metadata:** 1 row. Columns: `id,WKT`. Elevation-bearing `LINESTRING Z` polyline.
  - **Association and use:** Column types are specified by `line4.csvt`.

- **File:** `testproject1/line4.csvt`
  - **File-level metadata:** OGR CSV type descriptor: `Integer,String`.
  - **Association and use:** Type definition for `line4.csv`.

- **File:** `testproject1/line5.csv`
  - **File-level metadata:** 1 row. Columns: `id,WKT`. 2D `LINESTRING` without an elevation dimension.
  - **Association and use:** Column types are specified by `line5.csvt`. Sample line without Z values.

- **File:** `testproject1/line5.csvt`
  - **File-level metadata:** OGR CSV type descriptor: `Integer,String`.
  - **Association and use:** Type definition for `line5.csv`.

- **File:** `testproject1/lineV.csv`
  - **File-level metadata:** 1 row. Columns: `id,WKT`. Vertical `LINESTRING Z` from Z=0 to Z=10000 at a single XY position.
  - **Association and use:** Column types are specified by `lineV.csvt`. Used for the GUI vertical-line Z-range check.

- **File:** `testproject1/lineV.csvt`
  - **File-level metadata:** OGR CSV type descriptor: `Integer,String`.
  - **Association and use:** Type definition for `lineV.csv`.

- **File:** `testproject1/polygon1.csv`
  - **File-level metadata:** 6 rows. Columns: `pk,name,alt,height,WKT`. Includes triangular, rectangular, concave, and polygon-with-one-hole/two-holes shapes.
  - **Association and use:** Column types are specified by `polygon1.csvt`. Sample polygon geometries and elevation/height attributes.

- **File:** `testproject1/polygon1.csvt`
  - **File-level metadata:** OGR CSV type descriptor: `Integer,String,Integer,Integer,String`.
  - **Association and use:** Type definition for `polygon1.csv`.

- **File:** `testproject1/polygon2.csv`
  - **File-level metadata:** 6 rows. Same attribute structure and shape categories as `polygon1.csv`, with polygon features at different locations.
  - **Association and use:** Column types are specified by `polygon2.csvt`. A second set of polygon inputs.

- **File:** `testproject1/polygon2.csvt`
  - **File-level metadata:** OGR CSV type descriptor: `Integer,String,Integer,Integer,String`.
  - **Association and use:** Type definition for `polygon2.csv`.

- **File:** `testproject1/ne_10m_railroads.csv`
  - **File-level metadata:** 88 rows and 14 columns: `rwdb_rr_id`, `mult_track`, `electric`, `other_code`, `category`, `disp_scale`, `add`, `featurecla`, `scalerank`, `natlscale`, `part`, `continent`, `scalerank_x_200`, and `WKT`. Contains railroad attributes and WKT geometries.
  - **Association and use:** Types are specified by `ne_10m_railroads.csvt`. Railroad vector layer in the project. See Data Sources below.

- **File:** `testproject1/ne_10m_railroads.csvt`
  - **File-level metadata:** OGR CSV type descriptors for 14 columns, in order: `Integer,Integer,Integer,Integer,Integer,String,Integer,String,Integer,Integer,String,String,Integer,String`.
  - **Association and use:** Type definition for `ne_10m_railroads.csv`.


## testproject2

`testproject2.qgs` is a QGIS project whose project CRS is **EPSG:2447 — JGD2000 / Japan Plane Rectangular CS V**. It includes a small ASCII DEM, point/line CSVs, a LAS point cloud, and a GeoTIFF. It is used for scene construction, DEM building, origin-shift, line/point animation, and GUI web/glTF export tests.

### Project and Scene Settings

- **File:** `testproject2/testproject2.qgs`
  - **Format and metadata:** QGIS XML project. Project CRS: EPSG:2447. Registers points, lines, an ASCII DEM, a LAS point cloud, and a GeoTIFF.
  - **Use:** Project used by CLI builder tests and `gui/test_gui2.py`.

- **File:** `testproject2/scene2_g1.qto3settings`
  - **Format and metadata:** Scene settings in JSON format. The GUI tests treat it as the scene with origin shifting enabled.
  - **Use:** Used for scene construction and GUI scene/line tests.

- **File:** `testproject2/scene2_g2.qto3settings`
  - **Format and metadata:** Scene settings in JSON format. The GUI tests treat it as the scene with origin shifting disabled.
  - **Use:** Used by CLI scene/DEM/vector builder tests and GUI tests.

### Raster, Vector and LAS Data

- **File:** `testproject2/ascii_dem.asc`
  - **File-level metadata:** ESRI ASCII Grid. 10 columns × 10 rows, lower-left corner `(400,300)`, cell size 10, and NoData value `-9999`. Cell values range from 0 to 9.
  - **Association and use:** `ascii_dem` raster. The CLI DEM builder creates a 10×10 DEM block from this grid.

- **File:** `testproject2/srtm.tif`
  - **File-level metadata:** GeoTIFF referenced as the project's `srtm` raster layer. Tags and source details have not been independently verified for this inventory.
  - **Association and use:** Background/elevation raster input for testproject2.

- **File:** `testproject2/points.csv`
  - **File-level metadata:** 20 rows. Columns: `id,x,y,z,color,obj_height,name`. EPSG:2447 and the XYZ columns are recorded in the project's Delimited Text layer definition. Samples include fruit names, colors, Z values, and height attributes.
  - **Association and use:** `points` layer. Used by the CLI VectorLayerBuilder and GUI point/animation tests.

- **File:** `testproject2/linestrings.csv`
  - **File-level metadata:** 4 rows. Columns: `id,bird_name,wkt`. WKT `LINESTRING Z` geometries; the fourth includes a vertical segment. The project definition specifies CRS EPSG:2447.
  - **Association and use:** `linestrings` layer. Used for GUI Z-range and line-growing animation tests.

- **File:** `testproject2/pointcloud.las`
  - **File-level metadata:** LAS point-cloud file. Registered in the QGIS project as a `pointcloud` layer using the PDAL provider. LAS header details such as CRS and point count have not been re-read for this inventory.
  - **Association and use:** Target of GUI additional-layer/dialog checks.

## testproject3

`testproject3.qgs` is a QGIS project in **EPSG:2447 — JGD2000 / Japan Plane Rectangular CS V**. It combines an SRTM GeoTIFF with mountain locations from a CSV.

### Project and Scene Settings

- **File:** `testproject3/testproject3.qgs`
  - **Format and metadata:** QGIS XML project. Project CRS: EPSG:2447. Registers the `srtm` raster and `mountains` point layers.
  - **Use:** Used by the CLI pyramid DEM builder test and GUI pyramid DEM tests.

- **File:** `testproject3/scene3_pyramid.qto3settings`
  - **Format and metadata:** Qgis2threejs scene settings in JSON format. Configures the `srtm` layer as a pyramid DEM and enables XY origin shifting.
  - **Use:** Used to verify the pyramid DEM tile-set parameters in the CLI builder test and to display and zoom into the DEM in GUI tests.

- **File:** `testproject3/scene3_pyramid_originshift.qto3settings`
  - **Format and metadata:** Alternate scene settings in JSON format, with origin shifting disabled.
  - **Use:** Used by the GUI test variant that exercises the pyramid DEM without origin shifting.

### Raster and Vector Data

- **File:** `testproject3/srtm.tif`
  - **File-level metadata:** GeoTIFF used as the `srtm` raster layer. The project extent is `(-88000, -144000)` to `(38000, -60000)` in EPSG:2447.
  - **Association and use:** Elevation input for pyramid DEM/tile-set generation and GUI rendering and zoom tests.

- **File:** `testproject3/mountains.csv`
  - **File-level metadata:** Point data with columns `Name`, `Latitude`, `Longitude`, `Elevation`, and `山名`.
  - **Association and use:** Loaded as the `mountains` point layer; included in the project scene alongside the DEM.

## Data Sources

- `dem_srtm30.tif`: SRTM 30 data. Source listed in the original README: [USGS SRTM30](https://dds.cr.usgs.gov/srtm/version2_1/SRTM30/e100n40/)
- `shadedrelief_srtm3.tif`: SRTM 3 data. Source listed in the original README: [USGS SRTM3](https://dds.cr.usgs.gov/srtm/version2_1/SRTM3/)
- `ne_10m_railroads.csv`: Part of Natural Earth Railroads (`ne_10m_railroads.shp`). Source: [Natural Earth](https://www.naturalearthdata.com/)
