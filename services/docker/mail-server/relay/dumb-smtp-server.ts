import config from "./config.ts";
import log from "./log.ts";
import { MailDeliverer } from "./mail.ts";

const CRLF = "\r\n";

const SERVER_NAME = `[${config.SMTP_HOST}]:${config.SMTP_PORT}`;

const RESPONSES = {
  "READY": `220 ${SERVER_NAME} SMTP Ready`,
  "EHLO": `250 ${SERVER_NAME}`,
  "MAIL": "250 2.1.0 Sender OK",
  "RCPT": "250 2.1.5 Recipient OK",
  "DATA": "354 Start mail input; end with <CRLF>.<CRLF>",
  "QUIT": `211 2.0.0 ${SERVER_NAME} closing connection`,
  "INVALID": "500 5.5.1 Error: command not recognized",
} as const;

export class DumbSMTPServer {
  #deliverer: MailDeliverer;

  constructor(deliverer: MailDeliverer) {
    this.#deliverer = deliverer;
  }

  async #send(rawMail: string): Promise<{ message: string }> {
    const mail = await this.#deliverer.deliverRaw(rawMail);
    return {
      message: mail.deliverMessage ?? "Success",
    };
  }

  async #handleConnection(conn: Deno.Conn) {
    using disposeStack = new DisposableStack();
    disposeStack.defer(() => {
      log.info("Close smtp session tcp connection.");
      conn.close();
    });
    const writer = conn.writable.getWriter();
    disposeStack.defer(() => writer.releaseLock());
    const reader = conn.readable.getReader();
    disposeStack.defer(() => reader.releaseLock());

    const [decoder, encoder] = [new TextDecoder(), new TextEncoder()];
    const decode = (data: Uint8Array) => decoder.decode(data);
    const send = async (s: string) =>
      await writer.write(encoder.encode(s + CRLF));

    let buffer: string = "";
    let rawMail: string | null = null;

    await send(RESPONSES["READY"]);

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;

      buffer += decode(value);

      while (true) {
        const eolPos = buffer.indexOf(CRLF);
        if (eolPos === -1) break;

        const line = buffer.slice(0, eolPos);
        buffer = buffer.slice(eolPos + CRLF.length);

        if (rawMail == null) {
          log.info("Smtp server received line:", line);
          const upperLine = line.toUpperCase();
          if (upperLine.startsWith("EHLO") || upperLine.startsWith("HELO")) {
            await send(RESPONSES["EHLO"]);
          } else if (upperLine.startsWith("MAIL FROM:")) {
            await send(RESPONSES["MAIL"]);
          } else if (upperLine.startsWith("RCPT TO:")) {
            await send(RESPONSES["RCPT"]);
          } else if (upperLine === "DATA") {
            await send(RESPONSES["DATA"]);
            log.info("Begin to receive mail data...");
            rawMail = "";
          } else if (upperLine === "QUIT") {
            await send(RESPONSES["QUIT"]);
            return;
          } else {
            log.warn("Smtp server command unrecognized:", line);
            await send(RESPONSES["INVALID"]);
            return;
          }
        } else {
          if (line === ".") {
            try {
              log.info("Done receiving mail data...");
              const { message } = await this.#send(rawMail);
              await send(`250 2.6.0 ${message}`);
              rawMail = null;
              log.info("Done SMTP mail session.");
            } catch (err) {
              log.info(err);
              await send("554 5.3.0 Error: check server log");
              return;
            }
          } else {
            const dataLine = line.startsWith("..") ? line.slice(1) : line;
            rawMail += dataLine + CRLF;
          }
        }
      }
    }
  }

  async serve() {
    const listener = Deno.listen({
      hostname: config.SMTP_HOST,
      port: config.SMTP_PORT,
    });
    listener.unref();
    log.info(`Dumb SMTP server running on port ${config.SMTP_PORT}.`);

    for await (const conn of listener) {
      await this.#handleConnection(conn);
    }
  }
}
