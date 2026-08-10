// (C) 2014 Minoru Akagi
// SPDX-License-Identifier: MIT

import { CameraState } from "./types.js";

export const conf = {
    renderer: {
        /** HD-DPI support */
        hiDpi: true
    },

    texture: {
        /** Zero means max available value. negative value means max / -v. */
        anisotropy: -4
    },

    //// Scene

    /** Enables automatic camera height adjustment */
    autoAdjustCameraPos: true,

    /** Background color. null is sky. @type: {null | number} */
    bgColor: null,

    //// Camera
    orthoCamera: false,

    /** Z-up. */
    viewpoint: {
        /** Camera presets in map coordinates. */
        /** @type: {CameraState | null} */
        preset: null,

        /** Default value is assumed that origin is (0, 0, 0) and base extent width in 3D world coordinates is 1. */
        /** @type: {CameraState} */
        default: {
            pos: { x: 0, y: -1, z: 1 },
            lookAt: { x: 0, y: 0, z: 0 }
        }
    },

    //// Light
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

    //// Layer
    /** Set every layer visible property to true on load if set to true. */
    allVisible: false,

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

    // Widgets
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

    // Animation
    animation: {
        enabled: false,
        startOnLoad: false,
        easingCurve: "Cubic",
        repeat: false
    },

    // Others
    qmarker: {
        radius: 0.004,
        color: 0xffff00,
        opacity: 0.8,

        /** size factor for ortho camera */
        k: 0.2
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
        /** dat-gui */
        customPlane: false
    },

    /** @type: {number} */
    debugMode: 0,

    /** @type: {number | null} */
    qgisVersion: null,

    /** @type: {{Record<string, any>} | null } */
    preview: null
};

export type Config = typeof conf;
