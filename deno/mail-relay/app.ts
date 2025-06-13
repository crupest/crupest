import { Hono } from "hono";
import { logger as honoLogger } from "hono/logger";

import { LogFileProvider } from "@crupest/base/log";

import {
  AliasRecipientMailHook,
  FallbackRecipientHook,
  MailDeliverer,
  RecipientFromHeadersHook,
} from "./mail.ts";
import { DovecotMailDeliverer } from "./dovecot.ts";
import { DumbSmtpServer } from "./dumb-smtp-server.ts";

export function createInbound(
  logFileProvider: LogFileProvider,
  {
    fallback,
    mailDomain,
    aliasFile,
    ldaPath,
  }: {
    fallback: string[];
    mailDomain: string;
    aliasFile: string;
    ldaPath: string;
  },
) {
  const deliverer = new DovecotMailDeliverer(logFileProvider, ldaPath);
  deliverer.preHooks.push(
    new RecipientFromHeadersHook(mailDomain),
    new FallbackRecipientHook(new Set(fallback)),
    new AliasRecipientMailHook(aliasFile),
  );
  return deliverer;
}

export function createHono(outbound: MailDeliverer, inbound: MailDeliverer) {
  const hono = new Hono();

  hono.onError((err, c) => {
    console.error("Hono handler throws an error.", err);
    return c.json({ msg: "Server error, check its log." }, 500);
  });
  hono.use(honoLogger());
  hono.post("/send/raw", async (context) => {
    const body = await context.req.text();
    if (body.trim().length === 0) {
      return context.json({ msg: "Can't send an empty mail." }, 400);
    } else {
      const result = await outbound.deliverRaw(body);
      return context.json({
        awsMessageId: result.awsMessageId,
      });
    }
  });
  hono.post("/receive/raw", async (context) => {
    await inbound.deliverRaw(await context.req.text());
    return context.json({ msg: "Done!" });
  });

  return hono;
}

export function createSmtp(outbound: MailDeliverer) {
  return new DumbSmtpServer(outbound);
}

export async function sendMail(port: number) {
  const decoder = new TextDecoder();
  let text = "";
  for await (const chunk of Deno.stdin.readable) {
    text += decoder.decode(chunk);
  }

  const res = await fetch(`http://127.0.0.1:${port}/send/raw`, {
    method: "post",
    body: text,
  });
  const fn = res.ok ? "info" : "error";
  console[fn](res);
  console[fn](await res.text());
  if (!res.ok) Deno.exit(-1);
}
