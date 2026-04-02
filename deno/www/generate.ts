import { toSSG } from "hono/ssg";
import { createApp } from "./app.ts";
import { walk } from "@std/fs/walk";
import { basename, dirname, fromFileUrl, join, relative } from "@std/path";
import { transform as cssTransform } from "lightningcss";
import * as esbuild from "esbuild";
import { minify as minifyHtml } from "html-minifier-terser";

const app = await createApp();

const outDir = "./out/static";

const denoFS = {
  writeFile: async (path: string, data: string | Uint8Array) => {
    const encoder = new TextEncoder();
    const bytes = typeof data === "string" ? encoder.encode(data) : data;
    await Deno.writeFile(path, bytes);
  },
  mkdir: async (path: string, options: { recursive: boolean }) => {
    await Deno.mkdir(path, options);
  },
};

// Generate HTML pages via SSG
const result = await toSSG(app, denoFS, { dir: outDir });

if (!result.success) {
  console.error("SSG generation failed:", result.error);
  Deno.exit(1);
}

console.log(`Generated ${result.files?.length ?? 0} HTML pages`);

// Copy static assets
const staticDir = fromFileUrl(new URL("./static", import.meta.url));
let staticCount = 0;
for await (const entry of walk(staticDir, { includeDirs: false })) {
  const rel = relative(staticDir, entry.path);
  const dest = join(outDir, rel);
  await Deno.mkdir(dirname(dest), { recursive: true });
  await Deno.copyFile(entry.path, dest);
  staticCount++;
}
console.log(`Copied ${staticCount} static files`);

// Post-process: minify CSS
let cssCount = 0;
for await (const entry of walk(outDir, { exts: [".css"], includeDirs: false })) {
  const src = await Deno.readFile(entry.path);
  const { code } = cssTransform({
    filename: basename(entry.path),
    code: src,
    minify: true,
  });
  await Deno.writeFile(entry.path, code);
  cssCount++;
}
console.log(`Minified ${cssCount} CSS files`);

// Post-process: minify JS
let jsCount = 0;
for await (const entry of walk(outDir, { exts: [".js"], includeDirs: false })) {
  const src = await Deno.readTextFile(entry.path);
  const { code } = await esbuild.transform(src, { minify: true, loader: "js" });
  await Deno.writeTextFile(entry.path, code);
  jsCount++;
}
await esbuild.stop();
console.log(`Minified ${jsCount} JS files`);

// Post-process: minify HTML
let htmlCount = 0;
for await (
  const entry of walk(outDir, { exts: [".html"], includeDirs: false })
) {
  const src = await Deno.readTextFile(entry.path);
  const minified = await minifyHtml(src, {
    collapseWhitespace: true,
    removeComments: true,
    minifyCSS: false,
    minifyJS: false,
  });
  await Deno.writeTextFile(entry.path, minified);
  htmlCount++;
}
console.log(`Minified ${htmlCount} HTML files`);

console.log(`Output in ${outDir}/`);
