import { cache } from "react";
import * as runtime from "react/jsx-runtime";
import { stat, readFile, glob } from "fs/promises";
import { join, relative, dirname } from "path";
import { fileURLToPath, pathToFileURL } from "url";
import { z } from "zod";
import { parse } from "node-html-parser";
import type { MDXContent } from "mdx/types";
import { evaluate } from "@mdx-js/mdx";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
import rehypeStarryNight from "rehype-starry-night";

// --- Types ---

export const METADATA_SCHEMA = z.object({
  title: z.string(),
  date: z.coerce.date(),
  lastmod: z.coerce.date().optional(),
  description: z.string().optional(),
  categories: z.array(z.string()).optional(),
  tags: z.array(z.string()).optional(),
  css: z.array(z.string()).optional(),
});

export type Metadata = z.output<typeof METADATA_SCHEMA>;

export interface Article {
  path: string;
  sourcePath: string;
  title: string;
  date: Date;
  lastmod?: Date;
  description?: string;
  categories?: string[];
  tags?: string[];
  css?: string[];
  plainText: string;
  wordCount: number;
  summary: string;
  component: MDXContent;
}

// --- Helpers ---

function sourcePathToPath(path: string): string {
  path = path.replaceAll("\\", "/");
  if (!path.startsWith("/")) path = "/" + path;
  if (path.endsWith(".md")) path = path.slice(0, -".md".length);
  if (path.endsWith(".mdx")) path = path.slice(0, -".mdx".length);
  if (path.endsWith("/index")) path = path.slice(0, -"/index".length);
  return path + "/";
}

// TODO: Naive counting, no Asian character support, etc.
function countWords(text: string): number {
  return text.split(/\s+/).filter((w) => w.length > 0).length;
}

function extractSummary(plainText: string): string {
  return plainText
    .split("\n")
    .filter((l) => l.trim().length > 0)
    .slice(0, 5)
    .join("\n")
    .slice(0, 300);
}

// --- Page parsing ---

async function loadArticleFile(
  dir: string,
  sourcePath: string,
): Promise<Article> {
  const fullPath = join(dir, sourcePath);
  const fileContent = await readFile(fullPath, { encoding: "utf-8" });
  const mdxModule = await evaluate(fileContent, {
    ...runtime,
    baseUrl: pathToFileURL(fullPath),
    remarkPlugins: [remarkGfm, remarkMath],
    rehypePlugins: [
      [rehypeKatex, { strict: true, throwOnError: true }],
      rehypeStarryNight,
    ],
  });
  const { default: Component, metadata: rawMetadata } = mdxModule;

  const metadataParseResult = METADATA_SCHEMA.safeParse(rawMetadata);
  if (!metadataParseResult.success) {
    throw new Error(
      `Invalid metadata in ${fullPath}: ${metadataParseResult.error}`,
    );
  }
  const metadata = metadataParseResult.data;

  const path = sourcePathToPath(sourcePath);

  const ReactDOMServer = (await import("react-dom/server")).default;
  const html = ReactDOMServer.renderToStaticMarkup(<Component />);
  const plainText = parse(html).textContent;
  const wordCount = countWords(plainText);
  const summary = extractSummary(plainText);

  return {
    sourcePath,
    path,
    ...metadata,
    plainText,
    wordCount,
    summary,
    component: Component,
  };
}

export function getDefaultContentPath(): string {
  const filename = fileURLToPath(import.meta.url);
  return join(dirname(filename), "..", "content");
}

async function getArticleSourcePaths(dir?: string): Promise<string[]> {
  dir ??= getDefaultContentPath();
  const paths: string[] = [];
  for await (const path of glob(join(dir, "**/*.mdx"))) {
    paths.push(relative(dir, path));
  }
  return paths;
}

export async function getArticlePaths(dir?: string): Promise<string[]> {
  const sourcePaths = await getArticleSourcePaths(dir);
  return sourcePaths.map((sourcePath) => sourcePathToPath(sourcePath));
}

export async function getArticles(options?: {
  dir?: string;
  postOnly?: boolean;
  sort?: boolean;
}): Promise<Article[]> {
  const dir = options?.dir ?? getDefaultContentPath();
  let articles: Article[] = [];
  for (const sourcePath of await getArticleSourcePaths(dir)) {
    const article = await loadArticleFile(dir, sourcePath);
    articles.push(article);
  }
  if (options?.postOnly === true) {
    articles = articles.filter((a) => a.path.startsWith("/posts"));
  }
  if (options?.sort === true) {
    articles.sort((a, b) => b.date.getTime() - a.date.getTime());
  }
  return articles;
}

async function fileExists(filePath: string): Promise<boolean> {
  try {
    const s = await stat(filePath);
    return s.isFile();
  } catch (err) {
    if (
      err instanceof Error &&
      (err as NodeJS.ErrnoException).code === "ENOENT"
    ) {
      return false;
    }
    throw err;
  }
}

export async function getArticle(
  dir: string | undefined,
  path: string,
): Promise<Article | null> {
  dir ??= getDefaultContentPath();
  if (path.startsWith("/")) {
    path = path.slice(1);
  }
  const candidatePaths = [path + ".mdx", join(path, "index.mdx")];
  for (const candidate of candidatePaths) {
    if (await fileExists(join(dir, candidate))) {
      return await loadArticleFile(dir, candidate);
    }
  }
  return null;
}

export const cachedGetArticle = cache(getArticle);
