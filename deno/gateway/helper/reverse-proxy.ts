import { Context } from "hono";
import { getConnInfo } from "hono/deno";

export function createReverseProxyHandler(
  { originServer }: { originServer: string },
) {
  return async (c: Context) => {
    const url = new URL(c.req.url);
    const { host, protocol } = url;
    const remoteAddr = getConnInfo(c).remote.address;

    url.protocol = "http:";
    url.host = originServer;

    const headers = new Headers(c.req.header());
    headers.set("Connection", headers.get("upgrade") ? "upgrade" : "close");
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

    return await fetch(url, {
      method: c.req.method,
      headers,
      body: c.req.raw.body,
      redirect: "manual",
    });
  };
}
