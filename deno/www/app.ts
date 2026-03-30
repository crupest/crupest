import { Hono } from "hono";
import { serveStatic } from "hono/deno";
import { basename, fromFileUrl, join } from "@std/path";
import { transform } from "lightningcss";

import { loadContent } from "./content.ts";
import type { Page, SiteContent } from "./content.ts";
import { homePage, listPage, singlePage } from "./templates.ts";

export async function createApp(): Promise<Hono> {
  const app = new Hono();
  const site = await loadContent();

  // Serve static files (avatar.png, favicon.ico, gh.png, magic/, color-scheme.js)
  const staticDir = fromFileUrl(new URL("./static", import.meta.url));
  app.get("/favicon.ico", serveStatic({ root: staticDir }));
  app.get("/assets/*.css", async (c) => {
    const path = join(staticDir, c.req.path);
    try {
      if (!(await Deno.stat(path)).isFile) {
        return c.text("Not found", 404);
      }
    } catch (e) {
      if (e instanceof Deno.errors.NotFound) {
        return c.text("Not found", 404);
      }
      throw e;
    }

    const { code } = transform({
      filename: basename(path),
      code: await Deno.readFile(path),
      minify: true,
    });
    return c.body(code as Uint8Array<ArrayBuffer>, {
      headers: {
        "Content-Type": "text/css",
      },
    });
  });
  app.get("/assets/*", serveStatic({ root: staticDir }));
  app.get("/magic/*", serveStatic({ root: staticDir }));

  // robots.txt
  app.get("/robots.txt", (c) => {
    return c.text("User-agent: *\nDisallow: /git/\n");
  });

  // Home page
  app.get("/", (c) => {
    return c.html(homePage(site.posts));
  });

  // Register routes for all pages
  registerPageRoutes(app, site);

  return app;
}

function registerPageRoutes(app: Hono, site: SiteContent): void {
  for (const [slug, page] of site.pages) {
    if (slug === "/") continue; // Home already handled

    // Determine layout
    const isListPage = slug === "/posts/" ||
      (slug.endsWith("/") && !page.layout && hasChildPages(slug, site));

    // Register with trailing slash
    app.get(slug, (c) => {
      if (isListPage) {
        const children = getChildPages(slug, site);
        return c.html(listPage(page, children, site.pages));
      }
      // Single page (or pages with layout: single like notes index)
      return c.html(singlePage(page, site.pages));
    });

    // Redirect non-trailing-slash to trailing slash for non-root paths
    if (slug.endsWith("/") && slug !== "/") {
      const noSlash = slug.slice(0, -1);
      app.get(noSlash, (c) => c.redirect(slug, 301));
    }
  }
}

function hasChildPages(slug: string, site: SiteContent): boolean {
  for (const [otherSlug, otherPage] of site.pages) {
    if (
      otherSlug !== slug && otherSlug.startsWith(slug) &&
      !otherSlug.slice(slug.length).includes("/")
    ) {
      if (otherPage.date) return true;
    }
  }
  return false;
}

function getChildPages(slug: string, site: SiteContent): Page[] {
  const children: Page[] = [];
  for (const [otherSlug, page] of site.pages) {
    // Direct children only (not nested deeper), exclude _index pages
    if (otherSlug !== slug && otherSlug.startsWith(slug)) {
      const rest = otherSlug.slice(slug.length);
      // Direct child: no additional "/" in the remaining path (except trailing)
      const parts = rest.split("/").filter(Boolean);
      if (parts.length === 1) {
        children.push(page);
      }
    }
  }
  // Sort by date descending
  children.sort((a, b) => {
    const dateA = a.date?.getTime() ?? 0;
    const dateB = b.date?.getTime() ?? 0;
    return dateB - dateA;
  });
  return children;
}
