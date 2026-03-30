import type { HtmlEscapedString } from "hono/utils/html";
import { html, raw } from "hono/html";
import type { Page } from "./content.ts";

type Html = HtmlEscapedString | Promise<HtmlEscapedString>;

// --- Date formatting ---

function formatDate(date: Date): string {
  return date.toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

function formatDateISO(date: Date): string {
  return date.toISOString();
}

function dateHtml(date: Date): Html {
  return html`
    <time datetime="${formatDateISO(date)}">${formatDate(date)}</time>
  `;
}

// --- Navigation breadcrumb ---

interface BreadcrumbItem {
  title: string;
  href: string;
}

function buildBreadcrumbs(
  slug: string,
  pages: Map<string, Page>,
): BreadcrumbItem[] {
  const parts = slug.split("/").filter(Boolean);
  const crumbs: BreadcrumbItem[] = [{ title: "home", href: "/" }];

  for (let i = 0; i < parts.length; i++) {
    const path = "/" + parts.slice(0, i + 1).join("/") + "/";
    const page = pages.get(path);
    if (page) {
      crumbs.push({ title: page.title.toLowerCase(), href: path });
    }
  }

  return crumbs;
}

function navHtml(slug: string, pages: Map<string, Page>): Html {
  const crumbs = buildBreadcrumbs(slug, pages);
  // Don't show nav if we're on home
  if (crumbs.length <= 1) {
    return html`

    `;
  }

  const links = crumbs.slice(0, -1).map(
    (c) =>
      html`
        <a class="mono-link" href="${c.href}">${c.title}</a> &gt;
      `,
  );
  return html`
    <nav class="mono">${links}this</nav>
  `;
}

// --- Article preview ---

function articlePreviewHtml(
  page: Page,
  headingTag: string,
): Html {
  const lines = page.plainText
    .split("\n")
    .filter((l) => l.trim().length > 0)
    .slice(0, 5);
  const preview = lines.map((l) =>
    html`
      ${l}<br />
    `
  );

  return html`
    <section class="article-preview">
      <span class="date">${page.date ? formatDate(page.date) : ""}</span>
      ${raw(
        `<${headingTag} class="title"><a href="${page.slug}">${page.title}</a></${headingTag}>`,
      )}
      <p class="content">${preview}</p>
      <p>... <a class="mono-link" href="${page.slug}">Read more</a></p>
    </section>
  `;
}

function postsPreviewHtml(
  posts: Page[],
  headingTag: string,
): Html {
  if (posts.length === 0) {
    return html`

    `;
  }

  const items = posts.map((page, i) => {
    const sep = i > 0
      ? html`
        <hr class="article-preview-hr">
      `
      : html`

      `;
    return html`
      ${sep}${articlePreviewHtml(page, headingTag)}
    `;
  });

  return html`
    ${items}
  `;
}

// --- Base layout ---

interface LayoutOptions {
  title?: string;
  extraCss?: string[];
  extraHead?: Html;
  content: Html;
  footer?: Html;
}

export function baseLayout(options: LayoutOptions): Html {
  const title = options.title ?? "crupest's life";

  const cssLinks = (options.extraCss ?? []).map(
    (css) =>
      html`
        <link rel="stylesheet" href="/assets/${css}.css" />
      `,
  );

  return html`
    <!DOCTYPE html>
    <html>
      <head>
        <meta charset="utf-8">
        <meta http-equiv="X-UA-Compatible" content="IE=edge">
        <link rel="icon" href="/favicon.ico" />
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />
        <title>${title}</title>
        <script src="/assets/color-scheme.js"></script>
        <link rel="stylesheet" href="/assets/base.css" />
        ${cssLinks} ${options.extraHead ?? html`

        `}
      </head>
      <body>
        <article id="main-article">
          ${options.content}
          <hr />
          <footer class="mono-link">
            ${options.footer ?? html`

            `}
            <p id="license">
              <small>This work is licensed under
                <a
                  rel="license noopener noreferrer"
                  href="https://creativecommons.org/licenses/by-nc/4.0/"
                  target="_blank"
                >
                  <span id="license-text">CC BY-NC 4.0</span>
                  <span id="license-img-container">
                    <img
                      src="https://mirrors.creativecommons.org/presskit/icons/cc.svg"
                    />
                    <img
                      src="https://mirrors.creativecommons.org/presskit/icons/by.svg"
                    />
                    <img
                      src="https://mirrors.creativecommons.org/presskit/icons/nc.svg"
                    />
                  </span>
                </a>
              </small>
            </p>
          </footer>
        </article>
      </body>
    </html>
  `;
}

// --- Page-specific layouts ---

export function homePage(
  posts: Page[],
): Html {
  const recentPosts = posts.slice(0, 3);

  return baseLayout({
    extraCss: ["home", "article"],
    content: html`
      <img
        id="avatar"
        src="/assets/avatar.png"
        alt="My avatar"
        width="80"
        height="80"
      />
      <h1 id="title">Hello! This is <code>crupest</code> !</h1>
      <hr />
      <section>
        <p>Welcome to my home page! Nice to meet you here! 🥰</p>
        <p>
          Feel free to contact me via my email address <a
            href="mailto:crupest@crupest.life"
          >crupest@crupest.life</a>, or just create an issue in any of my <a
            rel="noopener noreferrer"
            href="https://github.com/crupest"
          >GitHub</a>
          repos. I love talking with people a lot.
        </p>
        <div id="links" class="mono-link">
          goto:
          <ul>
            <li><a href="/git/">git</a></li>
            <li><a href="/notes/">notes</a></li>
            <li><a href="/notes/hurd/">hurd</a></li>
            <li><a href="/notes/cheat-sheet/">cheat-sheet</a></li>
          </ul>
        </div>
      </section>
      <hr />
      <section id="recent-posts">
        <h2>Recent Posts <a class="mono-link" href="/posts/">(all)</a></h2>
        ${postsPreviewHtml(recentPosts, "h3")}
      </section>
      <hr />
      <section>
        <h2 id="friends">
          My Friends <small>(more links are being collected ...)</small>
        </h2>
        <div id="friends-container">
          ${friendHtml({
            name: "wsm",
            avatar: "https://avatars.githubusercontent.com/u/74699943?v=4",
            github: "wushuming666",
          })} ${friendHtml({
            name: "hsz",
            url: "https://www.hszsoft.com",
            avatar: "https://avatars.githubusercontent.com/u/63097618?v=4",
            github: "hszSoft",
            tag: "随性の程序员",
          })}
        </div>
      </section>
    `,
  });
}

interface FriendData {
  name: string;
  avatar: string;
  github: string;
  url?: string;
  tag?: string;
}

function friendHtml(friend: FriendData): Html {
  const ghUrl = `https://github.com/${friend.github}`;
  const linkUrl = friend.url ?? ghUrl;
  return html`
    <div class="friend">
      <a rel="noopener noreferrer" href="${linkUrl}">
        <img
          class="friend-avatar"
          alt="Friend ${friend.name}'s avatar"
          src="${friend.avatar}"
          width="80"
          height="80"
        /><br />${friend.name}</a>
      <a rel="noopener noreferrer" href="${ghUrl}">
        <img class="friend-github" src="/assets/gh.png" />
      </a><br />
      ${friend.tag
        ? html`
          <span class="friend-tag">${friend.tag}</span>
        `
        : html`

        `}
    </div>
  `;
}

export function singlePage(
  page: Page,
  pages: Map<string, Page>,
): Html {
  return baseLayout({
    title: page.title,
    extraCss: ["single", ...(page.extraCss ?? [])],
    content: html`
      ${navHtml(page.slug, pages)}
      <h1 class="post-title">${page.title}</h1>
      <hr />
      <p class="post-info">
        ${page.date
          ? html`
            <span class="created">${dateHtml(page.date)}</span> |
          `
          : html`

          `}
        <span class="words">${page.wordCount} words</span>
        ${page.lastmod && page.date &&
            page.lastmod.getTime() !== page.date.getTime()
          ? html`
            <span class="last-updated">Last updated: ${dateHtml(
              page.lastmod,
            )}</span>
          `
          : html`

          `}
      </p>
      ${raw(page.content)}
    `,
    footer: navHtml(page.slug, pages),
  });
}

export function listPage(
  page: Page,
  childPages: Page[],
  pages: Map<string, Page>,
): Html {
  return baseLayout({
    title: page.title,
    extraCss: ["article"],
    content: html`
      ${navHtml(page.slug, pages)}
      <h1>${page.title}</h1>
      <hr />
      ${postsPreviewHtml(childPages, "h3")}
    `,
  });
}
