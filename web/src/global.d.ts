import type { App, Gui, Modules, PyObj } from "./types.ts";
import type { Config } from "./conf.ts";

interface QWebChannelObjects {
    bridge: PyObj;
}

interface QWebChannelInstance {
    objects: QWebChannelObjects;
}

declare global {
    // For testing: exposed in core.ts
    var __qgis2threejs: {
        app: App;
        conf: Config;
        gui: Gui;
        modules: Modules;
    };

    // JavaScript dependencies
    const dat: typeof import("dat.gui");
    const proj4: typeof import("proj4");
    const TWEEN: typeof import("@tweenjs/tween.js");

    // Qt WebChannel (used by the preview)
    class QWebChannel {
        constructor(
            transport: unknown,
            callback: (channel: QWebChannelInstance) => void
        );
    }

    const qt: {
        webChannelTransport: unknown;
    };

    var pyObj: PyObj;
}
