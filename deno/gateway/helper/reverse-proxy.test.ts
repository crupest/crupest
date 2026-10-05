import { describe, it } from "@std/testing/bdd";
import { expect } from "@std/expect";
import { Hono } from "hono";

import { createReverseProxyHandler } from "./reverse-proxy.ts";

function waitForOpen(socket: WebSocket) {
  return new Promise<void>((resolve, reject) => {
    socket.addEventListener("open", () => resolve(), { once: true });
    socket.addEventListener(
      "error",
      () => reject(new Error("websocket failed to open")),
      { once: true },
    );
  });
}

function waitForMessage(socket: WebSocket) {
  return new Promise<MessageEvent>((resolve, reject) => {
    socket.addEventListener("message", (event) => resolve(event), {
      once: true,
    });
    socket.addEventListener(
      "error",
      () => reject(new Error("websocket error before message")),
      { once: true },
    );
    socket.addEventListener(
      "close",
      () => reject(new Error("websocket closed before message")),
      { once: true },
    );
  });
}

function sleep(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

describe("createReverseProxyHandler", () => {
  it("proxies websocket messages and forwards custom headers", async () => {
    const upstreamAbort = new AbortController();
    let upstreamAuthorization;
    let upstreamXTest;

    const upstreamServer = Deno.serve(
      {
        hostname: "127.0.0.1",
        port: 0,
        signal: upstreamAbort.signal,
        onListen: () => {},
      },
      async (request: Request) => {
        upstreamAuthorization = request.headers.get("authorization");
        upstreamXTest = request.headers.get("x-test");
        const { socket, response } = Deno.upgradeWebSocket(request);
        socket.addEventListener("message", (event) => {
          socket.send(`upstream:${String(event.data)}`);
        });
        return await Promise.resolve(response);
      },
    );

    const proxyAbort = new AbortController();
    const proxyApp = new Hono();
    proxyApp.all(
      "/ws",
      createReverseProxyHandler({
        originServer:
          `${upstreamServer.addr.hostname}:${upstreamServer.addr.port}`,
      }),
    );

    const proxyServer = Deno.serve(
      {
        signal: proxyAbort.signal,
        hostname: "127.0.0.1",
        port: 0,
        onListen: () => {},
      },
      proxyApp.fetch,
    );

    try {
      const client = new WebSocket(
        `ws://127.0.0.1:${proxyServer.addr.port}/ws`,
        {
          protocols: ["chat"],
          headers: {
            Authorization: "Bearer test-token",
            "X-Test": "from-client",
          },
        },
      );

      await waitForOpen(client);
      client.send("hello");
      const event = await waitForMessage(client);
      expect(event.data).toBe("upstream:hello");
      expect(upstreamAuthorization).toBe("Bearer test-token");
      expect(upstreamXTest).toBe("from-client");
      client.close(1000, "done");
    } finally {
      proxyAbort.abort();
      upstreamAbort.abort();
      await Promise.all([proxyServer.finished, upstreamServer.finished]);
    }
  });

  it("closes the upstream socket when the client leaves before it connects", async () => {
    // Upstream that accepts TCP but never answers the WebSocket handshake, so
    // the proxy's upstream socket stays in CONNECTING.
    const rawListener = Deno.listen({ hostname: "127.0.0.1", port: 0 });
    const upstreamConns: Deno.Conn[] = [];
    let markUpstreamClosed!: () => void;
    const upstreamClosed = new Promise<void>((resolve) => {
      markUpstreamClosed = resolve;
    });
    const acceptLoop = (async () => {
      for await (const conn of rawListener) {
        upstreamConns.push(conn);
        void (async () => {
          const reader = conn.readable.getReader();
          try {
            while (!(await reader.read()).done) {
              // Drain the handshake request but never reply.
            }
          } catch {
            // Ignore.
          } finally {
            try {
              conn.close();
            } catch {
              // Ignore.
            }
            markUpstreamClosed();
          }
        })();
      }
    })();

    const proxyAbort = new AbortController();
    const proxyApp = new Hono();
    proxyApp.all(
      "/ws",
      createReverseProxyHandler({
        originServer: `127.0.0.1:${(rawListener.addr as Deno.NetAddr).port}`,
      }),
    );
    const proxyServer = Deno.serve(
      {
        hostname: "127.0.0.1",
        port: 0,
        signal: proxyAbort.signal,
        onListen: () => {},
      },
      proxyApp.fetch,
    );

    const client = await Deno.connect({
      hostname: "127.0.0.1",
      port: proxyServer.addr.port,
    });

    try {
      await client.write(
        new TextEncoder().encode(
          "GET /ws HTTP/1.1\r\n" +
            "Host: 127.0.0.1\r\n" +
            "Upgrade: websocket\r\n" +
            "Connection: Upgrade\r\n" +
            "Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==\r\n" +
            "Sec-WebSocket-Version: 13\r\n\r\n",
        ),
      );

      // Wait until the proxy has dialed the upstream.
      for (let i = 0; i < 100 && upstreamConns.length === 0; i++) {
        await sleep(10);
      }
      expect(upstreamConns.length).toBeGreaterThan(0);

      // The downstream client leaves before the upstream handshake resolves.
      client.close();

      const released = await Promise.race([
        upstreamClosed.then(() => true),
        sleep(2000).then(() => false),
      ]);
      expect(released).toBe(true);
    } finally {
      try {
        client.close();
      } catch {
        // Already closed.
      }
      for (const conn of upstreamConns) {
        try {
          conn.close();
        } catch {
          // Already closed.
        }
      }
      rawListener.close();
      proxyAbort.abort();
      await proxyServer.finished;
      await acceptLoop;
    }
  });
});
