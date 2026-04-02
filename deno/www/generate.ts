import { toSSG } from "hono/ssg";
import { createApp } from "./app.ts";
import { walk } from "@std/fs/walk";
import { basename, dirname, join, relative } from "@std/path";

import { transform as transformCss } from "lightningcss";
import { transform as transformJs } from "esbuild";
// @ts-types="npm:@types/html-minifier-terser"
import { minify as minifyHtml } from "html-minifier-terser";

class StaticFile {
  readonly #src: string;
  readonly #dest: string;
  #content: Uint8Array | null = null;
  #textContent: string | null = null;

  constructor(src: string, dest: string) {
    this.#src = src;
    this.#dest = dest;
  }

  get src(): string {
    return this.#src;
  }

  get dest(): string {
    return this.#dest;
  }

  async getContent(): Promise<Uint8Array> {
    if (this.#content == null) {
      this.#content = await Deno.readFile(this.#src);
    }
    return this.#content;
  }

  async getTextContent(): Promise<string> {
    if (this.#textContent == null) {
      const bytes = await this.getContent();
      const decoder = new TextDecoder();
      this.#textContent = decoder.decode(bytes);
    }
    return this.#textContent;
  }

  setContent(content: string | Uint8Array): Promise<void> {
    if (typeof content === "string") {
      const encoder = new TextEncoder();
      this.#content = encoder.encode(content);
      this.#textContent = content;
    } else {
      this.#content = content;
      this.#textContent = null;
    }
    return Promise.resolve();
  }

  async writeToDest(): Promise<void> {
    return Deno.writeFile(this.#dest, await this.getContent());
  }
}

interface Processer {
  needProcess(file: StaticFile): Promise<boolean>;
  process(file: StaticFile): Promise<string | Uint8Array>;
}

class ProcesserBase {
  count = 0;
}

class CssProcesser extends ProcesserBase implements Processer {
  needProcess(file: StaticFile): Promise<boolean> {
    return Promise.resolve(file.src.endsWith(".css"));
  }

  async process(file: StaticFile): Promise<Uint8Array> {
    this.count++;
    const { code } = transformCss({
      filename: basename(file.src),
      code: await file.getContent(),
      minify: true,
    });
    return code;
  }
}

class JsProcesser extends ProcesserBase implements Processer {
  needProcess(file: StaticFile): Promise<boolean> {
    return Promise.resolve(file.src.endsWith(".js"));
  }

  async process(file: StaticFile): Promise<string> {
    this.count++;
    const { code } = await transformJs(await file.getContent(), {
      minify: true,
      loader: "js",
    });
    return code;
  }
}

class HtmlProcesser extends ProcesserBase implements Processer {
  needProcess(file: StaticFile): Promise<boolean> {
    return Promise.resolve(file.src.endsWith(".html"));
  }

  async process(file: StaticFile): Promise<string> {
    this.count++;
    return await minifyHtml(await file.getTextContent(), {
      collapseWhitespace: true,
      removeComments: true,
      minifyCSS: true,
      minifyJS: true,
    });
  }
}

const cssProcesser = new CssProcesser();
const jsProcesser = new JsProcesser();
const htmlProcesser = new HtmlProcesser();

const processers: Processer[] = [cssProcesser, jsProcesser, htmlProcesser];

const outDir = "./out";
const staticDir = join(import.meta.dirname!, "static");

await Deno.remove(outDir, { recursive: true });

// Generate HTML pages via SSG
const app = await createApp();
const result = await toSSG(app, {
  writeFile: (path: string, data: string | Uint8Array) =>
    typeof data === "string"
      ? Deno.writeTextFile(path, data)
      : Deno.writeFile(path, data),
  mkdir: Deno.mkdir,
}, { dir: outDir });

if (!result.success) {
  console.error("SSG generation failed:", result.error);
  Deno.exit(1);
}

console.log(`SSG generated ${result.files.length} files.`);

let staticFileCount = 0;
for await (const entry of walk(staticDir, { includeDirs: false })) {
  const relativePath = relative(staticDir, entry.path);
  const destPath = join(outDir, relativePath);
  await Deno.mkdir(dirname(destPath), { recursive: true });
  await Deno.copyFile(entry.path, destPath);
  staticFileCount++;
}

console.log(`Copied ${staticFileCount} static files.`);

for await (const entry of walk(outDir, { includeDirs: false })) {
  const file = new StaticFile(entry.path, entry.path);
  for (const processer of processers) {
    if (await processer.needProcess(file)) {
      await file.setContent(await processer.process(file));
    }
  }
  await file.writeToDest();
}
console.log(
  `Transformed HTML: ${htmlProcesser.count}, CSS: ${cssProcesser.count}, JS: ${jsProcesser.count}`,
);

console.log(`Output in ${outDir}/`);
