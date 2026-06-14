import { createMiddleware } from "hono/factory";
import { Context } from "hono";
import { HTTPException } from "hono/http-exception";

export interface ConnectionLimitOptions {
  maxConnections: number;
  /** Predicate to decide whether a URL path should count against the limit.
   *  Return true to count and limit, false to bypass. Default: always true. */
  shouldLimit?: (ctx: Context) => boolean;
}

export function createConnectionLimitMiddleware(
  options?: Partial<ConnectionLimitOptions>,
) {
  const maxConnections = options?.maxConnections ?? 10;
  const shouldLimit = options?.shouldLimit;

  let activeConnections = 0;

  return createMiddleware(async (c, next) => {
    const limited = shouldLimit?.(c) ?? true;

    if (limited) {
      if (activeConnections >= maxConnections) {
        throw new HTTPException(429, { message: "Too Many Requests" });
      }

      activeConnections++;
      try {
        await next();
      } finally {
        activeConnections--;
      }
    } else {
      await next();
    }
  });
}
