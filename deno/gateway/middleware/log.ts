import { createMiddleware } from "hono/factory";
import { getConnInfo } from "hono/deno";

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

  return createMiddleware(async (c, next) => {
    // Nginx log format: log_format combined '$remote_addr - $remote_user [$time_local] '
    //                                       '"$request" $status $body_bytes_sent '
    //                                       '"$http_referer" "$http_user_agent"';
    // However, we don't have $remote_user and $body_bytes_sent, so we'll omit those.
    const remoteAddr = getConnInfo(c).remote.address ?? "unknown";
    const referer = c.req.header("referer") ?? "";
    const userAgent = c.req.header("user-agent") ?? "";

    const logStr = `${remoteAddr} - [${
      new Date().toISOString()
    }] "${c.req.method} ${c.req.url}" ${c.res.status} "${referer}" "${userAgent}"`;
    await writer(logStr);

    await next();
  });
}
