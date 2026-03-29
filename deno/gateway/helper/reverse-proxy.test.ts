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
});
