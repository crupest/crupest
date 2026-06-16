import { join } from "@std/path";

import { createApp } from "./app.ts";

const port = parseInt(Deno.env.get("PORT") ?? "3001", 10);

let app = await createApp();
let server = Deno.serve({ port }, app.fetch);

const watcher = Deno.watchFs([
  join(import.meta.dirname!, "content"),
  join(import.meta.dirname!, "static"),
], { recursive: true });

for await (const event of watcher) {
  console.log(">>>> event", event);
  console.log(">>>> restarting server...");
  server.shutdown();
  await server.finished;
  app = await createApp();
  server = Deno.serve({ port }, app.fetch);
}
