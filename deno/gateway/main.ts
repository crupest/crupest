import { Context, Hono } from "hono";
import { serveStatic } from "hono/deno";
import { logger } from "hono/logger";

import { ConfigDefinition, ConfigProvider } from "@crupest/base/config";
import { CronTask } from "@crupest/base/cron";

const PREFIX = "crupest";
const CONFIG_DEFINITION: ConfigDefinition = {
  domain: {
    description: "the root domain",
  },
  github: {
    description: "site owner's github url",
  },
  v2rayPath: {
    description: "the path for v2ray websocket",
  },
  mailServerAwsInboundPath: {
    description: "the path for mail server aws inbound webhook",
  },
} as const satisfies ConfigDefinition;

const configProvider = new ConfigProvider(PREFIX, CONFIG_DEFINITION);
type Config = typeof configProvider;

interface Bindings {
  remoteAddr: string;
}

interface Env {
  Bindings: Bindings;
}

function createReverseProxyHandler({ originServer }: { originServer: string }) {
  return async (c: Context<Env>) => {
    const url = new URL(c.req.url);
    const { host, protocol } = url;

    let forwardedFor = c.req.header("x-forwarded-for");
    if (forwardedFor) forwardedFor += `, ${c.env.remoteAddr}`;
    else forwardedFor = c.env.remoteAddr;

    const connection = c.req.header("upgrade") ? "upgrade" : "close";

    url.protocol = "http:";
    url.host = originServer;

    return await fetch(url, {
      method: c.req.method,
      headers: {
        ...c.req.header(),
        "Connection": connection,
        "Host": host,
        "X-Forwarded-For": forwardedFor,
        "X-Forwarded-Host": host,
        "X-Forwarded-Proto": protocol.slice(0, -1),
        "X-Real-IP": c.env.remoteAddr,
      },
      body: c.req.raw.body,
      redirect: "manual",
    });
  };
}

function createHttpHono() {
  const app = new Hono();
  app.use(logger());

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

function createHttpsHono({ config }: { config: Config }) {
  const app = new Hono({
    getPath: (req) => req.url.replace(/^https?:\/([^?]+).*$/, "$1"),
  });
  app.use(logger());

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

let servers: {
  httpServer: Deno.HttpServer<Deno.NetAddr>;
  httpsServer: Deno.HttpServer<Deno.NetAddr>;
} | null = null;

async function restartServer() {
  if (servers) {
    await Promise.all([
      servers.httpServer.shutdown(),
      servers.httpsServer.shutdown(),
    ]);
  }

  const httpApp = createHttpHono();
  const httpsApp = createHttpsHono({ config: configProvider });

  const httpServer = Deno.serve({
    port: 80,
  }, (req, info) => {
    return httpApp.fetch(req, info);
  });

  const httpsServer = Deno.serve({
    port: 443,
    cert: await Deno.readTextFile(
      `/etc/letsencrypt/live/${configProvider.get("domain")}/fullchain.pem`,
    ),
    key: await Deno.readTextFile(
      `/etc/letsencrypt/live/${configProvider.get("domain")}/privkey.pem`,
    ),
  }, (req, info) => {
    return httpsApp.fetch(req, info);
  });

  servers = { httpServer, httpsServer };
  return servers;
}

async function certbotRenew() {
  const command = new Deno.Command("certbot", {
    args: ["renew", "--webroot", "-w", "/var/www/certbot"],
  });
  const process = command.spawn();
  await process.status;
  await restartServer();
}

function main() {
  restartServer();

  setTimeout(() => {
    new CronTask({
      name: "certbot-renewal",
      interval: 1000 * 60 * 60 * 12,
      callback: certbotRenew,
      startNow: true,
    });
  }, 5000);
}

main();
