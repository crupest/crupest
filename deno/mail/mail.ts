import { encodeBase64 } from "@std/encoding/base64";
import { parse } from "@std/csv/parse";

import { StringUtils } from "@crupest/base";

import { simpleParseMail } from "./mail-parsing.ts";

export class Mail {
  #raw;
  #parsed;

  constructor(raw: string) {
    this.#raw = raw;
    this.#parsed = simpleParseMail(raw);
  }

  get raw() {
    return this.#raw;
  }

  set raw(value) {
    this.#raw = value;
    this.#parsed = simpleParseMail(value);
  }

  get parsed() {
    return this.#parsed;
  }

  toUtf8Bytes(): Uint8Array {
    const utf8Encoder = new TextEncoder();
    return utf8Encoder.encode(this.raw);
  }

  toBase64(): string {
    return encodeBase64(this.raw);
  }

  simpleFindAllAddresses(): string[] {
    const re = /,?\<?([a-z0-9_'+\-\.]+\@[a-z0-9_'+\-\.]+)\>?,?/gi;
    return [...this.raw.matchAll(re)].map((m) => m[1]);
  }
}

export interface MailDeliverRecipientResult {
  kind: "success" | "failure";
  message?: string;
  cause?: unknown;
}

export class MailDeliverResult {
  message?: string;
  messageForSmtp?: string;
  newMessageId?: string;

  recipients = new Map<string, MailDeliverRecipientResult>();
  constructor(public mail: Mail) {}

  get hasFailure() {
    return this.recipients.values().some((v) => v.kind !== "success");
  }

  generateLogMessage(prefix: string) {
    const lines = [];
    if (this.message != null) lines.push(`${prefix} message: ${this.message}`);
    if (this.messageForSmtp != null) {
      lines.push(`${prefix} smtpMessage: ${this.messageForSmtp}`);
    }
    for (const [name, result] of this.recipients.entries()) {
      const { kind, message } = result;
      lines.push(`${prefix}   (${name}): ${kind} ${message}`);
    }
    return lines.join("\n");
  }

  generateMessageForSmtp(): string {
    if (this.messageForSmtp != null) return this.messageForSmtp;
    return `2.0.0 OK${
      StringUtils.prependNonEmpty(this.newMessageId)
    } Message accepted for delivery`;
  }
}

export class MailDeliverContext {
  readonly recipients: Set<string> = new Set();
  readonly result;

  constructor(public logTag: string, public mail: Mail) {
    this.result = new MailDeliverResult(this.mail);
  }
}

export interface MailDeliverHook {
  callback(context: MailDeliverContext): Promise<void>;
}

export abstract class MailDeliverer {
  #counter = 1;
  #last?: Promise<void>;

  abstract name: string;
  preHooks: MailDeliverHook[] = [];
  postHooks: MailDeliverHook[] = [];

  constructor(public sync: boolean) {}

  protected abstract doDeliver(
    mail: Mail,
    context: MailDeliverContext,
  ): Promise<void>;

  async deliverRaw(rawMail: string) {
    return await this.deliver({ mail: new Mail(rawMail) });
  }

  async #deliverCore(context: MailDeliverContext) {
    for (const hook of this.preHooks) {
      await hook.callback(context);
    }

    await this.doDeliver(context.mail, context);

    for (const hook of this.postHooks) {
      await hook.callback(context);
    }
  }

  async deliver(options: {
    mail: Mail;
    recipients?: string[];
    logTag?: string;
  }): Promise<MailDeliverResult> {
    const logTag = options.logTag ?? `[${this.name} ${this.#counter}]`;
    this.#counter++;

    if (this.#last != null) {
      console.info(logTag, "Wait for last delivering done...");
      await this.#last;
    }

    const context = new MailDeliverContext(
      logTag,
      options.mail,
    );
    options.recipients?.forEach((r) => context.recipients.add(r));

    console.info(context.logTag, "Begin to deliver mail...");

    const deliverPromise = this.#deliverCore(context);

    if (this.sync) {
      this.#last = deliverPromise.then(() => {}, () => {});
    }

    await deliverPromise;
    this.#last = undefined;

    console.info(context.logTag, "Deliver result:");
    console.info(context.result.generateLogMessage(context.logTag));

    if (context.result.hasFailure) {
      throw new Error("Failed to deliver to some recipients.");
    }

    return context.result;
  }
}

export class RecipientFromHeadersHook implements MailDeliverHook {
  constructor(public mailDomain: string) {}

  callback(context: MailDeliverContext) {
    if (context.recipients.size !== 0) {
      console.warn(
        context.logTag,
        "Recipients are already filled, skip inferring from headers.",
      );
    } else {
      [...context.mail.parsed.recipients].filter((r) =>
        r.endsWith("@" + this.mailDomain)
      ).forEach((r) => context.recipients.add(r));

      console.info(
        context.logTag,
        "Use recipients inferred from mail headers:",
        [...context.recipients].join(", "),
      );
    }
    return Promise.resolve();
  }
}

export class FallbackRecipientHook implements MailDeliverHook {
  constructor(public fallback: Set<string> = new Set()) {}

  callback(context: MailDeliverContext) {
    if (context.recipients.size === 0) {
      console.info(
        context.logTag,
        "Use fallback recipients:" + [...this.fallback].join(", "),
      );
      this.fallback.forEach((a) => context.recipients.add(a));
    }
    return Promise.resolve();
  }
}

export class AliasRecipientMailHook implements MailDeliverHook {
  #aliasFile;

  constructor(aliasFile: string) {
    this.#aliasFile = aliasFile;
  }

  async #parseAliasFile(logTag: string): Promise<Map<string, string>> {
    const result = new Map();
    if ((await Deno.stat(this.#aliasFile)).isFile) {
      const text = await Deno.readTextFile(this.#aliasFile);
      const csv = parse(text);
      for (const [real, ...aliases] of csv) {
        aliases.forEach((a) => result.set(a, real));
      }
    } else {
      console.warn(
        logTag,
        `Recipient alias file ${this.#aliasFile} is not found.`,
      );
    }
    return result;
  }

  async callback(context: MailDeliverContext) {
    const aliases = await this.#parseAliasFile(context.logTag);
    for (const recipient of [...context.recipients]) {
      const realRecipients = aliases.get(recipient);
      if (realRecipients != null) {
        console.info(
          context.logTag,
          `Recipient alias resolved: ${recipient} => ${realRecipients}.`,
        );
        context.recipients.delete(recipient);
        context.recipients.add(realRecipients);
      }
    }
  }
}

export class MessageIdRewriteHook implements MailDeliverHook {
  readonly #lookup;

  constructor(lookup: (origin: string) => Promise<string | null>) {
    this.#lookup = lookup;
  }

  async callback(context: MailDeliverContext): Promise<void> {
    const addresses = context.mail.simpleFindAllAddresses();
    for (const address of addresses) {
      const newMessageId = await this.#lookup(address);
      if (newMessageId != null && newMessageId.length !== 0) {
        console.info(
          context.logTag,
          `Rewrite address-line string in mail: ${address} => ${newMessageId}.`,
        );
        context.mail.raw = context.mail.raw.replaceAll(address, newMessageId);
      }
    }
  }
}

export class MessageIdSaveHook implements MailDeliverHook {
  readonly #record;

  constructor(
    record: (
      original: string,
      newMessageId: string,
      context: MailDeliverContext,
    ) => Promise<void>,
  ) {
    this.#record = record;
  }

  async callback(context: MailDeliverContext): Promise<void> {
    const { messageId } = context.mail.parsed;
    if (messageId == null) {
      console.warn(
        context.logTag,
        "Original mail doesn't have message id, skip saving message id map.",
      );
      return;
    }
    if (context.result.newMessageId != null) {
      console.info(
        context.logTag,
        `Save message id map: ${messageId} => ${context.result.newMessageId}.`,
      );
      context.mail.raw = context.mail.raw.replaceAll(
        messageId,
        context.result.newMessageId,
      );
      await this.#record(messageId, context.result.newMessageId, context);
    }
  }
}
