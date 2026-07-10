import { once } from "node:events";
import { createServer, type Server } from "node:http";
import type { AddressInfo } from "node:net";

import express from "express";
import { describe, expect, it } from "vitest";

import { Utils } from "@crupest/base";

import { createConnectionLimitMiddleware } from "./connection-limit.js";

interface RequestState {
  received: Promise<void>;
  receivedResolve: () => void;
  responded: Promise<void>;
  respondResolve: () => void;
}

async function setup(
  options: Parameters<typeof createConnectionLimitMiddleware>[0],
) {
  const app = express();
  app.use(createConnectionLimitMiddleware(options));

  const requestStateMap = new Map<string, RequestState>();
  app.all("/test", async (request, response) => {
    const key = typeof request.query.key === "string" ? request.query.key : "";
    if (key.length > 0) {
      const state = requestStateMap.get(key);
      if (state == null) {
        const [responded, respondResolve] = Utils.promise<void>();
        requestStateMap.set(key, {
          received: Promise.resolve(),
          receivedResolve: () => {},
          responded,
          respondResolve,
        });
        await responded;
      } else {
        state.receivedResolve();
        await state.responded;
      }
    }
    response.send("ok");
  });

  const server: Server = createServer(app);
  server.listen(0, "127.0.0.1");
  await once(server, "listening");
  const address = server.address() as AddressInfo;
  const origin = `http://127.0.0.1:${address.port}`;

  let sequence = 0;
  function get(pending = true) {
    const key = String(sequence++);
    const response = fetch(`${origin}/test?key=${key}`);

    const waitForReceived = async () => {
      const state = requestStateMap.get(key);
      if (state == null) {
        const [received, receivedResolve] = Utils.promise<void>();
        const [responded, respondResolve] = Utils.promise<void>();
        requestStateMap.set(key, {
          received,
          receivedResolve,
          responded,
          respondResolve,
        });
        await received;
      } else {
        await state.received;
      }
    };

    const respond = async () => {
      await waitForReceived();
      requestStateMap.get(key)!.respondResolve();
    };

    if (!pending) void respond();
    return { waitForReceived, respond, response };
  }

  return {
    get,
    async close() {
      server.close();
      await once(server, "close");
    },
  };
}

describe("createConnectionLimitMiddleware", () => {
  it("allows requests under the limit", async () => {
    const context = await setup({ maxConnections: 3 });
    try {
      const request = context.get();
      void request.respond();
      const response = await request.response;
      expect(response.status).toBe(200);
      expect(await response.text()).toBe("ok");
    } finally {
      await context.close();
    }
  });

  it("rejects requests over the limit with 429", async () => {
    const context = await setup({ maxConnections: 1 });
    try {
      const first = context.get();
      await first.waitForReceived();

      const second = context.get(false);
      const secondResponse = await second.response;
      expect(secondResponse.status).toBe(429);
      expect(await secondResponse.text()).toBe("Too Many Requests");

      void first.respond();
      expect((await first.response).status).toBe(200);
    } finally {
      await context.close();
    }
  });

  it("lets a new request through after a previous one completes", async () => {
    const context = await setup({ maxConnections: 1 });
    try {
      expect((await context.get(false).response).status).toBe(200);
      expect((await context.get(false).response).status).toBe(200);
    } finally {
      await context.close();
    }
  });

  it("bypasses limit when shouldLimit returns false", async () => {
    const context = await setup({
      maxConnections: 1,
      shouldLimit: (request) => request.path !== "/test",
    });
    try {
      const first = context.get();
      const second = context.get(false);
      expect((await second.response).status).toBe(200);
      void first.respond();
      expect((await first.response).status).toBe(200);
    } finally {
      await context.close();
    }
  });
});
