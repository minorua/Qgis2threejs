import type { PyObj } from "./types.ts";

interface QWebChannelObjects {
    bridge: PyObj;
}

interface QWebChannelInstance {
    objects: QWebChannelObjects;
}

declare global {
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

    // Declaration merging
    interface Window {
        pyObj: PyObj;
    }

    // JavaScript dependencies
    const dat: typeof import("dat.gui");
    const proj4: typeof import("proj4");
    const TWEEN: typeof import("@tweenjs/tween.js");
}
