import { createMiddleware } from "hono/factory";

import { Env } from "../base.ts";

export type LogWriter = (str: string) => Promise<void>;
export interface LogOptions {
  writer?: LogWriter;
}

function defaultLogWriter(str: string): Promise<void> {
  console.log(str);
  return Promise.resolve();
}

export function createLogMiddleware(options?: LogOptions) {
  const writer = options?.writer ?? defaultLogWriter;

  return createMiddleware<Env>(async (c, next) => {
    // Nginx log format: log_format combined '$remote_addr - $remote_user [$time_local] '
    //                                       '"$request" $status $body_bytes_sent '
    //                                       '"$http_referer" "$http_user_agent"';
    // However, we don't have $remote_user and $body_bytes_sent, so we'll omit those.
    const referer = c.req.header("referer") ?? "";
    const userAgent = c.req.header("user-agent") ?? "";

    const logStr = `${c.env.remoteAddr} - [${
      new Date().toISOString()
    }] "${c.req.method} ${c.req.url}" ${c.res.status} "${referer}" "${userAgent}"`;
    await writer(logStr);

    await next();
  });
}
