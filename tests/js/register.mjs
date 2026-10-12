// Registers a resolve hook that maps the bare specifier "three" to the bundled copy.
import { register } from "node:module";

register("./resolve-hooks.mjs", import.meta.url);
