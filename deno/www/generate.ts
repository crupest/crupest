import { toSSG } from "hono/ssg";
import { walk } from "@std/fs/walk";
import { basename, dirname, join, relative } from "@std/path";
import { transform as transformCss } from "lightningcss";
import { transform as transformJs } from "esbuild";
// @ts-types="npm:@types/html-minifier-terser"
import { minify as minifyHtml } from "html-minifier-terser";

import { createApp, STATIC_LIST, STATIC_ROOT } from "./app.ts";

class File {
  readonly #src: string;
  readonly #dest: string;
  #content: Uint8Array | null = null;
  #textContent: string | null = null;
  #contentCanGetFromSrc: boolean;

  constructor(
    src: string,
    dest: string,
    content: string | Uint8Array | null,
    contentCanGetFromSrc: boolean,
  ) {
    this.#src = src;
    this.#dest = dest;
    if (typeof content === "string") {
      this.#textContent = content;
    } else {
      this.#content = content;
    }
    this.#contentCanGetFromSrc = contentCanGetFromSrc;
  }

  get src(): string {
    return this.#src;
  }

  get dest(): string {
    return this.#dest;
  }

  async getContent(): Promise<Uint8Array> {
    if (this.#content == null) {
      if (this.#textContent != null) {
        const encoder = new TextEncoder();
        this.#content = encoder.encode(this.#textContent);
      } else if (this.#contentCanGetFromSrc) {
        this.#content = await Deno.readFile(this.#src);
      } else {
        throw new Error("Content is not available");
      }
    }
    return this.#content;
  }

  async getTextContent(): Promise<string> {
    if (this.#textContent == null) {
      if (this.#content != null) {
        const decoder = new TextDecoder();
        this.#textContent = decoder.decode(this.#content);
      } else if (this.#contentCanGetFromSrc) {
        this.#textContent = await Deno.readTextFile(this.#src);
      } else {
        throw new Error("Content is not available");
      }
    }
    return this.#textContent;
  }

  setContent(content: string | Uint8Array): Promise<void> {
    if (typeof content === "string") {
      this.#textContent = content;
      this.#content = null;
    } else {
      this.#content = content;
      this.#textContent = null;
    }
    return Promise.resolve();
  }

  async writeToDest(): Promise<void> {
    await Deno.mkdir(dirname(this.#dest), { recursive: true });
    if (this.#content != null) {
      await Deno.writeFile(this.#dest, this.#content);
    } else if (this.#textContent != null) {
      await Deno.writeTextFile(this.#dest, this.#textContent);
    } else if (this.#contentCanGetFromSrc && this.#src !== this.#dest) {
      await Deno.copyFile(this.#src, this.#dest);
    } else {
      throw new Error("Content is not available");
    }
  }
}

interface Processor {
  needProcess(file: File): Promise<boolean>;
  process(file: File): Promise<string | Uint8Array>;
}

class CssProcessor implements Processor {
  needProcess(file: File): Promise<boolean> {
    return Promise.resolve(file.src.endsWith(".css"));
  }

  async process(file: File): Promise<Uint8Array> {
    const { code } = transformCss({
      filename: basename(file.src),
      code: await file.getContent(),
      minify: true,
    });
    return code;
  }
}

class JsProcessor implements Processor {
  needProcess(file: File): Promise<boolean> {
    return Promise.resolve(file.src.endsWith(".js"));
  }

  async process(file: File): Promise<string> {
    const { code } = await transformJs(await file.getContent(), {
      minify: true,
      loader: "js",
    });
    return code;
  }
}

class HtmlProcessor implements Processor {
  needProcess(file: File): Promise<boolean> {
    return Promise.resolve(file.src.endsWith(".html"));
  }

  async process(file: File): Promise<string> {
    return await minifyHtml(await file.getTextContent(), {
      collapseWhitespace: true,
      removeComments: true,
      minifyCSS: true,
      minifyJS: true,
    });
  }
}

class CounterProcessorWrapper implements Processor {
  readonly #processor: Processor;
  #count = 0;

  constructor(processor: Processor) {
    this.#processor = processor;
  }

  get processor(): Processor {
    return this.#processor;
  }

  get count(): number {
    return this.#count;
  }

  needProcess(file: File): Promise<boolean> {
    return this.#processor.needProcess(file);
  }

  async process(file: File): Promise<string | Uint8Array> {
    this.#count++;
    return await this.#processor.process(file);
  }
}

const cssProcessor = new CounterProcessorWrapper(new CssProcessor());
const jsProcessor = new CounterProcessorWrapper(new JsProcessor());
const htmlProcessor = new CounterProcessorWrapper(new HtmlProcessor());

const processors: Processor[] = [cssProcessor, jsProcessor, htmlProcessor];

async function process(file: File): Promise<void> {
  for (const processor of processors) {
    if (await processor.needProcess(file)) {
      await file.setContent(await processor.process(file));
    }
  }
}

const outDir = "./dist";

if (await Deno.stat(outDir).catch(() => false)) {
  await Deno.remove(outDir, { recursive: true });
}

// Generate HTML pages via SSG
const app = await createApp();
const result = await toSSG(app, {
  writeFile: async (path: string, data: string | Uint8Array) => {
    const file = new File(path, path, data, false);
    await process(file);
    await file.writeToDest();
    console.log(`generated ${path}`);
  },
  mkdir: Deno.mkdir,
}, { dir: outDir });

if (!result.success) {
  console.error("SSG generation failed:", result.error);
  Deno.exit(1);
}

for await (const entry of walk(STATIC_ROOT, { includeDirs: false })) {
  const relativePath = relative(STATIC_ROOT, entry.path);
  const destPath = join(outDir, relativePath);
  const file = new File(entry.path, destPath, null, true);
  await process(file);
  await file.writeToDest();
  console.log(`processed ${relativePath}`);
}

console.log(
  `\nTransformed HTML: ${htmlProcessor.count}, CSS: ${cssProcessor.count}, JS: ${jsProcessor.count}`,
);

console.log(`Output in ${outDir}/`);
