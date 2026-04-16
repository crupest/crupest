import { extract } from "@std/front-matter/yaml";
import { walk } from "@std/fs/walk";
import { join, relative } from "@std/path";
import { Marked } from "marked";
import { codeToHtml } from "shiki/bundle/full";
// @ts-types="npm:@types/jsdom"
import { JSDOM } from "jsdom";
import * as z from "zod";

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

export type Frontmatter = z.output<typeof FRONTMATTER_SCHEMA>;

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
  renderedHtml: string;
  plainText: string;
  wordCount: number;
  summary: string;
}

// --- Helpers ---

// TODO: Naive counting, no Asian character support, etc.
function countWords(text: string): number {
  return text.split(/\s+/).filter((w) => w.length > 0).length;
}

function sourcePathToPath(path: string): string {
  if (path.endsWith(".md")) path = path.slice(0, -".md".length);
  if (path.endsWith("/index")) path = path.slice(0, -"/index".length);
  return path + "/";
}

// --- Marked instance ---

const marked = new Marked(
  {
    async: true,
    walkTokens: async (token) => {
      if (token.type === "code") {
        token.text = await codeToHtml(token.text, {
          lang: token.lang,
          themes: {
            light: "vitesse-light",
            dark: "vitesse-dark",
          },
        });
      }
    },
    gfm: true,
    renderer: {
      code(token) {
        return token.text;
      },
    },
  },
);

// --- Summary extraction ---

function extractSummary(renderedHtml: string, plainText: string): string {
  const moreIndex = renderedHtml.indexOf("<!--more-->");
  if (moreIndex !== -1) {
    const preMoreHtml = renderedHtml.slice(0, moreIndex);
    return new JSDOM(preMoreHtml).window.document.body.textContent.trim();
  }

  return plainText
    .split("\n")
    .filter((l) => l.trim().length > 0)
    .slice(0, 5)
    .join("\n")
    .slice(0, 300);
}

// --- Page parsing ---

async function loadArticle(dir: string, sourcePath: string): Promise<Article> {
  const fullPath = join(dir, sourcePath);
  const raw = await Deno.readTextFile(fullPath);

  const { attrs: rawFrontmatter, body } = extract<
    z.input<typeof FRONTMATTER_SCHEMA>
  >(raw);
  const frontmatterParseResult = FRONTMATTER_SCHEMA.safeParse(rawFrontmatter);
  if (!frontmatterParseResult.success) {
    throw new Error(
      `Invalid frontmatter in ${fullPath}: ${frontmatterParseResult.error}`,
    );
  }
  const frontmatter = frontmatterParseResult.data;

  const path = sourcePathToPath(sourcePath);
  const renderedHtml = await marked.parse(body, { async: true });
  const plainText = new JSDOM(renderedHtml).window.document.body
    .textContent;
  const wordCount = countWords(plainText);
  const summary = extractSummary(renderedHtml, plainText);

  return {
    sourcePath,
    path,
    ...frontmatter,
    renderedHtml,
    plainText,
    wordCount,
    summary,
  };
}

export async function loadArticles(dir: string): Promise<Article[]> {
  const articles: Article[] = [];
  for await (const entry of walk(dir, { exts: [".md"], includeDirs: false })) {
    const article = await loadArticle(
      dir,
      "/" + relative(dir, entry.path).replaceAll("\\", "/"),
    );
    articles.push(article);
  }
  return articles;
}
