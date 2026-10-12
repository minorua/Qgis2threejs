import { fileURLToPath, pathToFileURL } from "node:url";
import path from "node:path";

const here = path.dirname(fileURLToPath(import.meta.url));
const threeUrl = pathToFileURL(path.resolve(here, "../../web/js/lib/three/three.module.js")).href;

export async function resolve(specifier, context, nextResolve) {
  if (specifier === "three") {
    return { url: threeUrl, shortCircuit: true };
  }
  return nextResolve(specifier, context);
}
