import { Hono } from "hono";

import { Site } from "./site.ts";

export async function createApp(): Promise<Hono> {
  const app = new Hono();
  const site = await new Site().load();

  for (const [path, page] of site.pages) {
    const fullPath = `${site.baseUrl}${
      path.endsWith("/") ? path.slice(0, -1) : path
    }`;

    app.get(`${fullPath}/`, async (c) => {
      return c.html(await page.getTextContent(), 200);
    });

    if (fullPath.length !== 0) {
      app.get(fullPath, (c) => {
        return c.redirect(`${fullPath}/`, 301);
      });
    }
  }

  for (const resource of site.resources) {
    app.get(`${site.baseUrl}${resource.outputPath}`, async (c) => {
      return c.body(
        (await resource.getContent()) as Uint8Array<ArrayBuffer>,
        200,
        {
          "Content-Type": resource.mimeType,
        },
      );
    });

    for (const additionalOutput of resource.additionalOutputs) {
      app.get(`${site.baseUrl}${additionalOutput.path}`, (c) => {
        return c.body(
          additionalOutput.content as Uint8Array<ArrayBuffer>,
          200,
          {
            "Content-Type": additionalOutput.mimeType,
          },
        );
      });
    }
  }

  return app;
}
