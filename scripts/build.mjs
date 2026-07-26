import * as esbuild from "esbuild";

const minify = process.argv.includes("--minify");
const sourcemap = process.argv.includes("--sourcemap");
const watch = process.argv.includes("--watch");

const ctx = await esbuild.context({
    entryPoints: [
        "./src/Qgis2threejs.ts",
        "./src/gui_dat.ts",
        "./src/preview.ts"
    ],
    bundle: true,
    format: "esm",
    outdir: "./web/js",
    external: ["three", "three/*", "./Qgis2threejs.js"],
    minify,
    sourcemap
});

if (watch) {
    await ctx.watch();
    console.log("Watching for changes...");
} else {
    try {
        await ctx.rebuild();
    } catch (error) {
        console.error("Failed to build JavaScript files.", error);
    } finally {
        await ctx.dispose();
    }
}
