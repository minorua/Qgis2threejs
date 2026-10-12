// APIs of the bundled libraries (except three.js) that web/src depends on.
//   props:      dotted paths that must exist on the library object
//   protos:     class name -> members that must exist on Class.prototype
//   instance:   class name -> members that must exist on a new instance
//               (properties assigned in constructors)
//   converter / controller: members of objects returned by proj4() / GUI#add()

export default {
  tween: {
    used_in: "web/src/animation.ts, app.ts",
    props: ["Easing.Linear.None", "Tween", "update", "removeAll", "getAll"],
    protos: {
      Tween: ["delay", "onStart", "onUpdate", "onComplete", "to", "chain", "start", "stop"],
    },
  },

  proj4: {
    used_in: "web/src/scene.ts, gui.ts",
    converter: ["forward", "inverse"],
  },

  datgui: {
    used_in: "web/src/gui_dat.ts",
    props: ["GUI"],
    protos: {
      GUI: ["add", "addFolder", "addColor", "open", "close", "destroy"],
    },
    controller: ["name", "onChange", "min", "max", "setValue", "updateDisplay"],
    instance: { GUI: ["domElement"] },
  },

  meshline: {
    used_in: "web/src/material.ts, layer/linelayer.ts",
    props: ["MeshLineMaterial", "MeshLineGeometry", "raycast"],
  },

  tiles: {
    used_in: "web/src/layer/demlayer.ts, tiles/demplugin.ts",
    props: ["TilesRenderer", "LRUCache", "DownloadPriorityQueue"],
    protos: {
      TilesRenderer: ["registerPlugin", "setCamera", "setResolutionFromRenderer", "addEventListener", "preprocessTileset", "update"],
    },
    instance: {
      TilesRenderer: ["group", "lruCache", "downloadQueue"],
      LRUCache: ["itemList", "unloadPriorityCallback"],
      DownloadPriorityQueue: ["maxJobsPerOrigin", "priorityCallback"],
    },
  },
};
