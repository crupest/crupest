import { encodeBase64 } from "@std/encoding/base64";
import { parse } from "@std/csv/parse";
import emailAddresses from "email-addresses";

class MailSimpleParseError extends Error {}

class MailSimpleParsedHeaders {
  constructor(public fields: [key: string, value: string][]) {}

  getFirst(fieldKey: string): string | undefined {
    for (const [key, value] of this.fields) {
      if (key.toLowerCase() === fieldKey.toLowerCase()) return value;
    }
    return undefined;
  }

  messageId(): string | undefined {
    const messageIdField = this.getFirst("message-id");
    if (messageIdField == null) return undefined;

    const match = messageIdField.match(/\<(.*?)\>/);
    if (match != null) {
      return match[1];
    } else {
      console.warn("Invalid message-id header of mail: " + messageIdField);
      return undefined;
    }
  }

  date(invalidToUndefined: boolean = true): Date | undefined {
    const dateField = this.getFirst("date");
    if (dateField == null) return undefined;

    const date = new Date(dateField);
    if (invalidToUndefined && isNaN(date.getTime())) {
      console.warn(`Invalid date string (${dateField}) found in header.`);
      return undefined;
    }
    return date;
  }

  from(): string | undefined {
    const fromField = this.getFirst("from");
    if (fromField == null) return undefined;

    const addr = emailAddresses.parseOneAddress(fromField);
    return addr?.type === "mailbox" ? addr.address : undefined;
  }

  recipients(options?: { domain?: string; headers?: string[] }): Set<string> {
    const domain = options?.domain;
    const headers = options?.headers ?? ["to", "cc", "bcc", "x-original-to"];
    const recipients = new Set<string>();
    for (const [key, value] of this.fields) {
      if (headers.includes(key.toLowerCase())) {
        emailAddresses
          .parseAddressList(value)
          ?.flatMap((a) => (a.type === "mailbox" ? a : a.addresses))
          ?.forEach(({ address }) => {
            if (domain == null || address.endsWith(domain)) {
              recipients.add(address);
            }
          });
      }
    }
    return recipients;
  }
}

class MailSimpleParsedSections {
  header: string;
  body: string;
  eol: string;
  sep: string;

  constructor(raw: string) {
    const twoEolMatch = raw.match(/(\r?\n)(\r?\n)/);
    if (twoEolMatch == null) {
      throw new MailSimpleParseError(
        "No header/body section separator (2 successive EOLs) found.",
      );
    }

    const [eol, sep] = [twoEolMatch[1], twoEolMatch[2]];

    if (eol !== sep) {
      console.warn("Different EOLs (\\r\\n, \\n) found.");
    }

    this.header = raw.slice(0, twoEolMatch.index!);
    this.body = raw.slice(twoEolMatch.index! + eol.length + sep.length);
    this.eol = eol;
    this.sep = sep;
  }

  headers(): MailSimpleParsedHeaders {
    const headers = [] as [key: string, value: string][];

    let field: string | null = null;
    let lineNumber = 1;

    const handleField = () => {
      if (field == null) return;
      const sepPos = field.indexOf(":");
      if (sepPos === -1) {
        throw new MailSimpleParseError(`No ':' in the header line: ${field}`);
      }
      headers.push([field.slice(0, sepPos).trim(), field.slice(sepPos + 1)]);
      field = null;
    };

    for (const line of this.header.trimEnd().split(/\r?\n|\r/)) {
      if (line.match(/^\s/)) {
        if (field == null) {
          throw new MailSimpleParseError("Header section starts with a space.");
        }
        field += line;
      } else {
        handleField();
        field = line;
      }
      lineNumber += 1;
    }

    handleField();

    return new MailSimpleParsedHeaders(headers);
  }
}

export class Mail {
  constructor(public raw: string) {}

  toUtf8Bytes(): Uint8Array {
    const utf8Encoder = new TextEncoder();
    return utf8Encoder.encode(this.raw);
  }

  toBase64(): string {
    return encodeBase64(this.raw);
  }

  startSimpleParse() {
    return { sections: () => new MailSimpleParsedSections(this.raw) };
  }

  simpleFindAllAddresses(): string[] {
    const re = /,?\<?([a-z0-9_'+\-\.]+\@[a-z0-9_'+\-\.]+)\>?,?/gi;
    return [...this.raw.matchAll(re)].map((m) => m[1]);
  }
}

export type MailDeliverResultKind = "done" | "fail";

export interface MailDeliverRecipientResult {
  kind: MailDeliverResultKind;
  message: string;
  cause?: unknown;
}

export class MailDeliverResult {
  smtpMessage: string = "";
  recipients: Map<string, MailDeliverRecipientResult> = new Map();

  constructor(public mail: Mail) {}

  hasError(): boolean {
    return (
      this.recipients.size === 0 ||
      this.recipients.values().some((r) => r.kind !== "done")
    );
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
  readonly result;

  constructor(public mail: Mail) {
    this.result = new MailDeliverResult(this.mail);
  }
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

  async deliverRaw(rawMail: string) {
    return await this.deliver({ mail: new Mail(rawMail) });
  }

  async deliver(options: {
    mail: Mail;
    recipients?: string[];
  }): Promise<MailDeliverResult> {
    console.info(`Begin to deliver mail via ${this.name}...`);

    const context = new MailDeliverContext(options.mail);
    options.recipients?.forEach((r) => context.recipients.add(r));

    for (const hook of this.preHooks) {
      await hook.callback(context);
    }

    await this.doDeliver(context.mail, context);

    for (const hook of this.postHooks) {
      await hook.callback(context);
    }

    console.info("Deliver result:");
    console.info(context.result);

    if (context.result.hasError()) {
      throw new Error("Mail failed to deliver.");
    }

    return context.result;
  }
}

export abstract class SyncMailDeliverer extends MailDeliverer {
  #last: Promise<void> = Promise.resolve();

  override async deliver(options: {
    mail: Mail;
    recipients?: string[];
  }): Promise<MailDeliverResult> {
    console.info(
      "The mail deliverer is sync. Wait for last delivering done...",
    );
    await this.#last;
    const result = super.deliver(options);
    this.#last = result.then(
      () => {},
      () => {},
    );
    return result;
  }
}

export class RecipientFromHeadersHook implements MailDeliverHook {
  constructor(public mailDomain: string) {}

  callback(context: MailDeliverContext) {
    if (context.recipients.size !== 0) {
      console.warn(
        "Recipients are already filled. Won't set them with ones in headers.",
      );
    } else {
      context.mail
        .startSimpleParse()
        .sections()
        .headers()
        .recipients({
          domain: this.mailDomain,
        })
        .forEach((r) => context.recipients.add(r));

      console.info(
        "Recipients found from mail headers: " +
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
        "No recipients, fill with fallback: " + [...this.fallback].join(", "),
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
      console.info(`Found recipients alias file: ${this.#aliasFile}.`);
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
        console.info(
          `Recipient alias resolved: ${recipient} => ${realRecipients}.`,
        );
        context.recipients.delete(recipient);
        context.recipients.add(realRecipients);
      }
    }
  }
}
