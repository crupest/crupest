import { encodeBase64 } from "@std/encoding/base64";
import { parse } from "@std/csv/parse";
import emailAddresses from "email-addresses";

import log from "./log.ts";
import config from "./config.ts";

class MailParseError extends Error {
  constructor(
    message: string,
    public readonly mail: Mail,
    public readonly lineNumber?: number,
    options?: ErrorOptions,
  ) {
    if (lineNumber != null) message += `(at line ${lineNumber})`;
    super(message, options);
  }
}

interface ParsedMail {
  sections: {
    header: string;
    body: string;
  };
  /**
   * The empty line between headers and body.
   */
  sep: string;
  eol: string;
}

export class Mail {
  date?: Date;
  messageId?: string;
  deliverMessage?: string;

  constructor(public raw: string) {}

  toUtf8Bytes(): Uint8Array {
    const utf8Encoder = new TextEncoder();
    return utf8Encoder.encode(this.raw);
  }

  toBase64(): string {
    return encodeBase64(this.raw);
  }

  simpleParse(): ParsedMail {
    const twoEolMatch = this.raw.match(/(\r?\n)(\r?\n)/);
    if (twoEolMatch == null) {
      throw new MailParseError(
        "No header/body section separator (2 successive EOLs) found.",
        this,
      );
    }

    const [eol, sep] = [twoEolMatch[1], twoEolMatch[2]];

    if (eol !== sep) {
      log.warn("Different EOLs (\\r\\n, \\n) found.");
    }

    return {
      sections: {
        header: this.raw.slice(0, twoEolMatch.index!),
        body: this.raw.slice(twoEolMatch.index! + eol.length + sep.length),
      },
      sep,
      eol,
    };
  }

  simpleParseHeaders(): [key: string, value: string][] {
    const { sections } = this.simpleParse();
    const headers: [string, string][] = [];

    let field: string | null = null;
    let lineNumber = 1;

    const handleField = () => {
      if (field == null) return;
      const sepPos = field.indexOf(":");
      if (sepPos === -1) {
        throw new MailParseError(
          "No ':' in the header field.",
          this,
          lineNumber,
        );
      }
      headers.push([field.slice(0, sepPos).trim(), field.slice(sepPos + 1)]);
      field = null;
    };

    for (const line of sections.header.trimEnd().split(/\r?\n|\r/)) {
      if (line.match(/^\s/)) {
        if (field == null) {
          throw new MailParseError(
            "Header field starts with a space.",
            this,
            lineNumber,
          );
        }
        field += line;
      } else {
        handleField();
        field = line;
      }
      lineNumber += 1;
    }

    handleField();

    return headers;
  }

  simpleParseDate<T = undefined>(
    invalidValue: T | undefined = undefined,
  ): Date | T | undefined {
    const headers = this.simpleParseHeaders();
    for (const [key, value] of headers) {
      if (key.toLowerCase() === "date") {
        const date = new Date(value);
        if (isNaN(date.getTime())) {
          log.warn(`Invalid date string (${value}) found in header.`);
          return invalidValue;
        }
        return date;
      }
    }
    return undefined;
  }

  simpleParseRecipients(
    options?: { domain?: string; headers?: string[] },
  ): Set<string> {
    const domain = options?.domain;
    const headers = options?.headers ?? ["to", "cc", "bcc", "x-original-to"];
    const recipients = new Set<string>();
    for (const [key, value] of this.simpleParseHeaders()) {
      if (headers.includes(key.toLowerCase())) {
        emailAddresses.parseAddressList(value)?.flatMap((a) =>
          a.type === "mailbox" ? a.address : a.addresses.map((a) => a.address)
        )?.forEach((a) => {
          if (domain == null || a.endsWith(domain)) {
            recipients.add(a);
          }
        });
      }
    }
    return recipients;
  }

  // TODO: Add folding.
  appendHeaders(headers: [key: string, value: string][]) {
    const { sections, sep, eol } = this.simpleParse();

    this.raw = sections.header + eol +
      headers.map(([k, v]) => `${k}: ${v}`).join(eol) + eol + sep +
      sections.body;
  }
}

export type MailDeliverResultKind = "done" | "fail" | "retry";

export interface MailDeliverRecipientResult {
  kind: MailDeliverResultKind;
  message: string;
  cause?: unknown;
}

export class MailDeliverResult {
  readonly recipients: Map<string, MailDeliverRecipientResult> = new Map();

  add(
    recipient: string,
    kind: MailDeliverResultKind,
    message: string,
    cause?: unknown,
  ) {
    this.recipients.set(recipient, { kind, message, cause });
  }

  set(recipient: string, result: MailDeliverRecipientResult) {
    this.recipients.set(recipient, result);
  }

  [Symbol.for("Deno.customInspect")]() {
    return [
      ...this.recipients.entries().map(([recipient, result]) =>
        `${recipient} [${result.kind}]: ${result.message}`
      ),
    ].join("\n");
  }
}

export class MailDeliverContext {
  readonly recipients: Set<string> = new Set();
  readonly result: MailDeliverResult = new MailDeliverResult();

  constructor(public mail: Mail) {}
}

export interface MailDeliverHook {
  callback(context: MailDeliverContext): Promise<void>;
}

export abstract class MailDeliverer {
  abstract readonly name: string;
  preHooks: MailDeliverHook[] = [];
  postHooks: MailDeliverHook[] = [];

  protected abstract doDeliver(
    mail: Mail,
    context: MailDeliverContext,
  ): Promise<void>;

  async deliverRaw(rawMail: string): Promise<Mail> {
    const mail = new Mail(rawMail);
    await this.deliver({ mail });
    return mail;
  }

  async deliver(
    options: { mail: Mail; recipients?: string[] },
  ): Promise<MailDeliverResult> {
    log.info(`Begin to deliver mail via ${this.name}...`);

    const context = new MailDeliverContext(options.mail);
    options.recipients?.forEach((r) => context.recipients.add(r));

    for (const hook of this.preHooks) {
      await hook.callback(context);
    }

    await this.doDeliver(context.mail, context);

    for (const hook of this.postHooks) {
      await hook.callback(context);
    }

    log.info("Deliver result:");
    log.info(context.result);

    if (context.result.recipients.values().some((r) => r.kind !== "done")) {
      throw new Error("Mail failed to deliver.");
    }

    return context.result;
  }
}

export class RecipientFromHeadersHook implements MailDeliverHook {
  callback(context: MailDeliverContext) {
    if (context.recipients.size !== 0) {
      log.warn(
        "Recipients are already filled. Won't set them with ones in headers.",
      );
    } else {
      context.mail.simpleParseRecipients({
        domain: config.get("mailDomain"),
      }).forEach((r) => context.recipients.add(r));

      log.info(
        "Recipients found from mail headers: ",
        [...context.recipients].join(" "),
      );
    }
    return Promise.resolve();
  }
}

export class FallbackRecipientHook implements MailDeliverHook {
  constructor(public fallback: Set<string> = new Set()) {}

  callback(context: MailDeliverContext) {
    if (context.recipients.size === 0) {
      log.info(
        "No recipients, fill with fallback: ",
        [...this.fallback].join(" "),
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

  async #parseAliasFile(): Promise<Map<string, string>> {
    const result = new Map();
    if ((await Deno.stat(this.#aliasFile)).isFile) {
      log.info(`Found recipients alias file: ${this.#aliasFile}.`);
      const text = await Deno.readTextFile(this.#aliasFile);
      const csv = parse(text);
      for (const [real, ...aliases] of csv) {
        aliases.forEach((a) => result.set(a, real));
      }
    }
    return result;
  }

  async callback(context: MailDeliverContext) {
    const aliases = await this.#parseAliasFile();
    for (const recipient of [...context.recipients]) {
      const realRecipients = aliases.get(recipient);
      if (realRecipients != null) {
        log.info(`Recipient alias resolved: ${recipient} => ${realRecipients}.`);
        context.recipients.delete(recipient);
        context.recipients.add(realRecipients);
      }
    }
  }
}
