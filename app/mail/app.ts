import express, { type Express } from "express";

import type { ILogger } from "@crupest/base/log";

import { DovecotMailDeliverer } from "./dovecot.js";
import { DumbSmtpServer } from "./dumb-smtp-server.js";
import {
  AliasRecipientMailHook,
  FallbackRecipientHook,
  type MailDeliverer,
  RecipientFromHeadersHook,
} from "./mail.js";

export function createInbound({
  logger,
  fallback,
  mailDomain,
  aliasFile,
  ldaPath,
  doveadmPath,
}: {
  logger: ILogger;
  fallback: string[];
  mailDomain: string;
  aliasFile: string;
  ldaPath: string;
  doveadmPath: string;
}) {
  const deliverer = new DovecotMailDeliverer({ logger, ldaPath, doveadmPath });
  deliverer.preHooks.push(
    new RecipientFromHeadersHook(mailDomain),
    new FallbackRecipientHook(new Set(fallback)),
    new AliasRecipientMailHook(aliasFile),
  );
  return deliverer;
}

export function createApp({
  logger,
  outbound,
  inbound,
}: {
  logger: ILogger;
  outbound: MailDeliverer;
  inbound: MailDeliverer;
}): Express {
  const app = express();
  const rawMail = express.text({ limit: "50mb", type: "*/*" });

  app.use((request, response, next) => {
    const start = Date.now();
    response.once("finish", () => {
      void logger.info(
        `${request.method} ${request.originalUrl} ${response.statusCode} ${
          Date.now() - start
        }ms`,
      );
    });
    next();
  });

  app.post("/send/raw", rawMail, async (request, response) => {
    const body = typeof request.body === "string" ? request.body : "";
    if (body.trim().length === 0) {
      response.status(400).json({ message: "Can't send an empty mail." });
      return;
    }

    const result = await outbound.deliver({ mail: body });
    response.json({ newMessageId: result.newMessageId });
  });

  app.post("/receive/raw", rawMail, async (request, response) => {
    const body = typeof request.body === "string" ? request.body : "";
    await inbound.deliver({ mail: body });
    response.json({ message: "Done!" });
  });

  app.use(
    (
      error: unknown,
      _request: express.Request,
      response: express.Response,
      _next: express.NextFunction,
    ) => {
      void logger.error("Express handler threw an uncaught error.", error);
      response.status(500).json({ message: "Server error, check its log." });
    },
  );

  return app;
}

export function createSmtp({
  logger,
  outbound,
}: {
  logger: ILogger;
  outbound: MailDeliverer;
}) {
  return new DumbSmtpServer(logger, outbound);
}

export async function sendMail(port: number) {
  process.stdin.setEncoding("utf8");
  let text = "";
  for await (const chunk of process.stdin) {
    text += chunk;
  }

  const response = await fetch(`http://127.0.0.1:${port}/send/raw`, {
    method: "POST",
    body: text,
    headers: {
      "Content-Type": "message/rfc822",
    },
  });
  const log = response.ok ? console.info : console.error;
  log(response);
  log(await response.text());
  if (!response.ok) process.exitCode = 1;
}
