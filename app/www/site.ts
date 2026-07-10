import { basename, dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { Html, raw } from "@crupest/base-contrib/html";

import { type Article, loadArticles } from "./content.js";
import { AppResourceTransformer, Resource, scanResources } from "./resource.js";
import { homePage, listPage, singlePage } from "./templates.js";

const moduleDir = dirname(fileURLToPath(import.meta.url));
const packageDir =
  basename(moduleDir) === "build" ? dirname(moduleDir) : moduleDir;

export class Site {
  #baseUrl = "";
  #articles = new Map<string, Article>();
  #posts: Article[] = [];
  #pages = new Map<string, Resource>();
  #resources: Resource[] = [];
  readonly #transformer = new AppResourceTransformer();

  async #processResources(resources: Iterable<Resource>): Promise<void> {
    for (const resource of resources) {
      await this.#transformer.transform(resource);
    }
  }

  async #generatePages() {
    const addPage = (path: string, content: Html) => {
      const resource = new Resource({
        source: { type: "data", data: content.toEscapedString() },
        path,
        outputPath: `${path}${path.endsWith("/") ? "" : "/"}index.html`,
      });

      this.#pages.set(path, resource);
      this.#resources.push(resource);
    };

    addPage("/", homePage(this));
    addPage(
      "/posts",
      listPage({
        path: "/posts",
        title: "Posts",
        articles: this.#posts,
        site: this,
      }),
    );

    for (const [path, article] of this.#articles.entries()) {
      addPage(path, singlePage(article, this));
    }

    await this.#processResources(this.pages.values());
  }

  async load(): Promise<Site> {
    const articles = await loadArticles(join(packageDir, "content"));
    this.#articles = new Map(articles.map((a) => [a.path, a]));
    this.#posts = articles
      .filter((p) => p.path.startsWith("/posts/"))
      .sort((a, b) => b.date.getTime() - a.date.getTime());

    this.#resources = await scanResources(join(packageDir, "static"));
    await this.#processResources(
      this.#resources.filter((r) => r.path && /^\/?assets\//.test(r.path)),
    );

    await this.#generatePages();

    return this;
  }

  get baseUrl(): string {
    return this.#baseUrl;
  }

  get articles(): Article[] {
    return Array.from(this.#articles.values());
  }

  get posts(): Article[] {
    return this.#posts;
  }

  get pages(): Map<string, Resource> {
    return this.#pages;
  }

  get resources(): Resource[] {
    return this.#resources;
  }

  getOptionalResourceByPath(path: string): Resource | undefined {
    if (!path.startsWith("/")) {
      path = "/" + path;
    }
    return this.#resources.find((r) => r.path === path);
  }

  getResourceByPath(path: string): Resource {
    const resource = this.getOptionalResourceByPath(path);
    if (!resource) {
      throw new Error(`Resource not found for input path: ${path}`);
    }
    return resource;
  }

  getResourceHtmlLinkByPath(path: string): Html {
    const resource = this.getResourceByPath(path);
    return raw(resource.outputPath);
  }

  resourceLink = (() => {
    // TODO: Escape?
    const r = (path: string) =>
      `${this.#baseUrl}${this.getResourceHtmlLinkByPath(
        path,
      ).toEscapedString()}`;
    r.asset = (name: string) => r(`/assets/${name}`);
    r.css = (name: string) => r(`/assets/${name}.css`);
    r.js = (name: string) => r(`/assets/${name}.js`);
    r.page = (path: string) => new Html(`${this.#baseUrl}${path}`, true);
    return r;
  })();

  pageLink = this.resourceLink.page;
}
