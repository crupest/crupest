import { describe, it } from "@std/testing/bdd";
import { expect } from "@std/expect";
import { Hono } from "hono";

import { createConnectionLimitMiddleware } from "./connection-limit.ts";
import { Utils } from "@crupest/base";

interface Req {
  received: Promise<void>;
  receivedResolve: () => void;
  responded: Promise<void>;
  respondResolve: () => void;
}

function setup(
  options: Parameters<typeof createConnectionLimitMiddleware>[0],
) {
  const app = new Hono();
  app.use("*", createConnectionLimitMiddleware(options));

  const pendingMap = new Map<string, Req>();

  app.all("/test", async (c) => {
    const key = c.req.query("key");
    if (key) {
      const pending = pendingMap.get(key);
      if (pending == null) {
        const [responded, respondResolve] = Utils.promise<void>();
        pendingMap.set(key, {
          received: Promise.resolve(),
          receivedResolve: () => {},
          responded,
          respondResolve,
        });
        await responded;
      } else {
        pending.receivedResolve();
        await pending.responded;
      }
    }
    return c.text("ok");
  });

  const abort = new AbortController();
  const server = Deno.serve(
    {
      hostname: "127.0.0.1",
      port: 0,
      signal: abort.signal,
      onListen: () => {},
    },
    app.fetch,
  );
  const origin = `http://127.0.0.1:${server.addr.port}`;

  let seq = 0;
  function get(pending = true) {
    const key = String(seq++);
    const res = fetch(`${origin}/test?key=${key}`);
    const waitForReceived = async () => {
      const req = pendingMap.get(key);
      if (req == null) {
        const [received, receivedResolve] = Utils.promise<void>();
        const [responded, respondResolve] = Utils.promise<void>();
        pendingMap.set(key, {
          received,
          receivedResolve,
          responded,
          respondResolve,
        });
        await received;
      } else {
        await req.received;
      }
    };

    const respond = async () => {
      await waitForReceived();
      pendingMap.get(key)!.respondResolve();
    };

    if (!pending) {
      respond();
    }

    return {
      waitForReceived,
      respond,
      res,
    };
  }

  return {
    origin,
    get,
    async [Symbol.asyncDispose]() {
      abort.abort();
      await server.finished;
    },
  };
}

describe("createConnectionLimitMiddleware", () => {
  it("allows requests under the limit", async () => {
    await using ctx = setup({ maxConnections: 3 });

    const r1 = ctx.get();
    r1.respond();
    const res = await r1.res;
    expect(res.status).toBe(200);
    expect(await res.text()).toBe("ok");
  });

  it("rejects requests over the limit with 429", async () => {
    await using ctx = setup({ maxConnections: 1 });

    // First request blocks the single slot
    const r1 = ctx.get();
    await r1.waitForReceived();

    // Second request should be rejected immediately
    const r2 = ctx.get(false);
    const res2 = await r2.res;
    expect(res2.status).toBe(429);
    expect(await res2.text()).toBe("Too Many Requests");

    // Clean up
    r1.respond();
    const res1 = await r1.res;
    expect(res1.status).toBe(200);
    expect(await res1.text()).toBe("ok");
  });

  it("rejects requests over the limit (>= 2) with 429", async () => {
    await using ctx = setup({ maxConnections: 2 });

    // First request blocks the single slot
    const r1 = ctx.get();
    await r1.waitForReceived();
    const r2 = ctx.get();
    await r2.waitForReceived();

    // Second request should be rejected immediately
    const r3 = ctx.get(false);
    const res3 = await r3.res;
    expect(res3.status).toBe(429);
    expect(await res3.text()).toBe("Too Many Requests");

    // Clean up
    r1.respond();
    const res1 = await r1.res;
    expect(res1.status).toBe(200);
    expect(await res1.text()).toBe("ok");

    r2.respond();
    const res2 = await r2.res;
    expect(res2.status).toBe(200);
    expect(await res2.text()).toBe("ok");
  });

  it("lets a new request through after a previous one completes", async () => {
    await using ctx = setup({ maxConnections: 1 });

    // Grab the single slot
    const r1 = ctx.get(false);
    const res1 = await r1.res;
    expect(res1.status).toBe(200);
    expect(await res1.text()).toBe("ok");

    const r2 = ctx.get(false);
    const res2 = await r2.res;
    expect(res2.status).toBe(200);
    expect(await res2.text()).toBe("ok");
  });

  it("bypasses limit when shouldLimit returns false", async () => {
    await using ctx = setup({
      maxConnections: 1,
      shouldLimit: (c) => {
        return c.req.path !== "/test";
      },
    });

    // Should bypass — path is /test
    const r1 = ctx.get();
    const r2 = ctx.get(false);
    const res2 = await r2.res;
    expect(res2.status).toBe(200);
    expect(await res2.text()).toBe("ok");

    r1.respond();
    const res1 = await r1.res;
    expect(res1.status).toBe(200);
    expect(await res1.text()).toBe("ok");
  });
});
