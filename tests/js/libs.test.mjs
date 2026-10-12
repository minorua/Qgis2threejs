// Existence tests for the JavaScript libraries bundled in web/js/lib (three.js excluded).
// Run: npm run test:js
import { after, describe, it } from "node:test";
import assert from "node:assert/strict";

import spec from "./api-spec.mjs";
import { getPath, loadDatGui, loadESM, loadUMD } from "./loader.mjs";

function checkProps(lib, paths) {
  for (const p of paths || []) {
    it(`has ${p}`, () => assert.notEqual(getPath(lib, p), undefined, `${p} is missing`));
  }
}

function checkProtos(lib, protos) {
  for (const [cls, members] of Object.entries(protos || {})) {
    for (const m of members) {
      it(`${cls}.prototype has ${m}`, () => {
        assert.equal(typeof lib[cls], "function", `${cls} is not a class`);
        assert.ok(m in lib[cls].prototype, `${cls}.prototype.${m} is missing`);
      });
    }
  }
}

function checkInstances(lib, instance, factories = {}) {
  for (const [cls, members] of Object.entries(instance || {})) {
    const make = factories[cls] || (() => new lib[cls]());
    for (const m of members) {
      it(`new ${cls}() has ${m}`, () => assert.ok(m in make(), `${cls}#${m} is missing`));
    }
  }
}

describe("tween.js", () => {
  const s = spec.tween;
  const lib = loadUMD("tweenjs/tween.js");
  checkProps(lib, s.props);
  checkProtos(lib, s.protos);
});

describe("proj4js", () => {
  const s = spec.proj4;
  const proj4 = loadUMD("proj4js/proj4.js");

  it("is a function", () => assert.equal(typeof proj4, "function"));
  for (const m of s.converter) {
    it(`proj4(def) has ${m}`, () => assert.equal(typeof proj4("EPSG:4326")[m], "function"));
  }
});

describe("dat.gui", () => {
  const s = spec.datgui;
  const { lib, restore } = loadDatGui();
  after(restore);

  checkProps(lib, s.props);
  checkProtos(lib, s.protos);
  checkInstances(lib, s.instance, { GUI: () => new lib.GUI({ autoPlace: false }) });

  for (const m of s.controller) {
    it(`Controller has ${m}`, () => {
      const gui = new lib.GUI({ autoPlace: false });
      assert.equal(typeof gui.add({ v: 1 }, "v")[m], "function");
    });
  }
});

describe("meshline", async () => {
  const lib = await loadESM("meshline/meshline.js");
  checkProps(lib, spec.meshline.props);
});

describe("3d-tiles-renderer", async () => {
  const s = spec.tiles;
  const lib = await loadESM("3d-tiles-renderer/3d-tiles-renderer.js");
  checkProps(lib, s.props);
  checkProtos(lib, s.protos);
  checkInstances(lib, s.instance);
});
