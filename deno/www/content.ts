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
  date?: Date | string;
  lastmod?: Date | string;
  description?: string;
  categories?: string;
  tags?: string[];
  layout?: string;
  params?: { css?: string[] };
}

export interface Page {
  slug: string;
  title: string;
  date?: Date;
  lastmod?: Date;
  description?: string;
  categories?: string;
  tags?: string[];
  layout?: string;
  extraCss?: string[];
  content: string;
  plainText: string;
  wordCount: number;
  summary: string;
}

export interface SiteContent {
  pages: Map<string, Page>;
  posts: Page[];
}

// --- Helpers ---

function toDate(value: Date | string | undefined): Date | undefined {
  if (value == null) return undefined;
  return value instanceof Date ? value : new Date(value);
}

function countWords(text: string): number {
  return text.split(/\s+/).filter((w) => w.length > 0).length;
}

function filePathToSlug(filePath: string): string {
  let slug = filePath.replace(/\\/g, "/");
  if (slug === "_index.md") return "/";
  if (slug.endsWith("/_index.md")) {
    slug = slug.slice(0, -"/_index.md".length);
  } else if (slug.endsWith(".md")) {
    slug = slug.slice(0, -".md".length);
  }
  return `/${slug}/`;
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

async function parsePage(
  relPath: string,
  contentDir: string,
): Promise<Page> {
  const fullPath = `${contentDir}/${relPath}`;
  const raw = await Deno.readTextFile(fullPath);

  const { attrs, body } = extract<Frontmatter>(raw);

  const content = await marked.parse(body, { async: true });

  const plainText = new JSDOM(content).window.document.body
    .textContent as string;
  const wordCount = countWords(plainText);
  const summary = extractSummary(plainText);
  const slug = filePathToSlug(relPath);

  return {
    slug,
    title: attrs.title,
    date: toDate(attrs.date),
    lastmod: toDate(attrs.lastmod),
    description: attrs.description,
    categories: attrs.categories,
    tags: attrs.tags,
    layout: attrs.layout,
    extraCss: attrs.params?.css,
    content,
    plainText,
    wordCount,
    summary,
  };
}

// --- Main export ---

export async function loadContent(
  contentDir?: string,
): Promise<SiteContent> {
  const dir = contentDir ??
    fromFileUrl(new URL("./content", import.meta.url));

  const pages = new Map<string, Page>();
  const posts: Page[] = [];

  for await (
    const entry of walk(dir, {
      exts: [".md"],
      includeDirs: false,
    })
  ) {
    const relPath = relative(dir, entry.path);
    const page = await parsePage(relPath, dir);
    pages.set(page.slug, page);

    const normalized = relPath.replace(/\\/g, "/");
    if (
      normalized.startsWith("posts/") &&
      !normalized.endsWith("_index.md")
    ) {
      posts.push(page);
    }
  }

  // Sort posts by date descending
  posts.sort((a, b) => {
    const dateA = a.date?.getTime() ?? 0;
    const dateB = b.date?.getTime() ?? 0;
    return dateB - dateA;
  });

  return { pages, posts };
}
