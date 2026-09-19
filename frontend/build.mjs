import { build } from "esbuild";

await build({
  entryPoints: ["frontend/src/calendar-board.jsx"],
  bundle: true,
  format: "iife",
  target: ["es2018"],
  outfile: "static/js/react/calendar-board.js",
  jsx: "automatic",
  sourcemap: false,
  minify: false,
});
