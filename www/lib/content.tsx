import { cache, ReactNode } from "react";
import runtime from "react/jsx-runtime";
import { stat, glob } from "fs/promises";
import { join, relative, dirname } from "path";
import { fileURLToPath } from "url";
import { z } from "zod";
import { type VFile } from "vfile";
import { read } from "to-vfile";
import { matter } from "vfile-matter";
import { unified } from "unified";
import remarkParse from "remark-parse";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import remarkFrontmatter from "remark-frontmatter";
import remarkRehype from "remark-rehype";
import rehypeKatex from "rehype-katex";
import rehypeStarryNight from "rehype-starry-night";
import rehypeRaw from "rehype-raw";
import rehypeReact from "rehype-react";
import type * as hast from "hast";
import type * as mdast from "mdast";
import { toString as mdastToString } from "mdast-util-to-string";
import { isElement } from "hast-util-is-element";

import CodeBlock from "@/components/markdown/CodeBlock";
import { visitParents } from "unist-util-visit-parents";

// --- Types ---

export const FRONTMATTER_SCHEMA = z.object({
  title: z.string(),
  date: z.coerce.date(),
  lastmod: z.coerce.date().optional(),
  description: z.string().optional(),
  categories: z.array(z.string()).optional(),
  tags: z.array(z.string()).optional(),
  css: z.array(z.string()).optional(),
});

export type ArticleFrontmatter = z.output<typeof FRONTMATTER_SCHEMA>;

export interface Article extends ArticleFrontmatter {
  path: string;
  sourcePath: string;
  plainText: string;
  wordCount: number;
  summary: string;
  reactNode: ReactNode;
}

// --- Helpers ---

function sourcePathToPath(path: string): string {
  path = path.replaceAll("\\", "/");
  if (!path.startsWith("/")) path = "/" + path;
  if (path.endsWith(".md")) path = path.slice(0, -".md".length);
  if (path.endsWith("/index")) path = path.slice(0, -"/index".length);
  return path + "/";
}

// TODO: Naive counting, no Asian character support, etc.
function countWords(text: string): number {
  return text.split(/\s+/).filter((w) => w.length > 0).length;
}

// --- Page parsing ---

function remarkExtractFrontmatter() {
  return function (_: mdast.Root, file: VFile) {
    matter(file);
  };
}

function remarkExtractPlainTextAndSummary() {
  return (tree: mdast.Root, file: VFile) => {
    const paragraphs: string[] = [];
    let summaryParagraphs: string[] | null = null;
    for (const node of tree.children) {
      if (node.type === "yaml") continue;
      const paragraph = mdastToString(node).replaceAll("\n", " ");
      if (paragraph === "<!--more-->") {
        summaryParagraphs = paragraphs.slice();
        continue;
      }
      paragraphs.push(paragraph);
    }
    file.data.plainText = paragraphs.join("\n");
    if (summaryParagraphs == null) {
      file.data.summary = paragraphs.slice(0, 3).join("\n").slice(0, 300);
    } else {
      file.data.summary = summaryParagraphs.join("\n");
    }
  };
}

function rehypeAddLanguageToPre() {
  return (tree: hast.Root) => {
    visitParents(
      tree,
      (node) => isElement(node, "code"),
      (node, ancestors) => {
        if (isElement(ancestors.at(-1), "pre") && node.properties.className) {
          for (const className of node.properties.className) {
            const prefix = "language-";
            if (className.startsWith(prefix)) {
              (ancestors.at(-1) as hast.Element).properties.dataLanguage =
                className.slice(prefix.length);
            }
          }
        }
      },
    );
  };
}

async function loadArticleFile(
  dir: string,
  sourcePath: string,
): Promise<Article> {
  const fullPath = join(dir, sourcePath);

  const vfile: VFile = await unified()
    .use(remarkParse)
    .use(remarkFrontmatter)
    .use(remarkExtractFrontmatter)
    .use(remarkGfm)
    .use(remarkMath)
    .use(remarkExtractPlainTextAndSummary)
    .use(remarkRehype, { allowDangerousHtml: true })
    .use(rehypeStarryNight)
    .use(rehypeAddLanguageToPre)
    .use(rehypeKatex, { strict: true, throwOnError: true })
    .use(rehypeRaw)
    .use(rehypeReact, {
      ...runtime,
      components: {
        pre: CodeBlock,
      },
    })
    .process(await read(fullPath));

  const frontmatterParseResult = FRONTMATTER_SCHEMA.safeParse(
    vfile.data.matter,
  );
  if (!frontmatterParseResult.success) {
    throw new Error(
      `Invalid frontmatter in ${fullPath}: ${frontmatterParseResult.error}`,
    );
  }
  const frontmatter = frontmatterParseResult.data;

  const path = sourcePathToPath(sourcePath);
  const plainText = vfile.data.plainText as string;
  const summary = vfile.data.summary as string;
  const wordCount = countWords(plainText);
  const reactNode = vfile.result as ReactNode;

  return {
    sourcePath,
    path,
    ...frontmatter,
    plainText,
    wordCount,
    summary,
    reactNode,
  };
}

export function getDefaultContentPath(): string {
  const filename = fileURLToPath(import.meta.url);
  return join(dirname(filename), "..", "content");
}

async function getArticleSourcePaths(dir?: string): Promise<string[]> {
  dir ??= getDefaultContentPath();
  const paths: string[] = [];
  for await (const path of glob(join(dir, "**/*.md"))) {
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
    if (err instanceof Error && "code" in err && err.code === "ENOENT") {
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
  const candidatePaths = [path + ".md", join(path, "index.md")];
  for (const candidate of candidatePaths) {
    if (await fileExists(join(dir, candidate))) {
      return await loadArticleFile(dir, candidate);
    }
  }
  return null;
}

export const cachedGetArticle = cache(getArticle);
