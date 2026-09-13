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
import { createRateLimitMiddleware } from "./middleware/rate-limit.ts";
import { createConnectionLimitMiddleware } from "./middleware/connection-limit.ts";
import { createLogMiddleware, LogWriter } from "./middleware/log.ts";
import { createReverseProxyHandler } from "./helper/reverse-proxy.ts";

function createHttpHono(options?: { accessLogWriter?: LogWriter }) {
  const app = new Hono();
  app.use(createLogMiddleware({ writer: options?.accessLogWriter }));
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
      target: `https://github.com/${config.get("github")}`,
    }, {
      path: "/git/*",
      type: "reverse-proxy",
      server: "git-server:3636",
      middlewares: [createGitConnectionLimitMiddleware()],
    }, {
      path: "/webdav/*",
      type: "reverse-proxy",
      server: "webdav:3923",
    }, {
      path: "/gen/*",
      type: "static",
      root: "/srv/www",
    }, {
      path: "*",
      type: "reverse-proxy",
      server: "www:3000",
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

function createSubdomainHono(
  { basePath, sites, logger }: {
    basePath: string;
    sites: Site[];
    logger: ILogger;
  },
) {
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
          createReverseProxyHandler({ originServer: site.server, logger }),
        );
        break;
      }
    }
  }
  return app;
}

function createHttpsHono(
  { logger, config, accessLogWriter }: {
    logger: ILogger;
    config: Config;
    accessLogWriter?: LogWriter;
  },
) {
  const app = new Hono({
    getPath: (req) => req.url.replace(/^https?:\/([^?]+).*$/, "$1"),
  });
  app.use(createLogMiddleware({ writer: accessLogWriter }));
  app.use(createRateLimitMiddleware());

  const rootDomain = config.get("domain");

  const subdomains = createSubdomains(config);

  for (const { subdomain, sites } of subdomains) {
    const basePath = subdomain === ""
      ? `/${rootDomain}`
      : `/${subdomain}.${rootDomain}`;
    app.route(basePath, createSubdomainHono({ basePath, sites, logger }));
  }

  return app;
}

function createControllerHono(options: {
  restartHttpsServer: () => void;
}) {
  const app = new Hono();

  app.get("/restart-https-server", (c) => {
    options.restartHttpsServer();
    return c.text("HTTPS server restarted.", 200);
  });

  return app;
}

interface Services {
  config: Config;
  logger: ILogger;
}

type ServeOptions =
  | Deno.ServeTcpOptions
  | (Deno.ServeTcpOptions & Deno.TlsCertifiedKeyPem);

interface ServerDefinition {
  name: string;
  serveOptions: () => ServeOptions | Promise<ServeOptions>;
  honoCreator: (accessLogWriter?: LogWriter) => Hono | Promise<Hono>;
  /** If set, an access log file is opened for this server and closed when
   * the server stops. */
  accessLogFilePath?: string;
}

interface ServerState {
  abortController: AbortController;
  server: Deno.HttpServer<Deno.NetAddr>;
}

class ServerWrapper {
  #services: Services;
  #definition: ServerDefinition;
  #state: ServerState | null = null;
  #finished: Promise<void> = Promise.resolve();

  constructor(services: Services, definition: ServerDefinition) {
    this.#services = services;
    this.#definition = definition;
  }

  get #logger() {
    return this.#services.logger;
  }

  get running(): boolean {
    return this.#state != null;
  }

  /** Resolves when the current run finishes (clean stop or caught error). */
  get finished(): Promise<void> {
    return this.#finished;
  }

  /** Starts the server and waits until it stops. Errors during server
   * creation (`serveOptions`, `honoCreator`, `Deno.serve`) are hard errors
   * and propagate to the caller. */
  async run(): Promise<void> {
    const { name, serveOptions, honoCreator, accessLogFilePath } =
      this.#definition;
    if (this.#state != null) {
      throw new Error(`Server ${name} is already running.`);
    }

    const accessLogFile = accessLogFilePath == null
      ? null
      : await Deno.open(accessLogFilePath, { create: true, append: true });

    let server: Deno.HttpServer<Deno.NetAddr>;
    try {
      const textEncoder = new TextEncoder();
      const accessLogWriter: LogWriter | undefined = accessLogFile == null
        ? undefined
        : async (str) => {
            await accessLogFile.write(textEncoder.encode(str + "\n"));
          };

      const options = await serveOptions();
      const hono = await honoCreator(accessLogWriter);
      const abortController = new AbortController();
      this.#logger.info(`Starting server "${name}" ...`);
      server = Deno.serve({
        signal: abortController.signal,
        ...options,
      }, hono.fetch);
      this.#state = { abortController, server };
    } catch (error) {
      // Hard error while creating the server: release the log file and
      // rethrow so the process fails fast.
      try {
        accessLogFile?.close();
      } catch {
        // Ignore close errors; the original error is what matters.
      }
      throw error;
    }

    const [finished, resolveFinished] = Utils.promise<void>();
    this.#finished = finished;

    this.#logger.info(
      `Server "${name}" started on ${server.addr.hostname}:${server.addr.port}.`,
    );

    void (async () => {
      try {
        await server.finished;
        this.#logger.info(`Server "${name}" stopped.`);
      } catch (error) {
        // A serving error is not fatal: log it and let the loop restart.
        this.#logger.error(`Server "${name}" failed:`, error);
      } finally {
        this.#state = null;
        try {
          accessLogFile?.close();
        } catch (error) {
          this.#logger.error(
            `Failed to close access log file for server "${name}":`,
            error,
          );
        }
        resolveFinished();
      }
    })();

    await finished;
  }

  async stop(): Promise<void> {
    if (this.#state == null) return;
    const { name } = this.#definition;
    const { server: denoServer, abortController } = this.#state;
    this.#logger.info(`Try to shutdown server "${name}" gracefully...`);
    const result = await Utils.timeout(
      denoServer.shutdown(),
      Temporal.Duration.from({ seconds: 5 }),
    );
    if (!result) {
      this.#logger.warn(
        `Failed to shutdown server "${name}" gracefully, force to abort.`,
      );
      abortController.abort();
    }
    // Wait until the run fully finishes (state cleared and file closed).
    await this.#finished;
  }
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
  const services: Services = { logger, config: configProvider };

  const httpServer = new ServerWrapper(services, {
    name: "HTTP",
    honoCreator: (accessLogWriter) =>
      createHttpHono({ accessLogWriter }),
    serveOptions: () => ({ port: 80 }),
    accessLogFilePath: "/app/state/http-access.log",
  });
  const httpsServer = new ServerWrapper(services, {
    name: "HTTPS",
    honoCreator: (accessLogWriter) =>
      createHttpsHono({
        logger,
        config: configProvider,
        accessLogWriter,
      }),
    serveOptions: async () => ({
      port: 443,
      cert: await Deno.readTextFile(
        `/etc/letsencrypt/live/${configProvider.get("domain")}/fullchain.pem`,
      ),
      key: await Deno.readTextFile(
        `/etc/letsencrypt/live/${configProvider.get("domain")}/privkey.pem`,
      ),
    }),
    accessLogFilePath: "/app/state/https-access.log",
  });
  const controllerServer = new ServerWrapper(services, {
    name: "Controller",
    honoCreator: () => createControllerHono({ restartHttpsServer }),
    serveOptions: () => ({
      hostname: "127.0.0.1",
      port: 2266,
    }),
  });

  function restartHttpsServer() {
    // Trigger a graceful stop; the main loop restarts the server once it
    // has fully finished. No need to await here.
    httpsServer.stop().catch((error) => {
      logger.error(`Failed to stop HTTPS server:`, error);
    });
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

  const servers = [httpServer, httpsServer, controllerServer];
  while (true) {
    await Promise.race(
      servers.map((server) =>
        server.running ? server.finished : server.run()
      ),
    );
  }
}

await main();
