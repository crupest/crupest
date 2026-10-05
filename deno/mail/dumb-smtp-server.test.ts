import { describe, it } from "node:test";
import { expect } from "@std/expect";

import { NULL_LOGGER } from "@crupest/base/log";

import { DumbSmtpServer } from "./dumb-smtp-server.ts";
import { MailDeliverer } from "./mail.ts";

const CRLF = "\r\n";

function createDeliverer(): MailDeliverer {
  return {
    deliver: () =>
      Promise.resolve({ generateMessageForSmtp: () => "2.0.0 OK queued" }),
  } as unknown as MailDeliverer;
}

function sleep(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function findFreePort(): number {
  const listener = Deno.listen({ hostname: "127.0.0.1", port: 0 });
  const { port } = listener.addr as Deno.NetAddr;
  listener.close();
  return port;
}

function startServer() {
  const port = findFreePort();
  const server = new DumbSmtpServer(NULL_LOGGER, createDeliverer());
  const serving = server.serve({ hostname: "127.0.0.1", port });
  return { server, port, serving };
}

class SmtpClient {
  #conn: Deno.Conn;
  #reader: ReadableStreamDefaultReader<Uint8Array>;
  #writer: WritableStreamDefaultWriter<Uint8Array>;
  #decoder = new TextDecoder();
  #encoder = new TextEncoder();
  #buffer = "";

  constructor(conn: Deno.Conn) {
    this.#conn = conn;
    this.#reader = conn.readable.getReader();
    this.#writer = conn.writable.getWriter();
  }

  send(line: string) {
    return this.#writer.write(this.#encoder.encode(line + CRLF));
  }

  async readLine(): Promise<string> {
    while (true) {
      const index = this.#buffer.indexOf(CRLF);
      if (index !== -1) {
        const line = this.#buffer.slice(0, index);
        this.#buffer = this.#buffer.slice(index + CRLF.length);
        return line;
      }
      const { value, done } = await this.#reader.read();
      if (done) return this.#buffer;
      this.#buffer += this.#decoder.decode(value, { stream: true });
    }
  }

  /** Resolves to true once the server closes its side of the connection. */
  async waitForClose(timeoutMs: number): Promise<boolean> {
    return await Promise.race([
      this.#reader.read().then(({ done }) => done),
      sleep(timeoutMs).then(() => false),
    ]);
  }

  close() {
    try {
      this.#conn.close();
    } catch {
      // Already closed.
    }
  }
}

describe("DumbSmtpServer", () => {
  it("closes the connection after telling the client to reconnect", async () => {
    const { server, port, serving } = startServer();
    const client = new SmtpClient(
      await Deno.connect({ hostname: "127.0.0.1", port }),
    );

    try {
      await client.readLine(); // 220 greeting
      for (const command of [
        "EHLO test",
        "MAIL FROM:<a@b.c>",
        "RCPT TO:<d@e.f>",
        "DATA",
      ]) {
        await client.send(command);
        await client.readLine();
      }

      await client.send("hello");
      await client.send(".");
      await client.readLine(); // 250 accepted
      const closing = await client.readLine();
      expect(closing.startsWith("421")).toBe(true);

      expect(await client.waitForClose(2000)).toBe(true);
    } finally {
      client.close();
      server.close();
      await serving;
    }
  });

  it("accepts a new connection while another one is still open", async () => {
    const { server, port, serving } = startServer();
    const first = new SmtpClient(
      await Deno.connect({ hostname: "127.0.0.1", port }),
    );
    const second = new SmtpClient(
      await Deno.connect({ hostname: "127.0.0.1", port }),
    );

    try {
      // The first connection stays open after its greeting.
      await first.readLine();

      const greeting = await Promise.race([
        second.readLine(),
        sleep(2000).then(() => null),
      ]);
      expect(greeting?.startsWith("220")).toBe(true);
    } finally {
      first.close();
      second.close();
      server.close();
      await serving;
    }
  });
});
