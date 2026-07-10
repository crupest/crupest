import { parentPort } from "node:worker_threads";

import { Utils } from "../lib.js";
import { getDefaultWorkerLogger } from "./worker.js";

parentPort?.on("message", async (message: string) => {
  if (message === "start") {
    const logger = getDefaultWorkerLogger();
    await logger.info("msg-1");
    await Utils.delay(100);
    await logger.debug("msg-2");
    parentPort?.postMessage({ type: "done" });
    parentPort?.close();
  }
});
