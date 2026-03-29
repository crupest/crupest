import { describe, it } from "@std/testing/bdd";
import { expect } from "@std/expect";

import { Utils } from "../lib.ts";
import {
  DefaultLogFormatter,
  type FormattedLogEntry,
  installLogHandlerForWorker,
  Logger,
  SynchronousLogWriterWrapper,
} from "./index.ts";

class MockLogWriter {
  messages: string[] = [];

  write(entry: FormattedLogEntry): Promise<void> {
    this.messages.push(entry.message);
    return Promise.resolve();
  }
}

class MockDelayLogWriter {
  messages: string[] = [];
  maxInFlight = 0;
  #inFlight = 0;

  async write(entry: FormattedLogEntry): Promise<void> {
    this.#inFlight++;
    this.maxInFlight = Math.max(this.maxInFlight, this.#inFlight);

    const index = Number(entry.message.slice("msg-".length));
    await Utils.delay((4 - index) * 2);

    this.messages.push(entry.message);
    this.#inFlight--;
  }
}

describe("SynchronousLogWriterWrapper", () => {
  it("writes all messages and preserves queue order", async () => {
    const mockWriter = new MockDelayLogWriter();
    const writer = new SynchronousLogWriterWrapper(mockWriter);

    const writes = Array.from(
      { length: 5 },
      (_, i) =>
        writer.write({
          level: "info",
          time: new Date(),
          tag: "test",
          message: `msg-${i}`,
        }),
    );

    await Promise.all(writes);

    expect(mockWriter.messages).toEqual([
      "msg-0",
      "msg-1",
      "msg-2",
      "msg-3",
      "msg-4",
    ]);
    expect(mockWriter.maxInFlight).toBe(1);
  });
});

describe("worker logger", () => {
  it("forwards worker logs to main-thread logger with a real worker", async () => {
    const writer = new MockLogWriter();
    const logger = new Logger({
      formatter: new DefaultLogFormatter(false),
      writer,
    });
    const worker = new Worker(
      new URL("./test-worker.ts", import.meta.url).href,
      {
        type: "module",
      },
    );
    installLogHandlerForWorker(worker, logger);

    const donePromise = new Promise<void>((resolve) => {
      worker.addEventListener(
        "message",
        (event: MessageEvent<{ type?: string }>) => {
          if (typeof event.data === "object" && event.data?.type === "done") {
            resolve();
          }
        },
      );
    });

    try {
      worker.postMessage("start");
      await donePromise;
      expect(writer.messages).toHaveLength(2);
      expect(writer.messages[0]).toBe("msg-1");
      expect(writer.messages[1]).toBe("msg-2");
    } finally {
      worker.terminate();
    }
  });
});
