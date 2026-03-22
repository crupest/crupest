import { Hono } from "hono";
import { serveStatic } from "hono/deno";

import { CronTask } from "@crupest/base/cron";

import { Config, configProvider } from "./base.ts";
import { createRateLimitMiddleware } from "./middleware/rate-limit.ts";
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

function createRootHono(
  { basePath, config }: { basePath: string; config: Config },
) {
  const app = new Hono();

  app.get("/github", (c) => {
    const githubUrl = config.get("github");
    return c.redirect(githubUrl, 302);
  });

  app.all(
    "/git/*",
    createReverseProxyHandler({ originServer: "git-server:3636" }),
  );

  app.all(
    `/${config.get("v2rayPath")}`,
    createReverseProxyHandler({ originServer: "v2ray:10000" }),
  );

  app.get(
    "*",
    serveStatic({
      root: "/srv/www",
      rewriteRequestPath: (path) => path.replace(basePath, ""),
    }),
  );

  return app;
}

function createMailHono(
  { basePath, config }: { basePath: string; config: Config },
) {
  const app = new Hono();

  app.get(
    "/robots.txt",
    serveStatic({
      root: "/srv/mail",
      rewriteRequestPath: (path) => path.replace(basePath, ""),
    }),
  );

  app.all(
    `/${config.get("mailServerAwsInboundPath")}`,
    createReverseProxyHandler({ originServer: "mail-server:2345" }),
  );

  app.all(
    "*",
    createReverseProxyHandler({ originServer: "roundcubemail:80" }),
  );

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

  const rootBasePath = `/${config.get("domain")}`;
  app.route(
    rootBasePath,
    createRootHono({ basePath: rootBasePath, config }),
  );

  const mailBasePath = `/mail.${config.get("domain")}`;
  app.route(
    mailBasePath,
    createMailHono({ basePath: mailBasePath, config }),
  );

  return app;
}

class DenoHttpServerWrapper {
  #name: string;
  #abortController: AbortController;
  #server: Deno.HttpServer;

  constructor(
    name: string,
    hono: Hono,
    options:
      | Deno.ServeTcpOptions
      | (Deno.ServeTcpOptions & Deno.TlsCertifiedKeyPem),
  ) {
    this.#name = name;
    this.#abortController = new AbortController();
    this.#server = Deno.serve({
      signal: this.#abortController.signal,
      ...options,
    }, (req, info) => {
      return hono.fetch(req, info);
    });
  }

  async stop() {
    console.log(`Try to shutdown server "${this.#name}" gracefully...`);
    const result = await Promise.any([
      this.#server.shutdown().then(() => true),
      new Promise((resolve) => setTimeout(() => resolve(false), 5000)),
    ]);
    if (!result) {
      console.warn(
        `Failed to shutdown server "${this.#name}" gracefully, force to abort.`,
      );
      this.#abortController.abort();
      await this.#server.finished;
    }
    console.log(`Server "${this.#name}" stopped.`);
  }
}

async function startHttpServer() {
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
    new DenoHttpServerWrapper("HTTP", httpApp, { port: 80 }),
  );
}

async function certbotRenew() {
  console.log("Start certbot renewal...");
  const command = new Deno.Command("certbot", {
    args: ["renew", "--webroot", "-w", "/var/www/certbot"],
  });
  const process = command.spawn();
  await process.status;
  console.log("Certbot renewal completed.");
}

async function main() {
  const _geositeWorker = new Worker(
    new URL("./worker/geosite.ts", import.meta.url).href,
    {
      name: "GeoSite Worker",
      type: "module",
    },
  );

  const httpsAccessLogFile = await Deno.open("/app/state/https-access.log", {
    create: true,
    append: true,
  });
  const httpsAccessLogTextEncoder = new TextEncoder();

  async function startHttpsServer() {
    const httpsApp = createHttpsHono({
      config: configProvider,
      logWriter: async (str) => {
        await httpsAccessLogFile.write(
          httpsAccessLogTextEncoder.encode(str + "\n"),
        );
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
    });
  }

  const _httpServer = await startHttpServer();
  let httpsServer = await startHttpsServer();

  const renewCertbotAndRestartHttpsServer = async () => {
    await certbotRenew();
    await httpsServer.stop();
    httpsServer = await startHttpsServer();
  };

  setTimeout(async () => {
    await renewCertbotAndRestartHttpsServer();
    new CronTask({
      name: "certbot-renewal",
      interval: 1000 * 60 * 60 * 12,
      callback: renewCertbotAndRestartHttpsServer,
      startNow: true,
    });
  }, 5000);
}

await main();
