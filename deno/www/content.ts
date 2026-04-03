import { extract } from "@std/front-matter/yaml";
import { walk } from "@std/fs/walk";
import { fromFileUrl, relative } from "@std/path";
import { Marked } from "marked";
import { markedHighlight } from "marked-highlight";
import { codeToHtml } from "shiki/bundle/full";
import { JSDOM } from "jsdom";

// --- Types ---

export interface Frontmatter {
  title: string;
  date: string;
  lastmod?: string;
  description?: string;
  categories?: string;
  tags?: string[];
  params?: { css?: string[] };
}

export interface Article {
  slug: string;
  title: string;
  date: Date;
  lastmod?: Date;
  description?: string;
  categories?: string;
  tags?: string[];
  extraCss?: string[];
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

function toDate(value: string | undefined): Date | undefined {
  return value != null ? new Date(value) : undefined;
}

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
  markedHighlight({
    async: true,
    langPrefix: "code-block language-",
    highlight(code, lang) {
      return codeToHtml(code, {
        lang,
        themes: {
          light: "vitesse-light",
          dark: "vitesse-dark",
        },
      });
    },
  }),
  { gfm: true },
);

// --- Summary extraction ---

function extractSummary(plaintext: string): string {
  const moreIndex = plaintext.indexOf("<!--more-->");
  if (moreIndex !== -1) {
    return plaintext.slice(0, moreIndex).trim();
  }

  return plaintext
    .split("\n")
    .filter((l) => l.trim().length > 0)
    .slice(0, 5)
    .join(" ");
}

// --- Page parsing ---

async function parseArticle(
  relPath: string,
  contentDir: string,
): Promise<Article> {
  const fullPath = `${contentDir}/${relPath}`;
  const raw = await Deno.readTextFile(fullPath);

  const { attrs, body } = extract<Frontmatter>(raw);

  const slug = filePathToSlug(relPath);
  const renderedHtml = await marked.parse(body, { async: true });
  const plainText = new JSDOM(renderedHtml).window.document.body
    .textContent as string;
  const wordCount = countWords(plainText);
  const summary = extractSummary(plainText);

  return {
    slug,
    title: attrs.title,
    date: new Date(attrs.date),
    lastmod: toDate(attrs.lastmod),
    description: attrs.description,
    categories: attrs.categories,
    tags: attrs.tags,
    extraCss: attrs.params?.css,
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
