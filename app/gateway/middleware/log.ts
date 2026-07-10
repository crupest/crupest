import type { RequestHandler } from "express";

export type LogWriter = (value: string) => Promise<void>;
export interface LogOptions {
  writer?: LogWriter;
}

function defaultLogWriter(value: string): Promise<void> {
  console.log(value);
  return Promise.resolve();
}

export function createLogMiddleware(options?: LogOptions): RequestHandler {
  const writer = options?.writer ?? defaultLogWriter;

  return (request, response, next) => {
    response.once("finish", () => {
      const remoteAddress = request.socket.remoteAddress ?? "unknown";
      const referer = request.header("referer") ?? "";
      const userAgent = request.header("user-agent") ?? "";
      const contentLength = response.getHeader("content-length") ?? "-1";
      const line = `${remoteAddress} - [${new Date().toISOString()}] "${
        request.method
      } ${request.originalUrl}" ${response.statusCode} ${String(
        contentLength,
      )} "${referer}" "${userAgent}"`;
      void writer(line);
    });
    next();
  };
}
