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
    ACTIVE_CLOSE: "421 4.7.0 Please open a new connection to send more emails",
    INVALID: "500 5.5.1 Error: command not recognized",
  } as const;
}

export class DumbSmtpServer {
  #deliverer;

  constructor(deliverer: MailDeliverer) {
    this.#deliverer = deliverer;
  }

  async #handleConnection(
    logTag: string,
    conn: Deno.Conn,
    responses: ReturnType<typeof createResponses>,
  ) {
    using disposeStack = new DisposableStack();
    disposeStack.defer(() => {
      console.info(logTag, "Close tcp connection.");
      conn.close();
    });

    console.info(logTag, "New tcp connection established.");

    const writer = conn.writable.getWriter();
    disposeStack.defer(() => writer.releaseLock());
    const reader = conn.readable.getReader();
    disposeStack.defer(() => reader.releaseLock());

    const [decoder, encoder] = [new TextDecoder(), new TextEncoder()];
    const decode = (data: Uint8Array) => decoder.decode(data);
    const send = async (s: string) => {
      console.info(logTag, "Send line:", s);
      await writer.write(encoder.encode(s + CRLF));
    };

    let buffer: string = "";
    let rawMail: string | null = null;

    await send(responses["READY"]);

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
          console.info(logTag, "Received line:", line);
          const upperLine = line.toUpperCase();
          if (upperLine.startsWith("EHLO") || upperLine.startsWith("HELO")) {
            await send(responses["EHLO"]);
          } else if (upperLine.startsWith("MAIL FROM:")) {
            await send(responses["MAIL"]);
          } else if (upperLine.startsWith("RCPT TO:")) {
            await send(responses["RCPT"]);
          } else if (upperLine === "DATA") {
            await send(responses["DATA"]);
            console.info(logTag, "Begin to receive mail data...");
            rawMail = "";
          } else if (upperLine === "QUIT") {
            await send(responses["QUIT"]);
            return;
          } else {
            await send(responses["INVALID"]);
            return;
          }
        } else {
          if (line === ".") {
            try {
              console.info(logTag, "Mail data received, begin to relay...");
              const result = await this.#deliverer.deliverRaw(rawMail);
              await send(`250 2.6.0 ${result.generateMessageForSmtp()}`);
              rawMail = null;
            } catch (err) {
              console.error(logTag, "Relay failed.", err);
              await send("554 5.3.0 Error: check server log");
            }
            await send(responses["ACTIVE_CLOSE"]);
          } else {
            const dataLine = line.startsWith("..") ? line.slice(1) : line;
            rawMail += dataLine + CRLF;
          }
        }
      }
    }
  }

  async serve(options: { hostname: string; port: number }) {
    const listener = Deno.listen(options);
    const responses = createResponses(options.hostname, options.port);
    console.info(
      `Dumb SMTP server starts to listen on ${responses.serverName}.`,
    );

    let counter = 1;

    for await (const conn of listener) {
      const logTag = `[outbound ${counter++}]`;
      try {
        await this.#handleConnection(logTag, conn, responses);
      } catch (cause) {
        console.error(logTag, "A JS error was thrown by handler:", cause);
      }
    }
  }
}
