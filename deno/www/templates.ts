import { Html, html, raw } from "@crupest/base-contrib/html";
import type { Article } from "./content.ts";
import type { Site } from "./site.ts";

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
  name: string;
  href: Html;
}

function buildBreadcrumbs(path: string, site: Site): BreadcrumbItem[] {
  const parts = path.split("/").filter(Boolean);
  const crumbs: BreadcrumbItem[] = [{ name: "home", href: site.pageLink("/") }];

  for (let i = 0; i < parts.length; i++) {
    const p = "/" + parts.slice(0, i + 1).join("/") + "/";
    crumbs.push({ name: parts[i], href: site.pageLink(p) });
  }

  return crumbs;
}

function navHtml(path: string, site: Site): Html {
  const crumbs = buildBreadcrumbs(path, site);

  const links = crumbs.slice(0, -1).map(
    (c) =>
      html`
        <a class="mono-link" href="${c.href}">${c.name}</a> &gt;
      `,
  );
  return html`
    <nav class="mono">${links}this</nav>
  `;
}

// --- Article preview ---

function articlePreviewHtml(
  article: Article,
  headingTag: string,
  site: Site,
): Html {
  return html`
    <section class="article-preview">
      <span class="date">${formatDate(article.date)}</span>
      ${raw(`<${headingTag} class="title">`)}<a href="${site.pageLink(
        article.path,
      )}">${article
        .title}</a>${raw(`</${headingTag}>`)}
      <p class="content">${article.summary
        .split("\n").map((l) =>
          html`
            ${l}<br />
          `
        )}</p>
      <p>... <a class="mono-link" href="${site.pageLink(
        article.path,
      )}">Read more</a></p>
    </section>
  `;
}

function articlePreviewListHtml(
  articles: Article[],
  headingTag: string,
  site: Site,
): Html {
  return html`
    ${articles.map((article, i) =>
      html`
        ${i > 0 && html`
          <hr class="article-preview-hr">
        `} ${articlePreviewHtml(article, headingTag, site)}
      `
    )}
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

export function baseLayout(options: LayoutOptions, site: Site): Html {
  const title = options.title ?? "crupest's life";

  const cssLinks = ["base", ...(options.extraCss ?? [])].map(
    (css) =>
      html`
        <link rel="stylesheet" href="${site.resourceLink.css(css)}" />
      `,
  );

  return html`
    <!DOCTYPE html>
    <html>
      <head>
        <meta charset="utf-8">
        <meta http-equiv="X-UA-Compatible" content="IE=edge">
        <link rel="icon" href="${site.resourceLink("favicon.ico")}" />
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />
        <title>${title}</title>
        <script src="${site.resourceLink.js("color-scheme")}"></script>
        ${cssLinks} ${options.extraHead}
      </head>
      <body>
        <article id="main-article">
          ${options.content}
          <hr />
          <footer class="mono-link">
            ${options.footer}
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

export function homePage(site: Site): Html {
  const recentPosts = site.posts.slice(0, 3);

  return baseLayout({
    extraCss: ["home", "article"],
    content: html`
      <img
        id="avatar"
        src="${site.resourceLink.asset("avatar.png")}"
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
            <li><a href="${site.pageLink("/notes/")}">notes</a></li>
            <li><a href="${site.pageLink(
              "/notes/cheat-sheet/",
            )}">cheat-sheet</a></li>
          </ul>
        </div>
      </section>
      <hr />
      <section id="recent-posts">
        <h2>Recent Posts <a class="mono-link" href="${site.pageLink(
          "/posts/",
        )}">(all)</a></h2>
        ${articlePreviewListHtml(recentPosts, "h3", site)}
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
          }, site)} ${friendHtml({
            name: "hsz",
            url: "https://www.hszsoft.com",
            avatar: "https://avatars.githubusercontent.com/u/63097618?v=4",
            github: "hszSoft",
            tag: "随性の程序员",
          }, site)}
        </div>
      </section>
    `,
  }, site);
}

interface FriendData {
  name: string;
  avatar: string;
  github: string;
  url?: string;
  tag?: string;
}

function friendHtml(friend: FriendData, site: Site): Html {
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
        <img class="friend-github" src="${site.resourceLink.asset(
          "gh.png",
        )}" alt="github logo" />
      </a><br />
      ${friend.tag &&
        html`
          <span class="friend-tag">${friend.tag}</span>
        `}
    </div>
  `;
}

export function singlePage(article: Article, site: Site): Html {
  return baseLayout({
    title: article.title,
    extraCss: ["single", ...(article.css ?? [])],
    content: html`
      ${navHtml(article.path, site)}
      <h1 class="post-title">${article.title}</h1>
      <hr />
      <p class="post-info">
        ${html`
          <span class="created">${dateHtml(article.date)}</span>
        `} | <span class="words">${article.wordCount} words</span>
        ${article.lastmod &&
          article.lastmod.getTime() !== article.date.getTime() &&
          html`
            <span class="last-updated">Last updated: ${dateHtml(
              article.lastmod,
            )}</span>
          `}
      </p>
      ${raw(article.renderedHtml)}
    `,
    footer: navHtml(article.path, site),
  }, site);
}

export function listPage({ path, title, articles, site }: {
  path: string;
  title: string;
  articles: Article[];
  site: Site;
}): Html {
  return baseLayout({
    title,
    extraCss: ["article"],
    content: html`
      ${navHtml(path, site)}
      <h1>${title}</h1>
      <hr />
      ${articlePreviewListHtml(articles, "h3", site)}
    `,
  }, site);
}
