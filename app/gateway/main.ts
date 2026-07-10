import { execFile } from "node:child_process";
import { createWriteStream, type WriteStream } from "node:fs";
import { readFile } from "node:fs/promises";
import {
  createServer as createHttpServer,
  type IncomingMessage,
  type Server as HttpServer,
} from "node:http";
import {
  createServer as createHttpsServer,
  type Server as HttpsServer,
} from "node:https";
import type { Socket } from "node:net";
import type { Duplex } from "node:stream";
import { promisify } from "node:util";
import { Worker } from "node:worker_threads";

import express, {
  type Express,
  type NextFunction,
  type Request,
  type RequestHandler,
  type Response,
  type Router,
} from "express";

import { Utils } from "@crupest/base";
import { CronTask } from "@crupest/base/cron";
import {
  getDefaultLogger,
  type ILogger,
  installLogHandlerForWorker,
} from "@crupest/base/log";
import { Duration, isMain } from "@crupest/base/runtime";

import { type Config, configProvider } from "./base.js";
import { FileBasicAuthenticator } from "./middleware/basic-auth.js";
import { createConnectionLimitMiddleware } from "./middleware/connection-limit.js";
import { createLogMiddleware, type LogWriter } from "./middleware/log.js";
import { CrawlerRateLimiter } from "./middleware/rate-limit.js";
import {
  createReverseProxy,
  type ReverseProxy,
} from "./helper/reverse-proxy.js";

const execFileAsync = promisify(execFile);

function createHttpApp(options?: { logWriter?: LogWriter }): Express {
  const app = express();
  app.use(createLogMiddleware({ writer: options?.logWriter }));
  app.use(new CrawlerRateLimiter().middleware());
  app.use(
    "/.well-known/acme-challenge",
    express.static("/var/www/certbot/.well-known/acme-challenge"),
  );
  app.use((request, response) => {
    response.redirect(
      301,
      `https://${request.headers.host}${request.originalUrl}`,
    );
  });
  return app;
}

interface SiteCommon {
  path: string;
  middlewares?: RequestHandler[];
  upgradeAuthorize?: (request: IncomingMessage) => Promise<boolean>;
}

interface ReverseProxySite extends SiteCommon {
  type: "reverse-proxy";
  proxy: ReverseProxy;
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
  hostname: string;
  sites: Site[];
}

function createGitConnectionLimitMiddleware(): RequestHandler {
  const gitHttpBackend = new RegExp(
    "^/git/.*/(HEAD|info/refs|objects/info/[^/]+|git-(upload|receive)-pack)$",
  );
  const gitStatic = new RegExp(
    "^/git/.*/((objects/[0-9a-f]{2}/[0-9a-f]{38})|(pack/pack-[0-9a-f]{40}.(pack|idx)))$",
  );

  return createConnectionLimitMiddleware({
    maxConnections: 5,
    shouldLimit: (request) => {
      const path = request.path;
      return (
        !path.startsWith("/git/static") &&
        !gitHttpBackend.test(path) &&
        !gitStatic.test(path)
      );
    },
  });
}

function createSubdomains(config: Config): Subdomain[] {
  const rootDomain = config.get("domain");
  const devAuth = new FileBasicAuthenticator(config.get("devUserFile"));

  return [
    {
      hostname: rootDomain,
      sites: [
        {
          path: "/github",
          type: "redirect",
          target: config.get("github"),
        },
        {
          path: "/git/*",
          type: "reverse-proxy",
          proxy: createReverseProxy({ originServer: "git-server:3636" }),
          middlewares: [createGitConnectionLimitMiddleware()],
        },
        {
          path: "/webdav/*",
          type: "reverse-proxy",
          proxy: createReverseProxy({ originServer: "webdav:5000" }),
        },
        {
          path: "/dev/*",
          type: "reverse-proxy",
          proxy: createReverseProxy({ originServer: "debian-dev:7681" }),
          middlewares: [devAuth.middleware()],
          upgradeAuthorize: (request) => devAuth.verify(request.headers),
        },
        {
          path: "*",
          type: "static",
          root: "/srv/www",
        },
      ],
    },
    {
      hostname: `mail.${rootDomain}`,
      sites: [
        {
          path: "/robots.txt",
          type: "static",
          root: "/srv/mail",
        },
        {
          path: `/${config.get("mailServerAwsInboundPath")}`,
          type: "reverse-proxy",
          proxy: createReverseProxy({ originServer: "mail-server:2345" }),
        },
        {
          path: "*",
          type: "reverse-proxy",
          proxy: createReverseProxy({ originServer: "roundcubemail:80" }),
        },
      ],
    },
  ];
}

function matchesSitePath(pattern: string, path: string): boolean {
  if (pattern === "*") return true;
  if (pattern.endsWith("/*")) {
    const prefix = pattern.slice(0, -2);
    return path === prefix || path.startsWith(prefix + "/");
  }
  return path === pattern;
}

function runHandlers(
  handlers: RequestHandler[],
  request: Request,
  response: Response,
  done: NextFunction,
): void {
  let index = 0;
  const next: NextFunction = (error) => {
    if (error != null) {
      done(error);
      return;
    }
    const handler = handlers[index++];
    if (handler == null) {
      done();
      return;
    }
    try {
      Promise.resolve(handler(request, response, next)).catch(next);
    } catch (cause) {
      next(cause);
    }
  };
  next();
}

function createSubdomainRouter(sites: Site[]): Router {
  const router = express.Router();
  const staticHandlers = new Map<StaticSite, RequestHandler>(
    sites
      .filter((site): site is StaticSite => site.type === "static")
      .map((site) => [site, express.static(site.root)]),
  );

  router.use((request, response, next) => {
    const site = sites.find(
      (candidate) =>
        matchesSitePath(candidate.path, request.path) &&
        (candidate.type !== "redirect" || request.method === "GET"),
    );
    if (site == null) {
      response.status(404).send("Not Found");
      return;
    }

    let handler: RequestHandler;
    switch (site.type) {
      case "redirect":
        handler = (_request, result) => {
          result.redirect(302, site.target);
        };
        break;
      case "static":
        handler = staticHandlers.get(site)!;
        break;
      case "reverse-proxy":
        handler = site.proxy.middleware;
        break;
    }

    runHandlers(
      [...(site.middlewares ?? []), handler],
      request,
      response,
      next,
    );
  });

  return router;
}

function normalizeHostname(host: string | undefined): string {
  if (host == null) return "";
  return host.replace(/:\d+$/, "").toLowerCase();
}

function writeUpgradeError(
  socket: Duplex,
  status: number,
  message: string,
  headers: Record<string, string> = {},
): void {
  const reason =
    status === 401
      ? "Unauthorized"
      : status === 429
        ? "Too Many Requests"
        : "Not Found";
  const headerLines = Object.entries(headers)
    .map(([name, value]) => `${name}: ${value}\r\n`)
    .join("");
  socket.end(
    `HTTP/1.1 ${status} ${reason}\r\n${headerLines}Content-Type: text/plain; charset=utf-8\r\nContent-Length: ${Buffer.byteLength(
      message,
    )}\r\n\r\n${message}`,
  );
}

function createHttpsApplication({
  config,
  logWriter,
}: {
  config: Config;
  logWriter?: LogWriter;
}) {
  const app = express();
  const rateLimiter = new CrawlerRateLimiter();
  const subdomains = createSubdomains(config);
  const routers = new Map(
    subdomains.map(({ hostname, sites }) => [
      hostname.toLowerCase(),
      createSubdomainRouter(sites),
    ]),
  );

  app.use(createLogMiddleware({ writer: logWriter }));
  app.use(rateLimiter.middleware());
  app.use((request, response, next) => {
    const router = routers.get(normalizeHostname(request.headers.host));
    if (router == null) {
      response.status(404).send("Unknown host");
      return;
    }
    router(request, response, next);
  });

  const handleUpgrade = async (
    request: IncomingMessage,
    socket: Duplex,
    head: Buffer,
  ) => {
    const agent = request.headers["user-agent"];
    if (!rateLimiter.allow(typeof agent === "string" ? agent : undefined)) {
      writeUpgradeError(socket, 429, "Too Many Requests", {
        "Retry-After": "60",
      });
      return;
    }

    const subdomain = subdomains.find(
      ({ hostname }) =>
        hostname.toLowerCase() === normalizeHostname(request.headers.host),
    );
    const path = new URL(request.url ?? "/", "http://localhost").pathname;
    const site = subdomain?.sites.find(
      (candidate): candidate is ReverseProxySite =>
        candidate.type === "reverse-proxy" &&
        matchesSitePath(candidate.path, path),
    );
    if (site == null) {
      writeUpgradeError(socket, 404, "Not Found");
      return;
    }
    if (
      site.upgradeAuthorize != null &&
      !(await site.upgradeAuthorize(request))
    ) {
      writeUpgradeError(socket, 401, "Unauthorized", {
        "WWW-Authenticate": 'Basic realm="Secure Area"',
      });
      return;
    }
    site.proxy.upgrade(request, socket, head);
  };

  return { app, handleUpgrade };
}

function createControllerApp(options: {
  restartHttpsServer: () => Promise<void>;
}): Express {
  const app = express();
  app.get("/restart-https-server", async (_request, response) => {
    await options.restartHttpsServer();
    response.status(200).type("text").send("HTTPS server restarted.");
  });
  return app;
}

type NodeServer = HttpServer | HttpsServer;

class NodeServerWrapper {
  readonly #sockets = new Set<Socket>();
  readonly #name: string;
  readonly #server: NodeServer;
  readonly #logger: ILogger;
  readonly #cleanup: (() => Promise<void>) | undefined;

  private constructor(
    name: string,
    server: NodeServer,
    logger: ILogger,
    cleanup?: () => Promise<void>,
  ) {
    this.#name = name;
    this.#server = server;
    this.#logger = logger;
    this.#cleanup = cleanup;
    this.#server.on("connection", (socket) => {
      this.#sockets.add(socket);
      socket.once("close", () => this.#sockets.delete(socket));
    });
  }

  static async start(
    name: string,
    server: NodeServer,
    options: {
      hostname?: string;
      port: number;
      logger: ILogger;
      cleanup?: () => Promise<void>;
    },
  ): Promise<NodeServerWrapper> {
    const wrapper = new NodeServerWrapper(
      name,
      server,
      options.logger,
      options.cleanup,
    );
    options.logger.info(`Starting server "${name}" ...`);
    await new Promise<void>((resolve, reject) => {
      server.once("error", reject);
      server.listen(options.port, options.hostname, () => {
        server.off("error", reject);
        resolve();
      });
    });
    options.logger.info(
      `Server "${name}" started on ${options.hostname ?? "0.0.0.0"}:${options.port}.`,
    );
    return wrapper;
  }

  async stop(): Promise<void> {
    this.#logger.info(`Try to shutdown server "${this.#name}" gracefully...`);
    const closed = new Promise<void>((resolve) => {
      this.#server.close(() => resolve());
    });
    const graceful = await Utils.timeout(closed, Duration.seconds(5));
    if (!graceful) {
      this.#logger.warn(
        `Failed to shutdown server "${this.#name}" gracefully, destroying sockets.`,
      );
      for (const socket of this.#sockets) socket.destroy();
      await closed;
    }
    await this.#cleanup?.();
    this.#logger.info(`Server "${this.#name}" stopped.`);
  }
}

function createFileLogWriter(path: string): {
  stream: WriteStream;
  writer: LogWriter;
} {
  const stream = createWriteStream(path, { flags: "a" });
  return {
    stream,
    writer: (line) =>
      new Promise<void>((resolve, reject) => {
        stream.write(line + "\n", (error) =>
          error == null ? resolve() : reject(error),
        );
      }),
  };
}

async function startHttpServer({ logger }: { logger: ILogger }) {
  const log = createFileLogWriter("/app/state/http-access.log");
  const server = createHttpServer(createHttpApp({ logWriter: log.writer }));
  return await NodeServerWrapper.start("HTTP", server, {
    port: 80,
    logger,
    cleanup: () =>
      new Promise((resolve) => {
        log.stream.end(resolve);
      }),
  });
}

async function startHttpsServer({ logger }: { logger: ILogger }) {
  const log = createFileLogWriter("/app/state/https-access.log");
  const application = createHttpsApplication({
    config: configProvider,
    logWriter: log.writer,
  });
  const domain = configProvider.get("domain");
  const server = createHttpsServer(
    {
      cert: await readFile(
        `/etc/letsencrypt/live/${domain}/fullchain.pem`,
        "utf8",
      ),
      key: await readFile(
        `/etc/letsencrypt/live/${domain}/privkey.pem`,
        "utf8",
      ),
    },
    application.app,
  );
  server.on("upgrade", (request, socket, head) => {
    void application.handleUpgrade(request, socket, head).catch((error) => {
      logger.error("WebSocket upgrade failed.", error);
      socket.destroy();
    });
  });
  return await NodeServerWrapper.start("HTTPS", server, {
    port: 443,
    logger,
    cleanup: () =>
      new Promise((resolve) => {
        log.stream.end(resolve);
      }),
  });
}

async function startControllerServer(options: {
  restartHttpsServer: () => Promise<void>;
  logger: ILogger;
}) {
  const server = createHttpServer(createControllerApp(options));
  return await NodeServerWrapper.start("Controller", server, {
    hostname: "127.0.0.1",
    port: 2266,
    logger: options.logger,
  });
}

async function certbotRenew(logger: ILogger) {
  logger.info("Start certbot renewal...");
  try {
    const result = await execFileAsync("certbot", [
      "renew",
      "--webroot",
      "-w",
      "/var/www/certbot",
      "--deploy-hook",
      "curl -s http://127.0.0.1:2266/restart-https-server",
    ]);
    logger.info("Certbot renewal completed successfully.");
    if (result.stdout.length > 0)
      logger.info("Certbot stdout:\n" + result.stdout);
    if (result.stderr.length > 0)
      logger.warn("Certbot stderr:\n" + result.stderr);
  } catch (error) {
    logger.error("Certbot renewal failed.", error);
  }
}

export async function main() {
  const logger = getDefaultLogger();
  const sourceMode = import.meta.url.endsWith(".ts");
  const worker = new Worker(
    new URL(
      sourceMode ? "./worker/geosite.ts" : "./worker/geosite.js",
      import.meta.url,
    ),
    {
      execArgv: sourceMode ? process.execArgv : [],
      name: "GeoSite Worker",
    },
  );
  installLogHandlerForWorker(worker, logger);

  const httpServer = await startHttpServer({ logger });
  let httpsServer = await startHttpsServer({ logger });
  const controllerServer = await startControllerServer({
    restartHttpsServer: async () => {
      await httpsServer.stop();
      httpsServer = await startHttpsServer({ logger });
    },
    logger,
  });

  let shuttingDown = false;
  let certbotTask: CronTask | undefined;
  const certbotStartTimer = setTimeout(async () => {
    await certbotRenew(logger);
    if (shuttingDown) return;
    certbotTask = new CronTask({
      name: "certbot-renewal",
      interval: Duration.hours(12),
      callback: () => certbotRenew(logger),
      enableNow: true,
    });
  }, 5_000);
  certbotStartTimer.unref();

  let shutdownPromise: Promise<void> | undefined;
  const shutdown = () => {
    if (shutdownPromise == null) {
      shuttingDown = true;
      clearTimeout(certbotStartTimer);
      certbotTask?.disable();
      shutdownPromise = (async () => {
        try {
          await Promise.all([
            controllerServer.stop(),
            httpsServer.stop(),
            httpServer.stop(),
          ]);
        } finally {
          await worker.terminate();
        }
      })();
    }
    return shutdownPromise;
  };
  const handleShutdown = () => {
    void shutdown().catch((error) => {
      logger.error("Gateway shutdown failed.", error);
      process.exitCode = 1;
    });
  };
  process.once("SIGINT", handleShutdown);
  process.once("SIGTERM", handleShutdown);
}

if (isMain(import.meta.url)) {
  await main();
}
