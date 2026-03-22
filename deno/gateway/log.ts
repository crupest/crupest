import { createMiddleware } from "hono/factory";

export type PrintFunc = (str: string) => void | Promise<void>;
export interface LogOptions {
  printFunc?: PrintFunc;
}

export function createLogMiddleware(options?: Partial<LogOptions>) {
  const print = options?.printFunc ?? console.log;

  return createMiddleware(async (c, next) => {
    const start = Date.now();
    await next();
    const ms = Date.now() - start;
    const logStr = `${c.req.method} ${c.req.url} ${c.res.status} - ${
      c.req.header("user-agent") ?? ""
    } - ${ms}ms`;
    await print(logStr);
  });
}
