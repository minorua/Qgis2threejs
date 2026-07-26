// (C) 2014 Minoru Akagi
// SPDX-License-Identifier: MIT

import { THREE } from "./three.js";

export const conf = {
    // renderer
    renderer: {
        hiDpi: true       // HD-DPI support
    },

    texture: {
        anisotropy: -4    // zero means max available value. negative value means max / -v.
    },

    // scene
    autoAdjustCameraPos: true,  // automatic camera height adjustment
    bgColor: null,              // null is sky

    // camera
    orthoCamera: false,
    viewpoint: {      // z-up
        default: {      // assumed that origin is (0, 0, 0) and base extent width in 3D world coordinates is 1
            pos: new THREE.Vector3(0, -1, 1),
            lookAt: new THREE.Vector3()
        }
    },

    // light
    lights: {
        directional: [
            {
                type: "ambient",
                color: 0x999999,
                intensity: 2.513
            },
            {
                type: "directional",
                color: 0xffffff,
                intensity: 2.513,
                azimuth: 220,   // azimuth of light, in degrees. default light azimuth of gdaldem hillshade is 315.
                altitude: 45    // altitude angle in degrees.
            }
        ],
        point: [
            {
                type: "ambient",
                color: 0x999999,
                intensity: 2.827
            },
            {
                type: "point",
                color: 0xffffff,
                intensity: 3,
                decay: 0.01,
                height: 10
            }
        ]
    },

    // layer
    allVisible: false,   // set every layer visible property to true on load if set to true

    line: {
        dash: {
            dashSize: 1,
            gapSize: 0.5
        }
    },

    label: {
        visible: true,
        canvasHeight: 64,
        clickable: true
    },

    // widgets
    navigation: {
        enabled: true,
        top: null,
        bottom: 0
    },

    northArrow: {
        color: 0x8b4513,
        cameraDistance: 30,
        enabled: false
    },

    // animation
    animation: {
        enabled: false,
        startOnLoad: false,
        easingCurve: "Cubic",
        repeat: false
    },

    // others
    qmarker: {
        radius: 0.004,
        color: 0xffff00,
        opacity: 0.8,
        k: 0.2    // size factor for ortho camera
    },

    measure: {
        marker: {
            radius: 0.004,
            color: 0xffff00,
            opacity: 0.5
            /* k: 0.2 */
        },
        line: {
            color: 0xffff00
        }
    },

    coord: {
        visible: true,
        latlon: false
    },

    gui: {
        customPlane: false		// dat-gui
    },

    debugMode: false,

    preview: null
};
