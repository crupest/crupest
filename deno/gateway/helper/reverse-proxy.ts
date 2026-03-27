import { Context } from "hono";
import { getConnInfo } from "hono/deno";

function isWebSocketRequest(headers: Headers) {
  return headers.get("upgrade")?.toLowerCase() === "websocket";
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
      to.close(event.code, event.reason);
    }
  });
  from.addEventListener("error", () => {
    if (to.readyState === WebSocket.OPEN) {
      to.close(1011, "WebSocket error");
    }
  });
}

export function createReverseProxyHandler(
  { originServer }: { originServer: string },
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
      const forwardedFor = headers.get("x-forwarded-for");
      headers.set(
        "X-Forwarded-For",
        forwardedFor ? `${forwardedFor}, ${remoteAddr}` : remoteAddr,
      );
    }

    if (isWebSocket) {
      const { socket: downstreamSocket, response } = Deno.upgradeWebSocket(
        c.req.raw,
      );
      const upstreamSocket = new WebSocket(
        url.toString(),
        {
          headers,
        },
      );

      forwardWebSocket(downstreamSocket, upstreamSocket);
      forwardWebSocket(upstreamSocket, downstreamSocket);

      return response;
    }

    return await fetch(url, {
      method: c.req.method,
      headers,
      body: c.req.raw.body,
      redirect: "manual",
    });
  };
}
