// (C) 2022 Minoru Akagi
// SPDX-License-Identifier: MIT

import { app, conf, gui } from "./core.js";
import { convertToDMS, E } from "./utils.js";

const VIS = "visible";

function CE(tagName, parent, innerHTML) {
    const elem = document.createElement(tagName);
    if (parent) parent.appendChild(elem);
    if (innerHTML) elem.innerHTML = innerHTML;
    return elem;
}

function ON_CLICK(id, listener) {
    const e = document.getElementById(id);
    if (e) e.addEventListener("click", listener);
}

gui.init = () => {
    // tool buttons
    ON_CLICK("layerbtn", () => {
        if (!gui.layerPanel.initialized) gui.layerPanel.init();

        if (gui.layerPanel.isVisible()) {
            gui.layerPanel.hide();
        }
        else {
            if (gui.popup.isVisible()) {
                gui.popup.hide();
            }
            gui.layerPanel.show();
        }
    });

    ON_CLICK("infobtn", () => {
        gui.layerPanel.hide();

        if (gui.popup.isVisible() && gui.popup.content == "pageinfo") gui.popup.hide();
        else gui.showInfo();
    });

    const btn = E("animbtn");
    if (conf.animation.enabled && btn) {
        const anim = app.animation.keyframes;

        const playButton = () => {
            btn.className = "playbtn";
        };

        const pauseButton = () => {
            btn.className = "pausebtn";
        };

        btn.onclick = () => {
            if (anim.isActive) {
                anim.pause();
                playButton();
            }
            else if (anim.isPaused) {
                anim.resume();
                pauseButton();
            }
            else anim.start();
        };

        app.addEventListener('animationStarted', pauseButton);
        app.addEventListener('animationStopped', playButton);
    }

    // popup
    ON_CLICK("closebtn", app.cleanView);
    ON_CLICK("zoomtolayer", () => app.cameraAction.zoomToLayer(app.selectedLayer));
    ON_CLICK("zoomtopoint", () => app.cameraAction.zoom());
    ON_CLICK("orbitbtn", () => app.cameraAction.orbit());
    ON_CLICK("measurebtn", () => app.measure.start());

    // narrative box
    ON_CLICK("nextbtn", () => app.animation.keyframes.resume());

    // attribution
    if (typeof proj4 === "undefined") {
        const e = E("lib_proj4js");
        if (e) e.classList.add("hidden");
    }

    // initialize modules
    for (const mod of gui.modules) {
        mod.init();
    }
};

gui.clean = () => {
    gui.popup.hide();
    if (gui.layerPanel.initialized) gui.layerPanel.hide();
};

gui.popup = {

    modal: false,

    content: null,

    timerId: null,

    isVisible: function () {
        return E("popup").classList.contains(VIS);
    },

    // show box
    // obj: html, element or content id ("queryresult" or "pageinfo")
    // modal: boolean
    // duration: int [milliseconds]
    show: function (obj, title, modal, duration) {

        if (modal) app.pause();
        else if (this.modal) app.resume();

        this.content = obj;
        this.modal = Boolean(modal);

        const e = E("layerpanel");
        if (e) e.classList.remove(VIS);

        const content = E("popupcontent");
        [content, E("queryresult"), E("pageinfo")].forEach((e) => {
            if (e) e.classList.remove(VIS);
        });

        if (obj == "queryresult" || obj == "pageinfo") {
            E(obj).classList.add(VIS);
        }
        else {
            if (obj instanceof HTMLElement) {
                content.innerHTML = "";
                content.appendChild(obj);
            }
            else {
                content.innerHTML = obj;
            }
            content.classList.add(VIS);
        }
        E("popupbar").innerHTML = title || "";
        E("popup").classList.add(VIS);

        if (this.timerId !== null) {
            clearTimeout(this.timerId);
            this.timerId = null;
        }

        if (duration) {
            this.timerId = setTimeout(() => gui.popup.hide(), duration);
        }
    },

    hide: function () {
        E("popup").classList.remove(VIS);
        if (this.timerId !== null) clearTimeout(this.timerId);
        this.timerId = null;
        this.content = null;
        if (this.modal) app.resume();
    }

};

gui.showInfo = () => {
    const e = E("urlbox");
    if (e) e.value = app.currentViewUrl();
    gui.popup.show("pageinfo");
};

gui.showQueryResult = (point, layer, obj, show_coords) => {
    let e;
    // layer name
    e = E("qr_layername");
    if (layer && e) e.innerHTML = layer.properties.name;

    // clicked coordinates
    e = E("qr_coords_table");
    if (e) {
        if (show_coords) {
            e.classList.remove("hidden");

            const pt = app.scene.toMapCoordinates(point);

            e = E("qr_coords");

            if (conf.coord.latlon) {
                const lonLat = proj4(app.scene.userData.proj).inverse([pt.x, pt.y]);
                e.innerHTML = convertToDMS(lonLat[1], lonLat[0]) + ", Elev. " + pt.z.toFixed(2);
            }
            else {
                e.innerHTML = [pt.x.toFixed(2), pt.y.toFixed(2), pt.z.toFixed(2)].join(", ");
            }
        }
        else {
            e.classList.add("hidden");
        }
    }

    e = E("qr_attrs_table");
    if (e) {
        for (let i = e.children.length - 1; i >= 0; i--) {
            if (e.children[i].tagName.toUpperCase() == "TR") e.removeChild(e.children[i]);
        }

        if (layer && layer.properties.propertyNames !== undefined) {
            for (let i = 0, l = layer.properties.propertyNames.length; i < l; i++) {
                const row = document.createElement("tr");
                row.innerHTML = "<td>" + layer.properties.propertyNames[i] + "</td>" +
                                "<td>" + obj.userData.properties[i] + "</td>";
                e.appendChild(row);
            }
            e.classList.remove("hidden");
        }
        else {
            e.classList.add("hidden");
        }
    }
    gui.popup.show("queryresult");
};

gui.showPrintDialog = () => {

    var f = CE("form");
    f.className = "print";

    var d1 = CE("div", f, "Image Size");
    d1.style.textDecoration = "underline";

    var d2 = CE("div", f),
        l1 = CE("label", d2, "Width:"),
        width = CE("input", d2);
    d2.style.cssFloat = "left";
    l1.htmlFor = width.id = width.name = "printwidth";
    width.type = "text";
    width.value = app.width;
    CE("span", d2, "px,");

    var d3 = CE("div", f),
        l2 = CE("label", d3, "Height:"),
        height = CE("input", d3);
    l2.htmlFor = height.id = height.name = "printheight";
    height.type = "text";
    height.value = app.height;
    CE("span", d3, "px");

    var d4 = CE("div", f),
        ka = CE("input", d4);
    ka.type = "checkbox";
    ka.checked = true;
    CE("span", d4, "Keep Aspect Ratio");

    var d5 = CE("div", f, "Option");
    d5.style.textDecoration = "underline";

    var d6 = CE("div", f),
        bg = CE("input", d6);
    bg.type = "checkbox";
    bg.checked = true;
    CE("span", d6, "Fill Background");

    var d7 = CE("div", f),
        ok = CE("span", d7, "OK"),
        cancel = CE("span", d7, "Cancel");
    d7.className = "buttonbox";

    CE("input", f).type = "submit";

    // event handlers
    // width and height boxes
    var aspect = app.width / app.height;

    width.oninput = () => {
        if (ka.checked) height.value = Math.round(width.value / aspect);
    };

    height.oninput = () => {
        if (ka.checked) width.value = Math.round(height.value * aspect);
    };

    ok.onclick = () => {
        gui.popup.show("Rendering...");
        window.setTimeout(() => app.saveCanvasImage(width.value, height.value, bg.checked), 10);
    };

    cancel.onclick = app.cleanView;

    // enter key pressed
    f.onsubmit = () => {
        ok.onclick();
        return false;
    };

    gui.popup.show(f, "Save Image", true);   // modal
};

gui.layerPanel = {

    init: function () {
        const panel = E("layerpanel");
        app.scene.forEachLayer((layer, layerId) => {
            const p = layer.properties;
            const item = CE("div", panel);
            item.className = "layer";

            // visible
            let e = CE("div", item, "<input type='checkbox'" +  ((p.visible) ? " checked" : "") + ">" + p.name);
            e.querySelector("input[type=checkbox]").addEventListener("change", function () {
                layer.visible = this.checked;
            });

            // material dropdown
            let select;
            if (p.mtlNames && p.mtlNames.length > 1) {
                select = CE("select", CE("div", item, "Material: "));
                for (var i = 0; i < p.mtlNames.length; i++) {
                    CE("option", select, p.mtlNames[i]).setAttribute("value", i);
                }
                select.value = p.mtlIdx;
            }

            // opacity slider
            e = CE("div", item, "Opacity: <input type='range'><output></output>");
            const slider = e.querySelector("input[type=range]");
            const label = e.querySelector("output");
            const setLabel = (opacity) => {
                label.innerHTML = opacity + " %";
            };

            const o = Math.round(layer.opacity * 100);
            slider.value = o;
            setLabel(o);

            slider.addEventListener("input", function () {
                setLabel(this.value);
            });
            slider.addEventListener("change", function () {
                setLabel(this.value);
                layer.opacity = this.value / 100;
            });

            if (select) {
                select.addEventListener("change", function () {
                    layer.currentMtlIndex = this.value;
                    const o = Math.round(layer.opacity * 100);
                    slider.value = o;
                    setLabel(o);
                });
            }
        });
        gui.layerPanel.initialized = true;
    },

    isVisible: function () {
        return E("layerpanel").classList.contains(VIS);
    },

    show: function () {
        E("layerpanel").classList.add(VIS);
    },

    hide: function () {
        E("layerpanel").classList.remove(VIS);
    }

};
