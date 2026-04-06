import { extract } from "@std/front-matter/yaml";
import { walk } from "@std/fs/walk";
import { fromFileUrl, relative } from "@std/path";
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
  slug: string;
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

export interface Site {
  articles: Map<string, Article>;
  posts: Article[];
}

// --- Helpers ---

function countWords(text: string): number {
  return text.split(/\s+/).filter((w) => w.length > 0).length;
}

function filePathToSlug(filePath: string): string {
  let slug = filePath.replaceAll("\\", "/");
  if (slug.endsWith(".md")) slug = slug.slice(0, -".md".length);
  if (slug.endsWith("/index")) slug = slug.slice(0, -"/index".length);
  return slug.length === 0 ? "/" : `/${slug}/`;
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

async function parseArticle(
  relPath: string,
  contentDir: string,
): Promise<Article> {
  const fullPath = `${contentDir}/${relPath}`;
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

  const slug = filePathToSlug(relPath);
  const renderedHtml = await marked.parse(body, { async: true });
  const plainText = new JSDOM(renderedHtml).window.document.body
    .textContent;
  const wordCount = countWords(plainText);
  const summary = extractSummary(renderedHtml, plainText);

  return {
    slug,
    ...frontmatter,
    renderedHtml,
    plainText,
    wordCount,
    summary,
  };
}

// --- Main export ---

export async function loadContent(
  contentDir?: string,
): Promise<Site> {
  const dir = contentDir ??
    fromFileUrl(new URL("./content", import.meta.url));

  const articles: Map<string, Article> = new Map();

  for await (
    const entry of walk(dir, {
      exts: [".md"],
      includeDirs: false,
    })
  ) {
    const article = await parseArticle(relative(dir, entry.path), dir);
    articles.set(article.slug, article);
  }

  // Sort posts by date descending
  const posts = Array.from(articles.values()).filter((p) =>
    p.slug !== "/posts/" && p.slug.startsWith("/posts/")
  ).sort((a, b) => b.date.getTime() - a.date.getTime());

  return { articles, posts };
}
