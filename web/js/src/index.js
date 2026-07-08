// (C) 2014 Minoru Akagi
// SPDX-License-Identifier: MIT

import { THREE } from "./three.js";

import { app, gui, conf, deg2rad, Tweens, THREE_EX } from "./core.js";
import "./app.js";
import "./gui.js";
import "./tween.js";
import { E } from "./utils.js";

export const VERSION = "3.1";
export { app, gui, conf, deg2rad, Tweens, THREE_EX };

window["THREE"] = THREE;
window["THREE_EX"] = THREE_EX;
window["Q3D"] = { app, gui, conf, E, VERSION };
