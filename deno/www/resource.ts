import { walk } from "@std/fs/walk";
import { basename, dirname, join, relative } from "@std/path";
import { contentType } from "@std/media-types";
import { transform as transformCss } from "lightningcss";
import { transform as transformJs } from "esbuild";
// @ts-types="npm:@types/html-minifier-terser"
import { minify as transformHtml } from "html-minifier-terser";

function appendLine(content: string, line: string): string {
  return `${content}${content.endsWith("\n") ? "" : "\n"}${line}${
    line.endsWith("\n") ? "" : "\n"
  }`;
}

export type ResourceSource = { type: "file"; path: string } | {
  type: "data";
  data: string | Uint8Array;
};

export type ResourceOutput = {
  path: string;
  content: Uint8Array;
  mimeType: string;
};

export class Resource {
  #source: ResourceSource;
  #path: string | null;
  #outputPath: string;
  #content: Uint8Array | null = null;
  #textContent: string | null = null;
  #additionalOutputs: ResourceOutput[] = [];

  constructor({
    source,
    path,
    outputPath,
  }: {
    source: ResourceSource;
    path?: string | null;
    outputPath: string;
  }) {
    this.#source = source;
    this.#path = path ?? null;
    this.#outputPath = outputPath;
  }

  get source(): ResourceSource {
    return this.#source;
  }

  get path(): string | null {
    return this.#path;
  }

  get outputPath(): string {
    return this.#outputPath;
  }

  set outputPath(value: string) {
    this.#outputPath = value;
  }

  get mimeType(): string {
    const fallback = "application/octet-stream";
    const index = this.#outputPath.lastIndexOf(".");
    if (index === -1) return fallback;
    return contentType(this.#outputPath.slice(index)) ?? fallback;
  }

  get additionalOutputs(): ResourceOutput[] {
    return this.#additionalOutputs;
  }

  async getContent(): Promise<Uint8Array> {
    if (this.#content == null) {
      if (this.#source.type === "data") {
        if (typeof this.#source.data === "string") {
          const encoder = new TextEncoder();
          this.#content = encoder.encode(this.#source.data);
        } else {
          this.#content = this.#source.data;
        }
      } else {
        this.#content = await Deno.readFile(this.#source.path);
      }
    }
    return this.#content;
  }

  async getTextContent(): Promise<string> {
    if (this.#textContent == null) {
      const content = await this.getContent();
      this.#textContent = new TextDecoder().decode(content);
    }
    return this.#textContent;
  }

  setContent(
    content: string | Uint8Array,
    options?: { appendLine?: string },
  ): Promise<void> {
    if (typeof content === "string") {
      if (options?.appendLine) {
        content = appendLine(content, options.appendLine);
      }
      this.#textContent = content;
      this.#content = new TextEncoder().encode(content);
    } else {
      if (options?.appendLine) {
        this.#textContent = appendLine(
          new TextDecoder().decode(content),
          options.appendLine,
        );
        this.#content = new TextEncoder().encode(this.#textContent);
      } else {
        this.#content = content;
        this.#textContent = null;
      }
    }
    return Promise.resolve();
  }

  addAdditionalOutput(
    path: string,
    content: string | Uint8Array,
    mimeType: string,
  ): Promise<void> {
    if (typeof content === "string") {
      content = new TextEncoder().encode(content);
    }
    this.#additionalOutputs.push({ path, content, mimeType });
    return Promise.resolve();
  }

  addSourceMap(
    mapContent: string | Uint8Array,
    mimeType: string = "application/json",
  ): Promise<void> {
    this.addAdditionalOutput(this.outputPath + ".map", mapContent, mimeType);
    return Promise.resolve();
  }

  async writeContent(root: string | null): Promise<void> {
    const fullPath = root ? join(root, this.#outputPath) : this.#outputPath;
    await Deno.mkdir(dirname(fullPath), { recursive: true });
    await Deno.writeFile(fullPath, await this.getContent());
  }

  async writeAllOutputFiles(root: string | null): Promise<void> {
    await this.writeContent(root);
    for (const output of this.#additionalOutputs) {
      const fullPath = root ? join(root, output.path) : output.path;
      await Deno.mkdir(dirname(fullPath), { recursive: true });
      await Deno.writeFile(fullPath, output.content);
    }
  }
}

export interface ResourceTransformer {
  transform(resource: Resource): Promise<void>;
}

export class CssTransformer implements ResourceTransformer {
  async transform(resource: Resource): Promise<void> {
    if (!resource.outputPath.endsWith(".css")) return;
    const filename = basename(resource.outputPath);
    const { code, map } = transformCss({
      filename,
      code: await resource.getContent(),
      minify: true,
      sourceMap: true,
    });

    if (map) {
      await resource.setContent(
        code,
        {
          appendLine: `/*# sourceMappingURL=${filename}.map */`,
        },
      );
      await resource.addSourceMap(map);
    } else {
      await resource.setContent(code);
    }
  }
}

export class JsTransformer implements ResourceTransformer {
  async transform(resource: Resource): Promise<void> {
    if (!resource.outputPath.endsWith(".js")) return;
    const filename = basename(resource.outputPath);
    const { code, map } = await transformJs(await resource.getContent(), {
      sourcefile: filename,
      minify: true,
      loader: "js",
      sourcemap: "external",
    });
    await resource.setContent(
      code,
      {
        appendLine: `//# sourceMappingURL=${filename}.map`,
      },
    );
    await resource.addSourceMap(map);
  }
}

export class TsTransformer implements ResourceTransformer {
  async transform(resource: Resource): Promise<void> {
    if (!resource.outputPath.endsWith(".ts")) return;
    const filename = basename(resource.outputPath);
    resource.outputPath = resource.outputPath.replace(/\.ts$/, ".js");
    const { code, map } = await transformJs(await resource.getContent(), {
      sourcefile: filename,
      minify: true,
      loader: "ts",
      sourcemap: "external",
    });
    await resource.setContent(
      code,
      {
        appendLine: `//# sourceMappingURL=${basename(resource.outputPath)}.map`,
      },
    );
    if (map) {
      await resource.addSourceMap(map);
    }
  }
}

export class HtmlTransformer implements ResourceTransformer {
  async transform(resource: Resource): Promise<void> {
    if (!resource.outputPath.endsWith(".html")) return;
    const minified = await transformHtml(await resource.getTextContent(), {
      collapseWhitespace: true,
      removeComments: true,
      minifyCSS: true,
      minifyJS: true,
    });
    await resource.setContent(minified);
  }
}

export class AppResourceTransformer implements ResourceTransformer {
  readonly #transformers: ResourceTransformer[] = [
    new CssTransformer(),
    new JsTransformer(),
    new TsTransformer(),
    new HtmlTransformer(),
  ];

  async transform(resource: Resource): Promise<void> {
    for (const transformer of this.#transformers) {
      await transformer.transform(resource);
    }
  }
}

export async function scanResources(dir: string): Promise<Resource[]> {
  const resources: Resource[] = [];
  for await (const entry of walk(dir, { includeDirs: false })) {
    const relativePath = "/" + relative(dir, entry.path).replaceAll("\\", "/");
    const resource = new Resource({
      source: { type: "file", path: entry.path },
      path: relativePath,
      outputPath: relativePath,
    });
    resources.push(resource);
  }
  return resources;
}
