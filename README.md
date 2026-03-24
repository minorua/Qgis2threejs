# Custom Qgis2threejs Plugin

This plugin is a customized version of the original [Qgis2threejs](https://github.com/minorua/Qgis2threejs) plugin for [QGIS](https://qgis.org/). It keeps the standard 3D viewer/export workflow, but adds custom automation and export features for large-area production workflows.

## What Is Different In This Version

This custom version adds workflow-specific features on top of the original plugin:

- An `Automate` menu in the main exporter window
- `Build Settings File` for generating many `.qto3settings` tile settings from one large-area scene
- `Generate Tiles` for batch-loading those settings files and exporting all tiles automatically
- Multi-material glTF export through `Save Scene Test (All Materials)...`
- Multi-material support inside batch tile export, so settings files with multiple DEM materials export correctly in batch
- Polygon-based tile selection for large-area export planning
- Better long-running batch export handling with export completion checks and timeouts

## Main Menus Added

### File > Save Scene As

- `glTF (.gltf, .glb)...`
  - Standard single-scene glTF export
  - Uses the currently active material for the DEM, same as the normal/original behavior

- `Save Scene Test (All Materials)...`
  - Custom export mode for DEM layers with multiple materials
  - Exports a single terrain mesh with multiple material slots
  - Lets you switch materials/textures later in software such as Blender or Unity
  - Does not duplicate the DEM mesh for each material

### File > Automate

- `Build Settings File`
  - Creates many tile-level `.qto3settings` files from one source settings file
  - Uses a selected polygon to decide which tiles should be included
  - Updates tile center, tile width/height, DEM size, and texture size for each tile
  - Preserves multiple DEM materials in generated settings files

- `Generate Tiles`
  - Loads each generated `.qto3settings` file one by one
  - Rebuilds the scene automatically
  - Exports each tile to `.glb`
  - Detects whether a tile uses multiple DEM materials
  - Automatically switches to multi-material export when needed

## How The Custom Workflow Works

### 1. Prepare Your Scene

Set up your scene in QGIS as usual:

- Add DEM and other layers
- Configure DEM materials in layer properties
- If needed, add more than one material to the DEM layer
- Enable preview in the exporter window

If your DEM has multiple materials configured, this custom version can export all of them in one glTF/GLB as material slots on the same terrain mesh.

### 2. Single Scene Export

If you only want to export the current scene once:

- Use `File > Save Scene As > glTF (.gltf, .glb)...` for normal export
- Use `File > Save Scene As > Save Scene Test (All Materials)...` for multi-material DEM export

#### Multi-material export behavior

When `Save Scene Test (All Materials)...` is used:

- All visible DEM layers are rebuilt with all configured materials enabled
- The exporter sends every DEM material to the viewer before export
- The exported glTF keeps one terrain mesh per DEM block
- Each mesh gets multiple material slots instead of creating duplicate meshes

This is useful when you want:

- One static terrain mesh
- Multiple swappable textures/materials on that mesh
- Lower storage cost than exporting multiple duplicate terrain meshes

## Batch Export Workflow For Large Areas

This is the main custom workflow added in this plugin.

### Step 1. Create a Base Settings File

Prepare one source `.qto3settings` file for the large scene:

- Configure the full scene the way you want
- Save the export settings
- Make sure DEM material configuration is already correct

This source settings file becomes the template for tile generation.

### Step 2. Select Polygon Boundaries

Use the 3D viewer polygon workflow to define the area to export.

The plugin stores polygon coordinates and uses them later in `Build Settings File`.

The polygon is used to:

- include tiles fully inside the area
- include tiles partially intersecting the area
- skip tiles clearly outside the selected boundary

### Step 3. Use `Build Settings File`

Open:

- `File > Automate > Build Settings File`

This dialog lets you configure:

- Input settings file
- Output directory for generated `.qto3settings`
- Polygon boundaries from the 3D viewer
- Tile width
- Texture size
- DEM size
- Number of tiles in X/Y

#### What this function does

For each accepted tile:

- clones the input settings JSON
- updates scene center for that tile
- updates tile width and height
- updates DEM size
- updates texture size
- writes a new `.qto3settings` file

#### Important custom behavior for multi-material DEMs

If the DEM layer contains multiple materials:

- all materials are kept in the generated settings files
- texture size is updated for every material, not just the first one

That means batch exports generated from these settings files can still export all DEM materials later.

### Step 4. Use `Generate Tiles`

Open:

- `File > Automate > Generate Tiles`

Choose:

- the directory containing the generated `.qto3settings` files
- the output directory for exported `.glb` tiles

#### What this function does

For each settings file:

1. Load the tile settings
2. Rebuild the scene
3. Detect whether the DEM has multiple materials
4. If single-material:
   - export with the standard glTF exporter
5. If multi-material:
   - rebuild visible DEM layers with all materials enabled
   - export using the custom multi-material export path
6. Wait until the model file is actually saved before continuing
7. Move to the next tile

#### Why this matters

Without the custom logic, batch export would only use the current/active DEM material.

With this custom version:

- single-material tiles still export normally
- multi-material tiles automatically export all DEM materials
- the terrain stays a single mesh with material slots

## Multi-Material DEM Export Details

This custom version adds support for exporting more than one DEM material into the same glTF/GLB.

### Problem solved

In the default workflow, even if multiple DEM materials were configured, only one material was exported.

### Custom solution

This version:

- rebuilds DEM layers with `allMaterials=True`
- collects all available DEM materials before export
- exports one mesh with multiple material slots
- avoids creating one duplicate DEM mesh per material

### Result in external tools

In tools like Blender or Unity, you should see:

- a single terrain/DEM mesh
- multiple materials available on that mesh

This makes it easier to:

- swap terrain textures
- test different surface looks
- keep geometry fixed while changing appearance

## Notes About Reliability

Batch export includes extra handling for long operations:

- waits for scene rebuild before exporting
- waits for file save completion before moving to the next tile
- uses timeouts to avoid hanging forever
- shows progress in the status bar
- reports success/failure counts at the end

## Recommended Usage

### Use the normal export when:

- you only need one material
- you want the original glTF export behavior
- you are exporting a single scene quickly

### Use `Save Scene Test (All Materials)...` when:

- your DEM has multiple materials
- you want to inspect or use all DEM materials in external 3D software
- you want one terrain mesh with swappable materials

### Use `Build Settings File` + `Generate Tiles` when:

- your source area is too large to export as one scene
- you need tile-based export for a large region
- you want batch `.glb` generation
- your tiles may include multi-material DEM layers

## Original Documentation

Most standard Qgis2threejs behavior still follows the original project:

- Original project: https://github.com/minorua/Qgis2threejs
- Original documentation: https://minorua.github.io/Qgis2threejs/docs/

This README focuses on the custom workflow and features added in this modified version.

## Dependencies

This plugin uses the same main libraries/resources as the base project, including:

- [three.js](https://threejs.org)
- [Proj4js](https://trac.osgeo.org/proj4js/)
- [tween.js](https://github.com/tweenjs/tween.js)
- [Potree Core](https://github.com/tentone/potree-core)
- [dat-gui](https://github.com/dataarts/dat.gui)
- [Font Awesome](https://fontawesome.com/)
- Python port of [earcut](https://github.com/mapbox/earcut)
- [unfetch](https://github.com/developit/unfetch)
