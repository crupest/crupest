import { createApp } from "./app.ts";

const app = await createApp();
const port = parseInt(Deno.env.get("PORT") ?? "3001", 10);
Deno.serve({ port }, app.fetch);
