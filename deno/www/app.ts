import { Hono } from "hono";
import { serveStatic } from "hono/deno";
import { fromFileUrl } from "@std/path";

import { loadContent } from "./content.ts";
import type { Site } from "./content.ts";
import { homePage, listPage, singlePage } from "./templates.ts";

const STATIC_LIST = [
  "/favicon.ico",
  "/robots.txt",
  "/assets/",
  "/magic/",
];
export const STATIC_ROOT = fromFileUrl(new URL("./static", import.meta.url));

export async function createApp(): Promise<Hono> {
  const app = new Hono();
  const site = await loadContent();

  for (const prefix of STATIC_LIST) {
    app.get(
      prefix.endsWith("/") ? `${prefix}*` : prefix,
      serveStatic({ root: STATIC_ROOT }),
    );
  }

  // Home page
  app.get("/", (c) => {
    return c.html(homePage(site));
  });

  app.get("/posts/", (c) => {
    return c.html(listPage({
      slug: "/posts/",
      title: "Posts",
      articles: site.posts,
      site,
    }));
  });

  // Register routes for all pages
  registerPageRoutes(app, site);

  return app;
}

function registerPageRoutes(app: Hono, site: Site): void {
  for (const [slug, article] of site.articles) {
    app.get(slug, (c) => {
      return c.html(singlePage(article, site));
    });

    if (slug.endsWith("/") && slug !== "/") {
      app.get(slug.slice(0, -1), (c) => c.redirect(slug, 301));
    }
  }
}
