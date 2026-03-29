/// <reference no-default-lib="true" />
/// <reference lib="esnext" />
/// <reference lib="deno.worker" />

import { Utils } from "../lib.ts";
import { getDefaultWorkerLogger } from "./worker.ts";

self.addEventListener("message", async (event: MessageEvent<string>) => {
  if (event.data === "start") {
    const logger = getDefaultWorkerLogger();
    await logger.info("msg-1");
    await Utils.delay(100);
    await logger.debug("msg-2");
    self.postMessage({ type: "done" });
    self.close();
  }
});
