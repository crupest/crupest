import { Context } from "hono";

import { Env } from "../base.ts";

export function createReverseProxyHandler(
  { originServer }: { originServer: string },
) {
  return async (c: Context<Env>) => {
    const url = new URL(c.req.url);
    const { host, protocol } = url;

    let forwardedFor = c.req.header("x-forwarded-for");
    if (forwardedFor) forwardedFor += `, ${c.env.remoteAddr}`;
    else forwardedFor = c.env.remoteAddr;

    const connection = c.req.header("upgrade") ? "upgrade" : "close";

    url.protocol = "http:";
    url.host = originServer;

    return await fetch(url, {
      method: c.req.method,
      headers: {
        ...c.req.header(),
        "Connection": connection,
        "Host": host,
        "X-Forwarded-For": forwardedFor,
        "X-Forwarded-Host": host,
        "X-Forwarded-Proto": protocol.slice(0, -1),
        "X-Real-IP": c.env.remoteAddr,
      },
      body: c.req.raw.body,
      redirect: "manual",
    });
  };
}
