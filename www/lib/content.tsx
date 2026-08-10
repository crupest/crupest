import { cache, ReactNode } from "react";
import runtime from "react/jsx-runtime";
import { stat } from "fs/promises";
import { join, dirname } from "path";
import { fileURLToPath } from "url";
import { z } from "zod";
import { VFile } from "vfile";
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
  source: { baseDir: string; path: string; content: string };
}

export interface ParsedArticle extends Article {
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

function remarkExtractPlainTextAndSummary() {
  return (tree: mdast.Root, file: VFile) => {
    const paragraphs: string[] = [];
    let summaryParagraphs: string[] | null = null;
    for (const node of tree.children) {
      if (node.type === "yaml") continue;
      if (node.type === "html" && /\s*<!--\s*more\s*-->\s*/.test(node.value)) {
        summaryParagraphs = paragraphs.slice();
        continue;
      }
      const paragraph = mdastToString(node).replaceAll("\n", " ");
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

async function loadArticle(
  sourceBaseDir: string,
  sourcePath: string,
  sourceContent: string,
): Promise<Article> {
  const fullPath = join(sourceBaseDir, sourcePath);

  const vfile = new VFile({
    path: fullPath,
    value: sourceContent,
  });
  matter(vfile);

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

  return {
    source: {
      baseDir: sourceBaseDir,
      path: sourcePath,
      content: sourceContent,
    },
    path,
    ...frontmatter,
  };
}

export async function parseArticle(article: Article): Promise<ParsedArticle> {
  const fullPath = join(article.source.baseDir, article.source.path);

  const vfile: VFile = await unified()
    .use(remarkParse)
    .use(remarkFrontmatter)
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
    .process(
      new VFile({
        path: fullPath,
        value: article.source.content,
      }),
    );

  const plainText = vfile.data.plainText as string;
  const summary = vfile.data.summary as string;
  const wordCount = countWords(plainText);
  const reactNode = vfile.result as ReactNode;

  return {
    ...article,
    plainText,
    wordCount,
    summary,
    reactNode,
  };
}

export async function parseArticles(
  articles: Article[],
): Promise<ParsedArticle[]> {
  return Promise.all(articles.map(parseArticle));
}

async function loadAndParseArticle(
  sourceBaseDir: string,
  sourcePath: string,
  sourceContent: string,
): Promise<ParsedArticle> {
  const article = await loadArticle(sourceBaseDir, sourcePath, sourceContent);
  return await parseArticle(article);
}

const kContentDir = "../content";
const moduleDirPath = dirname(fileURLToPath(import.meta.url));
const contentDirPath = join(moduleDirPath, kContentDir);

function scanArticleSources(): Record<
  string,
  () => Promise<{ default: string }>
> {
  const modules = import.meta.glob(`**/*.md`, { base: kContentDir }) as Record<
    string,
    () => Promise<{ default: string }>
  >;
  return Object.fromEntries(
    Object.entries(modules).map(([sourcePath, getSourceContent]) => [
      sourcePath.slice(kContentDir.length + 1),
      getSourceContent,
    ]),
  );
}

export async function getArticlePaths(): Promise<string[]> {
  const sourcePaths = Object.keys(scanArticleSources());
  return sourcePaths.map(sourcePathToPath);
}

export async function getArticles(options?: {
  postOnly?: boolean;
  sort?: boolean;
}): Promise<Article[]> {
  const articleSources = scanArticleSources();
  let articles: Article[] = await Promise.all(
    Object.entries(articleSources).map(
      async ([sourcePath, getSourceContent]) =>
        await loadArticle(
          contentDirPath,
          sourcePath,
          (await getSourceContent()).default,
        ),
    ),
  );
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

export async function getParsedArticle(
  path: string,
): Promise<ParsedArticle | null> {
  if (path.startsWith("/")) {
    path = path.slice(1);
  }
  const candidatePaths = [path + ".md", path + "/index.md"];
  for (const candidate of candidatePaths) {
    if (await fileExists(join(contentDirPath, candidate))) {
      const sourceContent = (await import(`${kContentDir}/${candidate}`))
        .default;
      return await loadAndParseArticle(
        contentDirPath,
        candidate,
        sourceContent,
      );
    }
  }
  return null;
}

export const cachedGetParsedArticle = cache(getParsedArticle);
