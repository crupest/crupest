import { Logger } from "@crupest/base/log";
import { MailDeliverer } from "./mail.ts";

const CRLF = "\r\n";

function createResponses(host: string, port: number | string) {
  const serverName = `[${host}]:${port}`;
  return {
    serverName,
    READY: `220 ${serverName} SMTP Ready`,
    EHLO: `250 ${serverName}`,
    MAIL: "250 2.1.0 Sender OK",
    RCPT: "250 2.1.5 Recipient OK",
    DATA: "354 Start mail input; end with <CRLF>.<CRLF>",
    QUIT: `211 2.0.0 ${serverName} closing connection`,
    INVALID: "500 5.5.1 Error: command not recognized",
  } as const;
}

export class DumbSmtpServer {
  #logger;
  #deliverer;
  #responses: ReturnType<typeof createResponses> = createResponses(
    "invalid",
    "invalid",
  );

  constructor(logger: Logger, deliverer: MailDeliverer) {
    this.#logger = logger;
    this.#deliverer = deliverer;
  }

  async #handleConnection(conn: Deno.Conn) {
    using disposeStack = new DisposableStack();
    disposeStack.defer(() => {
      this.#logger.info("Close smtp session tcp connection.");
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

    await send(this.#responses["READY"]);

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
          this.#logger.info("Smtp server received line:", line);
          const upperLine = line.toUpperCase();
          if (upperLine.startsWith("EHLO") || upperLine.startsWith("HELO")) {
            await send(this.#responses["EHLO"]);
          } else if (upperLine.startsWith("MAIL FROM:")) {
            await send(this.#responses["MAIL"]);
          } else if (upperLine.startsWith("RCPT TO:")) {
            await send(this.#responses["RCPT"]);
          } else if (upperLine === "DATA") {
            await send(this.#responses["DATA"]);
            this.#logger.info("Begin to receive mail data...");
            rawMail = "";
          } else if (upperLine === "QUIT") {
            await send(this.#responses["QUIT"]);
            return;
          } else {
            this.#logger.warn("Smtp server command unrecognized:", line);
            await send(this.#responses["INVALID"]);
            return;
          }
        } else {
          if (line === ".") {
            try {
              this.#logger.info("Done receiving mail data, begin to relay...");
              const { message } = await this.#deliverer.deliverRaw(rawMail);
              await send(`250 2.6.0 ${message}`);
              rawMail = null;
              this.#logger.info("Done SMTP mail session.");
            } catch (err) {
              this.#logger.info(err);
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

  async serve(options: {
    hostname: string,
    port: number
  }) {
    const listener = Deno.listen(options);
    this.#responses = createResponses(options.hostname, options.port);
    this.#logger.info(
      `Dumb SMTP server starts running on ${this.#responses.serverName}.`,
    );

    for await (const conn of listener) {
      try {
        await this.#handleConnection(conn);
      } catch (cause) {
        this.#logger.error("One smtp connection session throws an error " + cause);
      }
    }
  }
}
