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
    await next();

    // Nginx log format: log_format combined '$remote_addr - $remote_user [$time_local] '
    //                                       '"$request" $status $body_bytes_sent '
    //                                       '"$http_referer" "$http_user_agent"';
    // However, we don't have $remote_user, so we'll omit that.
    // For $body_bytes_sent, we can't get real sent bytes, so we'll use the Content-Length header if available.
    const remoteAddr = getConnInfo(c).remote.address ?? "unknown";
    const referer = c.req.header("referer") ?? "";
    const userAgent = c.req.header("user-agent") ?? "";
    const contentLength = c.res.headers.get("content-length") ?? "-1";

    const logStr = `${remoteAddr} - [${
      new Date().toISOString()
    }] "${c.req.method} ${c.req.url}" ${c.res.status} ${contentLength} "${referer}" "${userAgent}"`;
    await writer(logStr);
  });
}
