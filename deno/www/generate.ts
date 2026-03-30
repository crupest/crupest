import { toSSG } from "hono/ssg";
import { createApp } from "./app.ts";
import { walk } from "@std/fs/walk";
import { dirname, fromFileUrl, join, relative } from "@std/path";

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

// Copy static assets (images, JS, etc.)
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

// Copy CSS files
const cssDir = fromFileUrl(new URL("./css", import.meta.url));
let cssCount = 0;
for await (const entry of walk(cssDir, { includeDirs: false })) {
  const rel = relative(cssDir, entry.path);
  const dest = join(outDir, "css", rel);
  await Deno.mkdir(dirname(dest), { recursive: true });
  await Deno.copyFile(entry.path, dest);
  cssCount++;
}
console.log(`Copied ${cssCount} CSS files`);

console.log(`Total output in ${outDir}/`);
