import type { Request, RequestHandler } from "express";

export interface ConnectionLimitOptions {
  maxConnections: number;
  shouldLimit?: (request: Request) => boolean;
}

export function createConnectionLimitMiddleware(
  options?: Partial<ConnectionLimitOptions>,
): RequestHandler {
  const maxConnections = options?.maxConnections ?? 10;
  const shouldLimit = options?.shouldLimit;
  let activeConnections = 0;

  return (request, response, next) => {
    const limited = shouldLimit?.(request) ?? true;
    if (!limited) {
      next();
      return;
    }

    if (activeConnections >= maxConnections) {
      response.status(429).send("Too Many Requests");
      return;
    }

    activeConnections++;
    let released = false;
    const release = () => {
      if (released) return;
      released = true;
      activeConnections--;
    };
    response.once("finish", release);
    response.once("close", release);
    next();
  };
}
