import type { Writable } from "node:stream";
import type { Worker } from "node:worker_threads";

import { TaskScheduler } from "../task.js";

import {
  DefaultLogFormatter,
  type FormattedLogEntry,
  type ILogger,
  type ILogWriter,
  Logger,
  type LogLevel,
} from "./common.js";

export * from "./common.js";

export type AnyWriter = Writable;
export type WriterMap = {
  [key in LogLevel]: { writer: AnyWriter; forceColor?: boolean | null };
};

const DEFAULT_WRITERS: WriterMap = {
  debug: { writer: process.stdout },
  info: { writer: process.stdout },
  warn: { writer: process.stderr },
  error: { writer: process.stderr },
};

export class WriterLogWriter implements ILogWriter {
  #writers: WriterMap;
  #textEncoder = new TextEncoder();

  constructor(writers: WriterMap = DEFAULT_WRITERS) {
    this.#writers = writers;
  }

  async write(entry: FormattedLogEntry): Promise<void> {
    const { writer } = this.#writers[entry.level];
    const data = this.#textEncoder.encode(entry.message + "\n");
    await new Promise<void>((resolve, reject) => {
      writer.write(data, (error) =>
        error == null ? resolve() : reject(error),
      );
    });
  }
}

export class SynchronousLogWriterWrapper implements ILogWriter {
  #writer: ILogWriter;
  #scheduler: TaskScheduler;

  constructor(writer: ILogWriter, maxConcurrentWrites = 1) {
    this.#writer = writer;
    this.#scheduler = new TaskScheduler(maxConcurrentWrites);
  }

  write(entry: FormattedLogEntry): Promise<void> {
    return this.#scheduler.queue(() => this.#writer.write(entry));
  }
}

let defaultLogger: Logger | null = null;

export function getDefaultLogger(): Logger {
  if (!defaultLogger) {
    defaultLogger = new Logger({
      formatter: new DefaultLogFormatter(),
      writer: new SynchronousLogWriterWrapper(new WriterLogWriter()),
    });
  }
  return defaultLogger;
}

export function installLogHandlerForWorker(worker: Worker, logger: ILogger) {
  worker.on("message", (data: { type?: string; entry?: FormattedLogEntry }) => {
    if (data.type === "log" && data.entry != null) {
      const { message, ...rest } = data.entry;
      logger.log({ ...rest, args: [message] });
    }
  });
}
