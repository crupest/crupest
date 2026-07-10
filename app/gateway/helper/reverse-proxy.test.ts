import { once } from "node:events";
import { createServer } from "node:http";
import type { AddressInfo } from "node:net";

import express from "express";
import { describe, expect, it } from "vitest";
import WebSocket, { WebSocketServer } from "ws";

import { createReverseProxy } from "./reverse-proxy.js";

function getHeaderValue(
  value: string | string[] | undefined,
): string | undefined {
  if (typeof value === "string") return value;
  return value?.join(", ");
}

describe("createReverseProxy", () => {
  it("proxies HTTP requests and responses with forwarding headers", async () => {
    let upstreamPath: string | undefined;
    let upstreamXForwardedFor: string | undefined;
    let upstreamXForwardedHost: string | undefined;
    let upstreamXForwardedProto: string | undefined;

    const upstreamServer = createServer((request, response) => {
      upstreamPath = request.url;
      upstreamXForwardedFor = getHeaderValue(
        request.headers["x-forwarded-for"],
      );
      upstreamXForwardedHost = getHeaderValue(
        request.headers["x-forwarded-host"],
      );
      upstreamXForwardedProto = getHeaderValue(
        request.headers["x-forwarded-proto"],
      );
      response.writeHead(201, {
        "Content-Type": "text/plain; charset=utf-8",
        "X-Upstream": "yes",
      });
      response.end("proxied");
    });
    upstreamServer.listen(0, "127.0.0.1");
    await once(upstreamServer, "listening");
    const upstreamAddress = upstreamServer.address() as AddressInfo;

    const proxy = createReverseProxy({
      originServer: `127.0.0.1:${upstreamAddress.port}`,
    });
    const proxyApp = express();
    proxyApp.use(proxy.middleware);
    const proxyServer = createServer(proxyApp);
    proxyServer.listen(0, "127.0.0.1");
    await once(proxyServer, "listening");
    const proxyAddress = proxyServer.address() as AddressInfo;

    try {
      const response = await fetch(
        `http://127.0.0.1:${proxyAddress.port}/api?value=1`,
        {
          headers: {
            "X-Forwarded-For": "203.0.113.10",
          },
        },
      );

      expect(response.status).toBe(201);
      expect(response.headers.get("x-upstream")).toBe("yes");
      expect(await response.text()).toBe("proxied");
      expect(upstreamPath).toBe("/api?value=1");
      expect(upstreamXForwardedFor).toBe("203.0.113.10, 127.0.0.1");
      expect(upstreamXForwardedHost).toBe(`127.0.0.1:${proxyAddress.port}`);
      expect(upstreamXForwardedProto).toBe("http");
    } finally {
      proxyServer.close();
      upstreamServer.close();
      await Promise.all([
        once(proxyServer, "close"),
        once(upstreamServer, "close"),
      ]);
    }
  });

  it("proxies websocket messages and forwards custom headers", async () => {
    let upstreamAuthorization: string | undefined;
    let upstreamXTest: string | undefined;

    const upstreamServer = createServer();
    const upstreamWebSocket = new WebSocketServer({ noServer: true });
    upstreamServer.on("upgrade", (request, socket, head) => {
      upstreamAuthorization = request.headers.authorization;
      upstreamXTest = request.headers["x-test"] as string | undefined;
      upstreamWebSocket.handleUpgrade(request, socket, head, (webSocket) => {
        upstreamWebSocket.emit("connection", webSocket, request);
      });
    });
    upstreamWebSocket.on("connection", (socket) => {
      socket.on("message", (data) => {
        socket.send(`upstream:${String(data)}`);
      });
    });
    upstreamServer.listen(0, "127.0.0.1");
    await once(upstreamServer, "listening");
    const upstreamAddress = upstreamServer.address() as AddressInfo;

    const proxy = createReverseProxy({
      originServer: `127.0.0.1:${upstreamAddress.port}`,
    });
    const proxyApp = express();
    proxyApp.use(proxy.middleware);
    const proxyServer = createServer(proxyApp);
    proxyServer.on("upgrade", proxy.upgrade);
    proxyServer.listen(0, "127.0.0.1");
    await once(proxyServer, "listening");
    const proxyAddress = proxyServer.address() as AddressInfo;

    try {
      const client = new WebSocket(
        `ws://127.0.0.1:${proxyAddress.port}/ws`,
        ["chat"],
        {
          headers: {
            Authorization: "Bearer test-token",
            "X-Test": "from-client",
          },
        },
      );

      await once(client, "open");
      client.send("hello");
      const [data] = await once(client, "message");
      expect(String(data)).toBe("upstream:hello");
      expect(upstreamAuthorization).toBe("Bearer test-token");
      expect(upstreamXTest).toBe("from-client");
      client.close(1000, "done");
    } finally {
      proxyServer.close();
      upstreamWebSocket.close();
      upstreamServer.close();
      await Promise.all([
        once(proxyServer, "close"),
        once(upstreamServer, "close"),
      ]);
    }
  });
});
