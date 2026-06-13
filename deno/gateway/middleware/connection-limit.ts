import { createMiddleware } from "hono/factory";
import { Context } from "hono";

export interface ConnectionLimitOptions {
  maxConnections: number;
  /** Predicate to decide whether a URL path should count against the limit.
   *  Return true to count and limit, false to bypass. Default: always true. */
  shouldLimit?: (ctx: Context) => boolean;
}

export function createConnectionLimitMiddleware(
  options?: Partial<ConnectionLimitOptions>,
) {
  const { maxConnections, shouldLimit } = {
    maxConnections: 200,
    shouldLimit: (_ctx: Context) => true,
    ...options,
  };

  let activeConnections = 0;

  return createMiddleware(async (c, next) => {
    const limited = shouldLimit(c);

    if (limited && activeConnections >= maxConnections) {
      return c.text("Too Many Requests", { status: 429 });
    }

    if (limited) activeConnections++;
    try {
      await next();
    } finally {
      if (limited) activeConnections--;
    }
  });
}
