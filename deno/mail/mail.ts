import { encodeBase64 } from "@std/encoding/base64";
import { parse } from "@std/csv/parse";

import { StringUtils } from "@crupest/base";
import type { ILogger } from "@crupest/base/log";

import { simpleParseMail } from "./mail-parsing.ts";

export class Mail {
  #raw;
  #parsed;
  #logger;

  constructor(raw: string, logger: ILogger) {
    this.#raw = raw;
    this.#parsed = simpleParseMail(raw, logger);
    this.#logger = logger;
  }

  get raw() {
    return this.#raw;
  }

  set raw(value) {
    this.#raw = value;
    this.#parsed = simpleParseMail(value, this.#logger);
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
  constructor(public readonly mail: Mail) {}

  get hasFailure() {
    return this.recipients.values().some((v) => v.kind !== "success");
  }

  generateLogMessage() {
    const lines = [];
    if (this.message != null) lines.push(`message: ${this.message}`);
    if (this.messageForSmtp != null) {
      lines.push(`smtpMessage: ${this.messageForSmtp}`);
    }
    for (const [name, result] of this.recipients.entries()) {
      const { kind, message } = result;
      lines.push(`\t(${name}): ${kind} ${message}`);
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

  constructor(public mail: Mail, public readonly logger: ILogger) {
    this.result = new MailDeliverResult(this.mail);
  }
}

export interface MailDeliverHook {
  callback(context: MailDeliverContext): Promise<void>;
}

export abstract class MailDeliverer {
  #sync: boolean;
  #counter = 1;
  #last?: Promise<void>;
  protected logger: ILogger;

  abstract name: string;
  preHooks: MailDeliverHook[] = [];
  postHooks: MailDeliverHook[] = [];

  constructor({ sync, logger }: { sync: boolean; logger: ILogger }) {
    this.#sync = sync;
    this.logger = logger;
  }

  protected abstract doDeliver(
    mail: Mail,
    context: MailDeliverContext,
  ): Promise<void>;

  async #deliverCore(context: MailDeliverContext) {
    for (const hook of this.preHooks) {
      await hook.callback(context);
    }

    await this.doDeliver(context.mail, context);

    for (const hook of this.postHooks) {
      await hook.callback(context);
    }
  }

  async deliver({ mail, recipients }: {
    mail: Mail | string;
    recipients?: string[];
  }): Promise<MailDeliverResult> {
    const logger = this.logger.withDefaultTag(
      `${this.name} ${this.#counter++}`,
    );

    if (typeof mail === "string") {
      mail = new Mail(mail, logger);
    }

    if (this.#last != null) {
      logger.info("Wait for last delivering done...");
      await this.#last;
    }

    const context = new MailDeliverContext(mail, logger);
    recipients?.forEach((r) => context.recipients.add(r));

    logger.info("Begin to deliver mail...");

    const deliverPromise = this.#deliverCore(context);

    if (this.#sync) {
      this.#last = deliverPromise.then(() => {}, () => {});
    }

    await deliverPromise;
    this.#last = undefined;

    logger.info("Deliver result:\n" + context.result.generateLogMessage());

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
      context.logger.warn(
        "Recipients are already filled, skip inferring from headers.",
      );
    } else {
      [...context.mail.parsed.recipients].filter((r) =>
        r.endsWith("@" + this.mailDomain)
      ).forEach((r) => context.recipients.add(r));

      context.logger.info(
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
      context.logger.info(
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

  async #parseAliasFile(
    context: MailDeliverContext,
  ): Promise<Map<string, string>> {
    const result = new Map();
    if ((await Deno.stat(this.#aliasFile)).isFile) {
      const text = await Deno.readTextFile(this.#aliasFile);
      const csv = parse(text);
      for (const [real, ...aliases] of csv) {
        aliases.forEach((a) => result.set(a, real));
      }
    } else {
      context.logger.warn(
        `Recipient alias file ${this.#aliasFile} is not found.`,
      );
    }
    return result;
  }

  async callback(context: MailDeliverContext) {
    const aliases = await this.#parseAliasFile(context);
    for (const recipient of [...context.recipients]) {
      const realRecipients = aliases.get(recipient);
      if (realRecipients != null) {
        context.logger.info(
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
        context.logger.info(
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
      context.logger.warn(
        "Original mail doesn't have message id, skip saving message id map.",
      );
      return;
    }
    if (context.result.newMessageId != null) {
      context.logger.info(
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
