import { createServer, type Server, type Socket } from "node:net";

import type { ILogger } from "@crupest/base/log";

import type { MailDeliverer } from "./mail.js";

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
  #count = 1;
  readonly #logger: ILogger;
  readonly #deliverer: MailDeliverer;

  constructor(logger: ILogger, deliverer: MailDeliverer) {
    this.#logger = logger;
    this.#deliverer = deliverer;
  }

  async #handleConnection(
    logger: ILogger,
    socket: Socket,
    responses: ReturnType<typeof createResponses>,
  ): Promise<void> {
    logger.info("New tcp connection established.");
    socket.setEncoding("utf8");

    const send = (line: string): Promise<void> => {
      logger.info("Send line:", line);
      return new Promise((resolve, reject) => {
        socket.write(line + CRLF, (error) => {
          if (error == null) resolve();
          else reject(error);
        });
      });
    };

    let buffer = "";
    let rawMail: string | null = null;

    try {
      await send(responses.READY);

      for await (const chunk of socket) {
        buffer += String(chunk);

        while (true) {
          const eolPos = buffer.indexOf(CRLF);
          if (eolPos === -1) break;

          const line = buffer.slice(0, eolPos);
          buffer = buffer.slice(eolPos + CRLF.length);

          if (rawMail == null) {
            logger.info("Received line:", line);
            const upperLine = line.toUpperCase();
            if (upperLine.startsWith("EHLO") || upperLine.startsWith("HELO")) {
              await send(responses.EHLO);
            } else if (upperLine.startsWith("MAIL FROM:")) {
              await send(responses.MAIL);
            } else if (upperLine.startsWith("RCPT TO:")) {
              await send(responses.RCPT);
            } else if (upperLine === "DATA") {
              await send(responses.DATA);
              logger.info("Begin to receive mail data...");
              rawMail = "";
            } else if (upperLine === "QUIT") {
              await send(responses.QUIT);
              return;
            } else {
              await send(responses.INVALID);
              return;
            }
          } else if (line === ".") {
            try {
              logger.info("Mail data received, begin to relay...");
              const result = await this.#deliverer.deliver({ mail: rawMail });
              await send(`250 2.6.0 ${result.generateMessageForSmtp()}`);
            } catch (error) {
              logger.error("Relay failed.", error);
              await send("554 5.3.0 Error: check server log");
            }
            await send(responses.ACTIVE_CLOSE);
            return;
          } else {
            const dataLine = line.startsWith("..") ? line.slice(1) : line;
            rawMail += dataLine + CRLF;
          }
        }
      }
    } finally {
      logger.info("Close tcp connection.");
      socket.end();
    }
  }

  serve(options: { hostname: string; port: number }): Server {
    const responses = createResponses(options.hostname, options.port);
    const server = createServer((socket) => {
      const logger = this.#logger.withDefaultTag(`outbound ${this.#count++}`);
      void this.#handleConnection(logger, socket, responses).catch((error) => {
        logger.error("A JS error was thrown by handler:", error);
        socket.destroy();
      });
    });

    server.listen(options.port, options.hostname, () => {
      this.#logger.info(
        `Dumb SMTP server starts to listen on ${responses.serverName}.`,
      );
    });
    return server;
  }
}
