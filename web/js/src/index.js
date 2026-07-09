// (C) 2014 Minoru Akagi
// SPDX-License-Identifier: MIT

import { THREE } from "./three.js";

import { app, conf, deg2rad, gui, modules, Tweens } from "./core.js";
import "./app.js";
import "./gui.js";
import "./tween.js";
import { E } from "./utils.js";

export const VERSION = "3.1";
export { app, conf, gui, modules, Tweens, deg2rad, E };

window["THREE"] = THREE;
window["Q3D"] = { app, conf, gui, modules, E, VERSION };
