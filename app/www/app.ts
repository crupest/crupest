import express, { type Express } from "express";

import { Site } from "./site.js";

export async function createApp(): Promise<Express> {
  const app = express();
  const site = await new Site().load();

  for (const [path, page] of site.pages) {
    const fullPath = `${site.baseUrl}${
      path.endsWith("/") ? path.slice(0, -1) : path
    }`;

    app.get(`${fullPath}/`, async (_request, response, next) => {
      try {
        response
          .status(200)
          .type("html")
          .send(await page.getTextContent());
      } catch (error) {
        next(error);
      }
    });

    if (fullPath.length !== 0) {
      app.get(fullPath, (_request, response) => {
        response.redirect(301, `${fullPath}/`);
      });
    }
  }

  for (const resource of site.resources) {
    app.get(
      `${site.baseUrl}${resource.outputPath}`,
      async (_request, response, next) => {
        try {
          response
            .status(200)
            .type(resource.mimeType)
            .send(Buffer.from(await resource.getContent()));
        } catch (error) {
          next(error);
        }
      },
    );

    for (const additionalOutput of resource.additionalOutputs) {
      app.get(
        `${site.baseUrl}${additionalOutput.path}`,
        (_request, response) => {
          response
            .status(200)
            .type(additionalOutput.mimeType)
            .send(Buffer.from(additionalOutput.content));
        },
      );
    }
  }

  return app;
}
