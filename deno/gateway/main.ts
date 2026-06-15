import { Hono, MiddlewareHandler } from "hono";
import { serveStatic } from "hono/deno";

import { Utils } from "@crupest/base";
import { CronTask } from "@crupest/base/cron";
import {
  getDefaultLogger,
  ILogger,
  installLogHandlerForWorker,
} from "@crupest/base/log";

import { Config, configProvider } from "./base.ts";
import { basicAuthFromFile } from "./middleware/basic-auth.ts";
import { createRateLimitMiddleware } from "./middleware/rate-limit.ts";
import { createConnectionLimitMiddleware } from "./middleware/connection-limit.ts";
import { createLogMiddleware, LogWriter } from "./middleware/log.ts";
import { createReverseProxyHandler } from "./helper/reverse-proxy.ts";

function createHttpHono(options?: { logWriter?: LogWriter }) {
  const app = new Hono();
  app.use(createLogMiddleware({ writer: options?.logWriter }));
  app.use(createRateLimitMiddleware());

  // Serve static files for ACME challenge
  app.get(
    "/.well-known/acme-challenge/*",
    serveStatic({
      root: "/var/www/certbot",
    }),
  );

  // Redirect all other requests to the HTTPS version of the site
  app.all("*", (c) => {
    return c.redirect(c.req.url.replace("http://", "https://"), 301);
  });

  return app;
}

interface SiteCommon {
  path: string;
  middlewares?: MiddlewareHandler[];
}

interface ReverseProxySite extends SiteCommon {
  type: "reverse-proxy";
  server: string;
}

interface StaticSite extends SiteCommon {
  type: "static";
  root: string;
}

interface RedirectSite extends SiteCommon {
  type: "redirect";
  target: string;
}

type Site = ReverseProxySite | StaticSite | RedirectSite;

interface Subdomain {
  subdomain: string;
  sites: Site[];
}

function createGitConnectionLimitMiddleware() {
  const GIT_HTTP_BACKEND = new RegExp(
    `^/git/.*/(HEAD|info/refs|objects/info/[^/]+|git-(upload|receive)-pack)$`,
  );
  const GIT_STATIC = new RegExp(
    `^/git/.*/((objects/[0-9a-f]{2}/[0-9a-f]{38})|(pack/pack-[0-9a-f]{40}.(pack|idx)))$`,
  );

  // Connection limit only for cgit CGI (not git-backend, not static)
  return createConnectionLimitMiddleware({
    maxConnections: 5,
    shouldLimit: (ctx) => {
      const path = new URL(ctx.req.url).pathname;
      if (path.startsWith("/git/static")) return false;
      if (GIT_HTTP_BACKEND.test(path)) return false;
      if (GIT_STATIC.test(path)) return false;
      return true;
    },
  });
}

function createSubdomains(config: Config): Subdomain[] {
  return [{
    subdomain: "",
    sites: [{
      path: "/github",
      type: "redirect",
      target: config.get("github"),
    }, {
      path: "/git/*",
      type: "reverse-proxy",
      server: "git-server:3636",
      middlewares: [createGitConnectionLimitMiddleware()],
    }, {
      path: "/webdav/*",
      type: "reverse-proxy",
      server: "webdav:5000",
    }, {
      path: "/dev/*",
      type: "reverse-proxy",
      server: "debian-dev:7681",
      middlewares: [basicAuthFromFile(config.get("devUserFile"))],
    }, {
      path: "*",
      type: "static",
      root: "/srv/www",
    }],
  }, {
    subdomain: "mail",
    sites: [{
      path: "/robots.txt",
      type: "static",
      root: "/srv/mail",
    }, {
      path: `/${config.get("mailServerAwsInboundPath")}`,
      type: "reverse-proxy",
      server: "mail-server:2345",
    }, {
      path: "*",
      type: "reverse-proxy",
      server: "roundcubemail:80",
    }],
  }];
}

function createSubdomainHono(basePath: string, sites: Site[]) {
  const app = new Hono();
  for (const site of sites) {
    if (site.middlewares != null && site.middlewares.length > 0) {
      app.use(site.path, ...site.middlewares);
    }
    switch (site.type) {
      case "redirect": {
        app.get(
          site.path,
          (c) => c.redirect(site.target, 302),
        );
        break;
      }
      case "static": {
        app.get(
          site.path,
          serveStatic({
            root: site.root,
            rewriteRequestPath: (path) => path.replace(basePath, ""),
          }),
        );
        break;
      }
      case "reverse-proxy": {
        app.all(
          site.path,
          createReverseProxyHandler({ originServer: site.server }),
        );
        break;
      }
    }
  }
  return app;
}

function createHttpsHono(
  { config, logWriter }: { config: Config; logWriter?: LogWriter },
) {
  const app = new Hono({
    getPath: (req) => req.url.replace(/^https?:\/([^?]+).*$/, "$1"),
  });
  app.use(createLogMiddleware({ writer: logWriter }));
  app.use(createRateLimitMiddleware());

  const rootDomain = config.get("domain");

  const subdomains = createSubdomains(config);

  for (const { subdomain, sites } of subdomains) {
    const basePath = subdomain === ""
      ? `/${rootDomain}`
      : `/${subdomain}.${rootDomain}`;
    app.route(basePath, createSubdomainHono(basePath, sites));
  }

  return app;
}

function createControllerHono(options: {
  restartHttpsServer: () => Promise<void>;
}) {
  const app = new Hono();

  app.get("/restart-https-server", async (c) => {
    await options.restartHttpsServer();
    return c.text("HTTPS server restarted.", 200);
  });

  return app;
}

class DenoHttpServerWrapper {
  #name: string;
  #abortController: AbortController;
  #server: Deno.HttpServer<Deno.NetAddr>;
  #logger: ILogger;

  constructor(
    name: string,
    hono: Hono,
    { logger, ...options }:
      & (
        | Deno.ServeTcpOptions
        | (Deno.ServeTcpOptions & Deno.TlsCertifiedKeyPem)
      )
      & {
        logger: ILogger;
      },
  ) {
    this.#name = name;
    this.#logger = logger;
    this.#abortController = new AbortController();
    this.#logger.info(`Starting server "${this.#name}" ...`);
    this.#server = Deno.serve({
      signal: this.#abortController.signal,
      ...options,
    }, hono.fetch);
    this.#logger.info(
      `Server "${this.#name}" started on ${this.#server.addr.hostname}:${this.#server.addr.port}.`,
    );
  }

  async stop() {
    this.#logger.info(`Try to shutdown server "${this.#name}" gracefully...`);
    const result = await Utils.timeout(
      this.#server.shutdown(),
      Temporal.Duration.from({ seconds: 5 }),
    );
    if (!result) {
      this.#logger.warn(
        `Failed to shutdown server "${this.#name}" gracefully, force to abort.`,
      );
      this.#abortController.abort();
      await this.#server.finished;
    }
    this.#logger.info(`Server "${this.#name}" stopped.`);
  }
}

async function startHttpServer({ logger }: { logger: ILogger }) {
  const accessLogFile = await Deno.open("/app/state/http-access.log", {
    create: true,
    append: true,
  });
  const textEncoder = new TextEncoder();
  const httpApp = createHttpHono({
    logWriter: async (str) => {
      await accessLogFile.write(textEncoder.encode(str + "\n"));
    },
  });
  return await Promise.resolve(
    new DenoHttpServerWrapper("HTTP", httpApp, { port: 80, logger }),
  );
}

async function startHttpsServer({ logger }: { logger: ILogger }) {
  const accessLogFile = await Deno.open("/app/state/https-access.log", {
    create: true,
    append: true,
  });
  const textEncoder = new TextEncoder();

  const httpsApp = createHttpsHono({
    config: configProvider,
    logWriter: async (str) => {
      await accessLogFile.write(textEncoder.encode(str + "\n"));
    },
  });
  return new DenoHttpServerWrapper("HTTPS", httpsApp, {
    port: 443,
    cert: await Deno.readTextFile(
      `/etc/letsencrypt/live/${configProvider.get("domain")}/fullchain.pem`,
    ),
    key: await Deno.readTextFile(
      `/etc/letsencrypt/live/${configProvider.get("domain")}/privkey.pem`,
    ),
    logger,
  });
}

async function startControllerServer(
  options: { restartHttpsServer: () => Promise<void>; logger: ILogger },
) {
  const controllerApp = createControllerHono(options);
  return await Promise.resolve(
    new DenoHttpServerWrapper("Controller", controllerApp, {
      hostname: "127.0.0.1",
      port: 2266,
      logger: options.logger,
    }),
  );
}

async function certbotRenew(logger: ILogger) {
  logger.info("Start certbot renewal...");
  const command = new Deno.Command("certbot", {
    args: [
      "renew",
      "--webroot",
      "-w",
      "/var/www/certbot",
      "--deploy-hook",
      "curl -s http://127.0.0.1:2266/restart-https-server",
    ],
  });
  const output = await command.output();
  const decoder = new TextDecoder();
  logger[output.success ? "info" : "error"](
    "Certbot renewal completed with exit code " + output.code,
  );
  logger.info("Certbot stdout:\n" + decoder.decode(output.stdout));
  logger.error("Certbot stderr:\n" + decoder.decode(output.stderr));
}

async function main() {
  const logger = getDefaultLogger();
  const geositeWorker = new Worker(
    new URL("./worker/geosite.ts", import.meta.url).href,
    {
      name: "GeoSite Worker",
      type: "module",
    },
  );
  installLogHandlerForWorker(geositeWorker, logger);

  const _httpServer = await startHttpServer({ logger });
  let httpsServer = await startHttpsServer({ logger });
  const _controllerServer = await startControllerServer({
    restartHttpsServer,
    logger,
  });

  async function restartHttpsServer() {
    await httpsServer.stop();
    httpsServer = await startHttpsServer({ logger });
  }

  setTimeout(async () => {
    await certbotRenew(logger);
    new CronTask({
      name: "certbot-renewal",
      interval: Temporal.Duration.from({ hours: 12 }),
      callback: () => certbotRenew(logger),
      enableNow: true,
    });
  }, 5000);
}

await main();
