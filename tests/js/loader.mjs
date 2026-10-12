// Helpers to load the JavaScript libraries bundled under web/js/lib.
import { createRequire } from "node:module";
import { fileURLToPath, pathToFileURL } from "node:url";
import path from "node:path";
import { JSDOM } from "jsdom";

const here = path.dirname(fileURLToPath(import.meta.url));
export const libDir = path.resolve(here, "../../web/js/lib");

const require = createRequire(import.meta.url);

export function loadESM(relPath) {
  return import(pathToFileURL(path.join(libDir, relPath)).href);
}

// UMD builds (tween.js, proj4.js)
export function loadUMD(relPath) {
  return require(path.join(libDir, relPath));
}

// dat.gui needs a DOM both at load time and when creating a GUI.
// Installs DOM globals and returns { lib, restore }.
export function loadDatGui() {
  const dom = new JSDOM("<!DOCTYPE html><body></body>");
  const keys = ["window", "document", "navigator", "HTMLElement"];
  const saved = keys.map(k => [k, Object.getOwnPropertyDescriptor(globalThis, k)]);

  for (const k of keys) {
    Object.defineProperty(globalThis, k, { value: dom.window[k], configurable: true, writable: true });
  }

  const restore = () => {
    for (const [k, d] of saved) {
      if (d) Object.defineProperty(globalThis, k, d);
      else delete globalThis[k];
    }
  };

  try {
    return { lib: require(path.join(libDir, "dat-gui/dat.gui.js")), restore };
  } catch (e) {
    restore();
    throw e;
  }
}

// Returns the value at a dotted path, or undefined.
export function getPath(obj, dotted) {
  let o = obj;
  for (const key of dotted.split(".")) {
    if (o === null || o === undefined) return undefined;
    o = o[key];
  }
  return o;
}
