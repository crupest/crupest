import { createServer } from "node:http";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import chokidar from "chokidar";
import type { Express } from "express";

import { createApp } from "./app.js";

const port = Number.parseInt(process.env.PORT ?? "3001", 10);
const packageDir = dirname(fileURLToPath(import.meta.url));
let app: Express = await createApp();

const server = createServer((request, response) => {
  app(request, response);
});

server.listen(port, () => {
  console.info(`WWW development server listening on port ${port}.`);
});

let reloadTimer: ReturnType<typeof setTimeout> | undefined;
const watcher = chokidar.watch(
  [join(packageDir, "content"), join(packageDir, "static")],
  {
    ignoreInitial: true,
  },
);

watcher.on("all", () => {
  clearTimeout(reloadTimer);
  reloadTimer = setTimeout(async () => {
    try {
      app = await createApp();
      console.info("Reloaded site content.");
    } catch (error) {
      console.error("Failed to reload site content.", error);
    }
  }, 100);
});
