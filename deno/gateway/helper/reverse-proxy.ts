import { Context } from "hono";
import { getConnInfo } from "hono/deno";

import { ILogger } from "@crupest/base/log";

function isWebSocketRequest(headers: Headers) {
  return headers.get("upgrade")?.toLowerCase() === "websocket";
}

function splitWebSocketProtocols(protocolHeader: string | null) {
  if (!protocolHeader) {
    return [];
  }
  return protocolHeader
    .split(",")
    .map((protocol) => protocol.trim())
    .filter((protocol) => protocol.length > 0);
}

type WebSocketData = string | Blob | ArrayBufferLike | ArrayBufferView;

function forwardWebSocket(from: WebSocket, to: WebSocket) {
  const queue: WebSocketData[] = [];
  from.addEventListener("message", (event) => {
    switch (to.readyState) {
      case WebSocket.OPEN:
        to.send(event.data);
        break;
      case WebSocket.CONNECTING:
        queue.push(event.data);
        break;
    }
  });
  to.addEventListener("open", () => {
    queue.forEach((data) => to.send(data));
    queue.length = 0;
  });
  from.addEventListener("close", (event) => {
    if (to.readyState === WebSocket.OPEN) {
      to.close(
        event.code === 1000 || event.code === 1001 ? 1000 : 4000,
        event.reason,
      );
    }
  });
  from.addEventListener("error", () => {
    if (to.readyState === WebSocket.OPEN) {
      to.close(4000, "WebSocket error");
    }
  });
}

export function createReverseProxyHandler(
  { originServer, logger }: { originServer: string; logger?: ILogger },
) {
  return async (c: Context) => {
    const url = new URL(c.req.url);
    const { host, protocol } = url;
    const remoteAddr = getConnInfo(c).remote.address;
    const headers = new Headers(c.req.header());
    const isWebSocket = isWebSocketRequest(headers);

    url.protocol = isWebSocket ? "ws:" : "http:";
    url.host = originServer;

    headers.set("Host", host);
    headers.set("X-Forwarded-Host", host);
    headers.set("X-Forwarded-Proto", protocol.slice(0, -1));
    if (remoteAddr) {
      headers.set("X-Real-IP", remoteAddr);
      // We should actually chain the IPs if we trust the proxy in front of deno gateway.
      // However, we're facing clients, so we don't trust and use the header, but just
      // overwrite it.
      //
      // ```typescript
      // const forwardedFor = headers.get("x-forwarded-for");
      // headers.set(
      //   "X-Forwarded-For",
      //   forwardedFor ? `${forwardedFor}, ${remoteAddr}` : remoteAddr,
      // );
      // ```
      headers.set("X-Forwarded-For", remoteAddr);
    }

    if (isWebSocket) {
      const wsProtocol = splitWebSocketProtocols(
        headers.get("sec-websocket-protocol"),
      );

      headers.delete("connection");
      headers.delete("upgrade");
      headers.delete("sec-websocket-key");
      headers.delete("sec-websocket-version");
      headers.delete("sec-websocket-extensions");
      headers.delete("sec-websocket-protocol");

      const { socket: downstreamSocket, response } = Deno.upgradeWebSocket(
        c.req.raw,
      );
      const upstreamSocket = new WebSocket(
        url.toString(),
        {
          protocols: wsProtocol,
          headers,
        },
      );

      forwardWebSocket(downstreamSocket, upstreamSocket);
      forwardWebSocket(upstreamSocket, downstreamSocket);

      return response;
    }

    try {
      return await fetch(url, {
        method: c.req.method,
        headers,
        body: c.req.raw.body,
        redirect: "manual",
      });
    } catch (e) {
      logger?.warn(`Upstream error to ${originServer}`, e);
      return new Response("Upstream error.", {
        status: 502,
      });
    }
  };
}
