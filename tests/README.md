# Test Guide

This document summarizes the test code under `tests/`. For the input data descriptions, see [`data/README.md`](data/README.md).

## Test Structure

### CLI Tests

Tests in this section are run from the command line in a QGIS-enabled Python environment.

- **File:** `cli/test_00_env.py`

  Verifies that the QGIS application starts and that all major Python modules in the plugin can be imported.

- **File:** `cli/test_10_builder.py`

  Builds scene, DEM, and vector-layer data, then checks their structure and key properties. Covers a simple DEM, tiled ASCII Grid DEM, pyramid DEM tile-set metadata, and point-feature geometry.

- **File:** `cli/test_11_export.py`

  Exports web pages and checks JavaScript errors and warnings using the web page inspector (see below).

- **File:** `cli/test_20_bridge.py`

  Checks image and glTF exports through WebEngine, including image dimensions and comparison with expected images.

- **File:** `cli/test_30_plugins.py`

  Runs an export with the GSI elevation tile plugin enabled.

### GUI Tests

Tests in this section are run through the plugin's GUI in QGIS with a test project loaded.

- **File:** `gui/test_gui1.py`

  GUI checks for scenes, layers, clicks, keyboard input, animation, and dialogs using `testproject1`.

- **File:** `gui/test_gui2.py`

  GUI checks for origin shifting, points and lines, animation, and web/glTF output using `testproject2`.

- **File:** `gui/test_gui3.py`

  GUI checks that display and zoom into the pyramid DEM in `testproject3`, both with and without origin shifting.

## CLI Tests

CLI tests use `qgis.testing.unittest` and run in a Python environment where QGIS is available.

- **File:** `test_00_env.py`
  - **Class:** `TestQgisStartup`
    - **Test:** `test01_start_qgis`

      Logs the Python, PyQt, Qt, and QGIS versions, then verifies that a QGIS application can be created.

  - **Class:** `TestPluginImports`
    - **Test:** `test01_import_all_modules`

      Walks and imports Python modules under `core`, `gui`, `lib`, `plugins`, and `utils`. This is intended to detect import errors that may not surface during startup.

- **File:** `test_10_builder.py`
  - **Class:** `TestSceneBuilder`
    - **Test:** `test01_build_scene_data`

      Builds scene data from `testproject2` and `scene2_g2`, then checks the scene type, base extent, 3D origin, vertical scale, and lighting.

  - **Class:** `TestDEMLayerBuilder`
    - **Test:** `test01_build_simple_dem_data`

      Builds DEM data from `testproject1`. It also checks that the builder returns no data when the DEM lies outside the scene extent.

    - **Test:** `test02_build_tiled_dem_data`

      Builds and verifies a tiled DEM data from the small ASCII Grid in `testproject2`.

    - **Test:** `test03_build_pyramid_tiled_dem_data`

      Verifies the parameters used to generate 3D tiles metadata for `testproject3/srtm.tif`.

  - **Class:** `TestVectorLayerBuilder`
    - **Test:** `test01_build_point_layer_data`

      Builds point-layer data from `testproject2`.

- **File:** `test_11_export.py`
  - **Class:** `TestExportWeb`
    - **Test:** `test01_export_scene1_webpage`

      Exports `testproject1` as a web page and its associated data files.

    - **Test:** `test02_check_scene1_webpage`

      Loads the exported page and checks for JavaScript errors and warnings after the scene has loaded and rendered. Because `MANUAL_PAGE_CHECK=True`, the page is opened even when the test passes.

    - **Test:** `test03_check_scene1_webpage_capture`

      Captures the exported page at 1024×768 and checks the image dimensions.
  - **Class:** `TestExportWebLM_datgui` (inherits the three `TestExportWeb` tests above)
    - **Test:** `test01_export_scene1_webpage`

      Runs the same export with the `3DViewer(dat-gui).html` template.
    - **Test:** `test02_check_scene1_webpage`

      Checks dat-gui top-level items, folders, layer count, and Custom Plane item count.
    - **Test:** `test03_check_scene1_webpage_capture`

      Captures the exported dat-gui page and checks the image dimensions.

- **File:** `test_20_bridge.py`
  - **Class:** `TestExportImageWebEngine`
    - **Test:** `test01_export_scene1_image`

      Checks that ImageExporter logs no errors and that events occur in order from settings load through scene/layer/block loading to saving. Warnings are logged.
    - **Test:** `test02_check_scene1_image`

      Checks that the output image is 1024×768. In the default manual mode it opens the image and skips; in automatic mode it compares against `expected/scene1.png`.
  - **Class:** `TestExportModelWebEngine`
    - **Test:** `test01_export_scene1_glTF`

      Checks that ModelExporter produces a non-empty `scene1.gltf` file.

- **File:** `test_30_plugins.py`
  - **Class:** `TestPlugins`
    - **Test:** `test01_gsielevtile`

      Enables all plugins and runs a web export using settings for GSI elevation tiles. The required `gsielevtile.qto3settings` is not present under `tests/data/testproject1/` in the current checkout, so this test may not run due to the missing fixture.

## GUI Tests

GUI tests are run with the corresponding test project loaded in QGIS and the plugin open.

### `test_gui1.py` — `testproject1`

- **Class:** `TestScene`
  - **Test:** `test01_loadScene1`

    Loads `scene1_g1` and checks the basic GUI display using the scene settings.

  - **Test:** `test02_ZRange`

    Checks the scene's Z range when the map canvas includes the expected area and is not rotated. Skips when the preconditions do not match the environment. The range covers the flat surface at the lower end and the high feature in `pt4` at the upper end.

- **Class:** `TestDEMLayer`

  Declares a DEM layer ID but has no `test...` methods of its own. It adds no standalone test, but identifies the target layer for dialog layout checks.

- **Class:** `TestPointLayer`
  - **Test:** `test01_propertiesdialog`

    Applies the available object types in the layer properties dialog one by one and waits for the `dataLoaded` signal.

  - **Test:** `test02_clickObject`

    Clicks an object in `pt3` and checks that the reported Z coordinate has the expected value.

  - **Test:** `test03_clickObjectWithAttr`

    Clicks an object in `pt4` and checks that `cone 3` appears in the attribute table.

  - **Test:** `test04_hideAndClick`

    Hides `pt4`, clicks the same location, and checks that the sea surface behind it is selected.

  - **Test:** `test05_restoreAndClick`

    Shows `pt4` again and checks that `cone 3` can be selected again.

- **Class:** `TestLineLayer`
  - **Test:** `test01_propertiesdialog`

    As a shared vector-layer check, applies the available types from the line properties dialog.

  - **Test:** `test02_verticalLine`

    Shows the vertical line and checks that the scene Z range is 0–10000.

- **Class:** `TestPolygonLayer`
  - **Test:** `test01_propertiesdialog`

    As a shared vector-layer check, applies the available types from the polygon properties dialog.

- **Class:** `TestWidget`
  - **Test:** `test01_testLabels1`

    Loads `scene1_g1` without test labels and checks that the project's header label is displayed.

  - **Test:** `test02_testLabels2`

    Checks that the running test's class and method names appear in the header and its description appears in the footer.

  - **Test:** `test03_naviZ`

    Clicks the +Z navigation control, then clicks the sea surface and checks that the displayed coordinate is 0.

  - **Test:** `test04_naviX`

    Clicks the +X navigation control, then clicks the flat surface and checks that the displayed coordinate is -4000.

  - **Test:** `test05_clickSky`

    Checks that clicking the sky does not display an information popup.

- **Class:** `TestKeyboardInteraction`
  - **Test:** `test01_hideLabels`

    Sends the `L` key to exercise the label visibility toggle. The test does not explicitly assert the resulting visibility state.

  - **Test:** `test02_showLabels`

    Sends the `L` key again to exercise the label visibility toggle. The test does not explicitly assert the resulting visibility state.

- **Class:** `TestCameraAnimation`
  - **Test:** `test01_cameraAnimation`

    Starts the camera animation and uses the shared helper to verify that the `animationStopped` signal arrives before the timeout.

- **Class:** `DialogLayoutCheck`
  - **Test:** `test01_Scene`

    Iterates through the scene properties dialog tabs and checks their display.

  - **Test:** `test02_Layer`

    Iterates through the properties dialogs for the DEM, point, line, polygon, and specified additional layers.

  - **Test:** `test03_Export`

    Checks the display of the web export dialog.

  - **Test:** `test04_SaveAsImage`

    Checks the display of the image save dialog.

  - **Test:** `test05_Settings`

    Checks the display of the plugin settings dialog.

  - **Test:** `test07_NorthArrow`

    Checks the display of the North Arrow settings dialog.

  - **Test:** `test08_HFLabel`

    Checks the display of the HFLabel settings dialog.

`DialogLayoutCheck` is not included in the regular list of classes whose names start with `Test`; run it with option `9999`. `SNAPSHOT_DIR`, the destination for dialog screenshots, is empty by default, so screenshots are not saved to files under the default configuration.

### `test_gui2.py` — `testproject2`

- **Class:** `TestScene`
  - **Test:** `test01_loadScene2_1`

    Loads `scene2_g1`, where origin shifting is enabled, and checks the 3D bounding box shifted to center around the origin.

  - **Test:** `test02_loadScene2_2`

    Loads `scene2_g2`, where origin shifting is disabled, and checks the 3D bounding box in the original map coordinates.

- **Class:** `TestPointLayer`
  - **Test:** `test01_showLayer`

    Shows the point layer and checks for a Z range of 0–30.

  - **Test:** `test02_opacityAnimation`

    Runs the point layer animation and hides the layer after it finishes.

- **Class:** `TestLineLayer`
  - **Test:** `test01_loadScene2_1`

    Shows the line in `scene2_g1` and checks for a Z range of 0–50.

  - **Test:** `test02_lineGrowingAnimation`

    Runs the line-growing animation in `scene2_g1`.

  - **Test:** `test03_loadScene2_2`

    Shows the thick line in `scene2_g2` and checks for a Z range of 0–50.

  - **Test:** `test04_lineGrowingAnimation`

    Runs the line-growing animation in `scene2_g2`.

- **Class:** `TestWebExport`
  - **Test:** `test01_export`

    Opens the GUI web export dialog and runs an export.

- **Class:** `TestGLTFExport`
  - **Test:** `test01_export`

    Calls `saveAsGLTF` in the WebView and generates `output/test_gui2.gltf`.

### `test_gui3.py` — `testproject3`

- **Class:** `TestDEMLayer`
  - **Test:** `test01_showAndZoomToPyramidDEM`

    Loads `scene3_pyramid`, zooms to the `srtm` DEM layer, and waits for the scene to render.

  - **Test:** `test02_zoomFurtherIntoPyramidDEM`

    Moves the camera further into the pyramid DEM and waits for the scene to render at the closer view.

- **Class:** `TestDEMLayer_OriginShift`

  Inherits the same two zoom tests using `scene3_pyramid_originshift`, which enables origin shifting.

## Web Page Inspector

`inspector/` contains a small PyQt6 + QWebEngineView application for inspecting exported web pages. CLI tests run it as a separate process (via `InspectorClient` in `inspector/client.py`).

## Known Issues

- `cli/test_30_plugins.py` specifies `tests/data/testproject1/gsielevtile.qto3settings`, but that file is not present in the current `tests/data/`.
- The automatic image comparisons in `cli/test_20_bridge.py` and the HTML capture test use images under `tests/expected/`, but that directory is currently absent. The default configuration uses manual inspection; expected images must be supplied to enable automatic comparison.
- `output/` contain generated or runtime data. Do not confuse them with fixed input fixtures.
