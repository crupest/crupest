import { extract } from "@std/front-matter/yaml";
import { walk } from "@std/fs/walk";
import { join, relative } from "@std/path";
import { Marked } from "marked";
import { codeToHtml } from "shiki/bundle/full";
// @ts-types="npm:@types/jsdom"
import { JSDOM } from "jsdom";
import * as z from "zod";

import { html } from "@crupest/base-contrib/html";

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

const clipboardSvg = html.raw(
  `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-clipboard" viewBox="0 0 16 16">
  <path d="M4 1.5H3a2 2 0 0 0-2 2V14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V3.5a2 2 0 0 0-2-2h-1v1h1a1 1 0 0 1 1 1V14a1 1 0 0 1-1 1H3a1 1 0 0 1-1-1V3.5a1 1 0 0 1 1-1h1z"/>
  <path d="M9.5 1a.5.5 0 0 1 .5.5v1a.5.5 0 0 1-.5.5h-3a.5.5 0 0 1-.5-.5v-1a.5.5 0 0 1 .5-.5zm-3-1A1.5 1.5 0 0 0 5 1.5v1A1.5 1.5 0 0 0 6.5 4h3A1.5 1.5 0 0 0 11 2.5v-1A1.5 1.5 0 0 0 9.5 0z"/>
</svg>`,
);

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
  let codeBlockCount = 1;
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
          token.text = html`
            <div id="code-block-${codeBlockCount}" class="code-block">
              <div><span>${token.lang ??
                "plain"}</span><span class="copy-button" onclick="copyCodeBlock(${codeBlockCount})">${clipboardSvg}</span></div>
              ${html.raw(token.text)}
            </div>
          `.toEscapedString();
          codeBlockCount++;
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
