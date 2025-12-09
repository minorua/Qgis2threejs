// (C) 2024 MapLibre GL Viewer for Qgis2threejs
// SPDX-License-Identifier: MIT

"use strict";

var maplibregl = window.maplibregl;

var app = {
    map: null,
    container: null,
    layers: {},
    sources: {},
    pyObj: null,
    initialized: false,
    debugMode: false,
    isWebEngine: false
};

// Initialize the map viewer
function init(off_screen, debug_mode, qgis_version, is_webengine) {
    app.debugMode = debug_mode;
    app.isWebEngine = is_webengine;

    if (is_webengine) {
        // Web Channel
        new QWebChannel(qt.webChannelTransport, function(channel) {
            app.pyObj = channel.objects.bridge;
            app.pyObj.sendScriptData.connect(function (script, data) {
                var pyData = function () {
                    return data;
                };

                eval(script);

                if (app.debugMode) {
                    console.debug("↓", script, "# sendScriptData", (data === undefined) ? "" : data);
                }
            });

            _init(off_screen);
        });
    }
    else {
        // WebKit Bridge
        window.pyData = function () {
            return app.pyObj.data();
        }

        _init(off_screen);
    }
}

function _init(off_screen) {
    var mapContainer = document.getElementById('map');

    app.map = new maplibregl.Map({
        container: 'map',
        zoom: 12,
        center: [11.39085, 47.27574],
        pitch: 70,
        hash: true,
        style: {
            version: 8,
            sources: {
                osm: {
                    type: 'raster',
                    tiles: ['https://a.tile.openstreetmap.org/{z}/{x}/{y}.png'],
                    tileSize: 256,
                    attribution: '&copy; OpenStreetMap Contributors',
//                    maxzoom: 19
                },
                // Use a different source for terrain and hillshade layers, to improve render quality
                terrainSource: {
                    type: 'raster-dem',
                    url: 'https://demotiles.maplibre.org/terrain-tiles/tiles.json',
                    tileSize: 256
                },
                hillshadeSource: {
                    type: 'raster-dem',
                    url: 'https://demotiles.maplibre.org/terrain-tiles/tiles.json',
                    tileSize: 256
                }
            },
            layers: [
                {
                    id: 'osm',
                    type: 'raster',
                    source: 'osm'
                },
                {
                    id: 'hills',
                    type: 'hillshade',
                    source: 'hillshadeSource',
                    layout: {visibility: 'visible'},
                    paint: {'hillshade-shadow-color': '#473B24'}
                }
            ],
            terrain: {
                source: 'terrainSource',
                exaggeration: 1
            },
            sky: {}
        },
/*        maxZoom: 18,
        maxPitch: 85*/
    });

    app.map.addControl(
        new maplibregl.NavigationControl({
            visualizePitch: true,
            showZoom: true,
            showCompass: true
        })
    );

    app.map.addControl(
        new maplibregl.TerrainControl({
            source: 'terrainSource',
            exaggeration: 1
        })
    );


    app.container = mapContainer;

    // Handle map events
    app.map.on('load', function() {
        console.log('Map loaded');
        app.initialized = true;
        if (app.pyObj) {
			// app.pyObj.emitMapLoaded();
		}
    });

    app.map.on('error', function(e) {
        console.error('Map error:', e);
        if (app.pyObj) {
			// app.pyObj.emitError(e.error.message);
		}
    });

    // Handle clicks for feature queries
    app.map.on('click', function(e) {
        handleMapClick(e);
    });

    // Message bar
    var closeMsgBar = document.getElementById('closemsgbar');
    if (closeMsgBar) {
        closeMsgBar.onclick = closeMessageBar;
    }

    if (app.pyObj) {
        app.pyObj.emitSceneLoaded();
    }
}

// Load scene data
function loadData(data) {
    if (!app.initialized || !app.map) {
        console.error('Map not initialized');
        return;
    }

    var p = data.properties;

    if (data.type === "scene" && p !== undefined) {
        // Initialize scene properties
        var baseExtent = p.baseExtent;

        if (baseExtent) {
            // Set map center and zoom based on base extent
            var center = [baseExtent.cx, baseExtent.cy];
            var zoom = calculateZoomLevel(baseExtent.width);

            app.map.easeTo({
                center: center,
                zoom: zoom,
                duration: 1000
            });
        }

        // Store scene data
        app.sceneData = p;
    }

    if (data.type === "layer" && data.layers) {
        for (var i = 0; i < data.layers.length; i++) {
            addLayer(data.layers[i]);
        }
    }
}

// Add a layer to the map
function addLayer(layerData) {
    if (!app.map || !layerData) return;

    var layerId = layerData.id || createLayerId();

    // Parse geometry data
    var features = [];
    if (layerData.features) {
        for (var i = 0; i < layerData.features.length; i++) {
            features.push(layerData.features[i]);
        }
    }

    // Create GeoJSON source
    var sourceId = 'source-' + layerId;
    var source = {
        type: 'geojson',
        data: {
            type: 'FeatureCollection',
            features: features
        }
    };

    app.sources[sourceId] = source;

    // Add source to map
    if (!app.map.getSource(sourceId)) {
        app.map.addSource(sourceId, source);
    }

    // Create layers based on geometry type
    var geomType = layerData.geomType || 'point';
    var layers = createLayersFromData(layerId, sourceId, geomType, layerData.properties);

    // Add layers to map
    for (var i = 0; i < layers.length; i++) {
        if (!app.map.getLayer(layers[i].id)) {
            app.map.addLayer(layers[i]);
        }
    }

    app.layers[layerId] = {
        id: layerId,
        sourceId: sourceId,
        geomType: geomType,
        properties: layerData.properties,
        visible: layerData.visible !== false
    };
}

// Create MapLibre GL layers from data
function createLayersFromData(layerId, sourceId, geomType, properties) {
    var layers = [];
    var layerProperties = properties || {};

    if (geomType === 'point') {
        layers.push({
            id: layerId,
            type: 'circle',
            source: sourceId,
            paint: {
                'circle-radius': layerProperties.pointSize || 5,
                'circle-color': layerProperties.color || '#088',
                'circle-opacity': (layerProperties.opacity !== undefined) ? layerProperties.opacity : 0.8
            }
        });
    }
    else if (geomType === 'linestring') {
        layers.push({
            id: layerId,
            type: 'line',
            source: sourceId,
            paint: {
                'line-color': layerProperties.color || '#088',
                'line-width': layerProperties.lineWidth || 2,
                'line-opacity': (layerProperties.opacity !== undefined) ? layerProperties.opacity : 0.8
            }
        });
    }
    else if (geomType === 'polygon') {
        // Add fill layer
        layers.push({
            id: layerId + '-fill',
            type: 'fill',
            source: sourceId,
            paint: {
                'fill-color': layerProperties.color || '#088',
                'fill-opacity': (layerProperties.opacity !== undefined) ? layerProperties.opacity * 0.5 : 0.4
            }
        });

        // Add outline layer
        layers.push({
            id: layerId + '-outline',
            type: 'line',
            source: sourceId,
            paint: {
                'line-color': layerProperties.color || '#088',
                'line-width': 2,
                'line-opacity': (layerProperties.opacity !== undefined) ? layerProperties.opacity : 0.8
            }
        });
    }
    else if (geomType === 'dem' || geomType === 'raster') {
        // For DEM/raster data, create a raster layer
        // This would need raster source data
        layers.push({
            id: layerId,
            type: 'raster',
            source: sourceId,
            paint: {
                'raster-opacity': (layerProperties.opacity !== undefined) ? layerProperties.opacity : 1
            }
        });
    }

    return layers;
}

// Calculate zoom level from extent width
function calculateZoomLevel(width) {
    // Approximate zoom level calculation
    // This is a simplified calculation
    if (width > 1000000) return 4;
    if (width > 100000) return 7;
    if (width > 10000) return 10;
    if (width > 1000) return 13;
    return 16;
}

// Handle map click for feature queries
function handleMapClick(e) {
    var bbox = [[e.lngLat.lng - 0.001, e.lngLat.lat - 0.001],
                [e.lngLat.lng + 0.001, e.lngLat.lat + 0.001]];

    var features = app.map.querySourceFeatures({sourceId: undefined}, {layers: Object.keys(app.layers)});

    if (features.length > 0) {
        showQueryResult(e.lngLat, features[0]);
    }
}

// Show query result in popup
function showQueryResult(lngLat, feature) {
    var html = '<div>';

    if (feature.properties) {
        for (var key in feature.properties) {
            html += '<p><strong>' + key + ':</strong> ' + feature.properties[key] + '</p>';
        }
    }

    html += '</div>';

    var popupContent = document.getElementById('popupcontent');
    if (popupContent) {
        popupContent.innerHTML = html;
    }

    var popup = document.getElementById('popup');
    if (popup) {
        popup.style.display = 'block';
    }
}

// Hide layer
function hideLayer(layerId, remove_obj) {
    if (app.layers[layerId]) {
        app.layers[layerId].visible = false;
        var layer = app.layers[layerId];

        if (app.map.getLayer(layerId)) {
            app.map.setLayoutProperty(layerId, 'visibility', 'none');
        }
        if (app.map.getLayer(layerId + '-fill')) {
            app.map.setLayoutProperty(layerId + '-fill', 'visibility', 'none');
        }
        if (app.map.getLayer(layerId + '-outline')) {
            app.map.setLayoutProperty(layerId + '-outline', 'visibility', 'none');
        }
    }
}

// Show layer
function showLayer(layerId) {
    if (app.layers[layerId]) {
        app.layers[layerId].visible = true;

        if (app.map.getLayer(layerId)) {
            app.map.setLayoutProperty(layerId, 'visibility', 'visible');
        }
        if (app.map.getLayer(layerId + '-fill')) {
            app.map.setLayoutProperty(layerId + '-fill', 'visibility', 'visible');
        }
        if (app.map.getLayer(layerId + '-outline')) {
            app.map.setLayoutProperty(layerId + '-outline', 'visibility', 'visible');
        }
    }
}

// Hide all layers
function hideAllLayers(remove_obj) {
    for (var id in app.layers) {
        hideLayer(id, remove_obj);
    }
}

// Set layer opacity
function setLayerOpacity(layerId, opacity) {
    if (app.layers[layerId] && app.map) {
        var layer = app.layers[layerId];

        if (app.map.getLayer(layerId)) {
            if (layer.geomType === 'polygon') {
                app.map.setPaintProperty(layerId + '-fill', 'fill-opacity', opacity * 0.5);
                app.map.setPaintProperty(layerId + '-outline', 'line-opacity', opacity);
            } else {
                var paintProperty = (layer.geomType === 'point') ? 'circle-opacity' : 'line-opacity';
                app.map.setPaintProperty(layerId, paintProperty, opacity);
            }
        }
    }
}

// Load script file
function loadScriptFile(path, callback) {
    var url = new URL(path, document.baseURI);

    var elms = document.head.getElementsByTagName("script");
    for (var i = 0; i < elms.length; i++) {
        if (elms[i].src == url) {
            if (callback) callback();
            return false;
        }
    }

    var s = document.createElement("script");
    s.src = url;
    if (callback) s.onload = callback;
    document.head.appendChild(s);
    return true;
}

// Request rendering (callback for off-screen rendering)
function requestRendering() {
    // For MapLibre GL, rendering is continuous, but we need to notify Python when done
    if (app.pyObj && app.pyObj.emitRequestedRenderingFinished) {
        requestAnimationFrame(function() {
            app.pyObj.emitRequestedRenderingFinished();
        });
    }
}

// Message bar functions
var barTimerId = null;
function showMessageBar(message, timeout_ms, warning) {
    if (barTimerId !== null) {
        clearTimeout(barTimerId);
        barTimerId = null;
    }
    if (timeout_ms) {
        barTimerId = setTimeout(closeMessageBar, timeout_ms);
    }

    var msgContent = document.getElementById('msgcontent');
    if (msgContent) {
        msgContent.innerHTML = message;
    }

    var e = document.getElementById('msgbar');
    if (e) {
        e.style.display = "block";
        if (warning) {
            e.classList.add("warning");
        }
        else {
            e.classList.remove("warning");
        }
    }
}

function closeMessageBar() {
    var e = document.getElementById('msgbar');
    if (e) {
        e.style.display = "none";
    }
    barTimerId = null;
}

function showStatusMessage(message, timeout_ms) {
    if (app.pyObj && app.pyObj.showStatusMessage) {
        app.pyObj.showStatusMessage(message, timeout_ms || 0);
    }
    console.log(message);
}

function clearStatusMessage() {
    showStatusMessage("");
}

// Camera/view functions (adapted for MapLibre GL)
function switchCamera(is_ortho) {
    // MapLibre GL doesn't have orthographic/perspective switching in the same way
    // This is a no-op for MapLibre GL
    console.log("Camera mode setting ignored for MapLibre GL");
}

function cameraState(flat) {
    var center = app.map.getCenter();
    var zoom = app.map.getZoom();
    var pitch = app.map.getPitch();
    var bearing = app.map.getBearing();

    if (flat) {
        return {
            lng: center.lng,
            lat: center.lat,
            zoom: zoom,
            pitch: pitch,
            bearing: bearing
        };
    }

    return {
        center: {lng: center.lng, lat: center.lat},
        zoom: zoom,
        pitch: pitch,
        bearing: bearing
    };
}

function setCameraState(s) {
    var options = {
        duration: 1000
    };

    if (s.center !== undefined) {
        options.center = s.center;
        options.zoom = s.zoom;
        options.pitch = s.pitch;
        options.bearing = s.bearing;
    } else {
        options.center = [s.lng, s.lat];
        options.zoom = s.zoom;
        options.pitch = s.pitch;
        options.bearing = s.bearing;
    }

    app.map.easeTo(options);
}

// Preview functions
function setPreviewEnabled(enabled) {
    var e = document.getElementById('cover');
    if (e) {
        e.style.display = (enabled) ? "none" : "block";
        if (!enabled) {
            e.innerHTML = '<img src="../../Qgis2threejs.png">';
        }
    }
}

function setBackgroundColor(color, alpha) {
    // MapLibre GL doesn't have a direct background color property like three.js
    // This would need to be handled differently, e.g., with a background layer
    console.log("Background color setting: #" + color.toString(16) + ", alpha: " + alpha);
}

// Canvas/image functions
function saveCanvasImage(width, height) {
    var canvas = app.map.getCanvas();
    if (canvas && app.pyObj) {
        app.pyObj.saveImage(canvas.toDataURL("image/png"));
    }
}

function copyCanvasToClipboard(width, height) {
    var canvas = app.map.getCanvas();
    if (canvas && app.pyObj) {
        app.pyObj.copyToClipboard(canvas.toDataURL("image/png"));
    }
}

// Utility functions
function createLayerId() {
    return 'layer-' + Date.now() + '-' + Math.random().toString(36).substr(2, 9);
}

// Polyfill for toBlob if needed
if (!HTMLCanvasElement.prototype.toBlob) {
    Object.defineProperty(HTMLCanvasElement.prototype, 'toBlob', {
        value: function (callback, type, quality) {
            var binStr = atob(this.toDataURL(type, quality).split(',')[1]),
                len = binStr.length,
                arr = new Uint8Array(len);

            for (var i = 0; i < len; i++) {
                arr[i] = binStr.charCodeAt(i);
            }

            callback(new Blob([arr], {type: type || 'image/png'}));
        }
    });
}
