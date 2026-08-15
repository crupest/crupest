import { describe, it } from "@std/testing/bdd";
import { expect } from "@std/expect";

import { NULL_LOGGER } from "@crupest/base/log";

import { createHono } from "./app.ts";
import { MailDeliverer } from "./mail.ts";

describe("createHono", () => {
  it("reports healthy", async () => {
    const unusedDeliverer = null as unknown as MailDeliverer;
    const response = await createHono({
      logger: NULL_LOGGER,
      outbound: unusedDeliverer,
      inbound: unusedDeliverer,
    }).request("/health");

    expect(response.status).toBe(200);
    expect(await response.text()).toBe("OK");
  });
});
