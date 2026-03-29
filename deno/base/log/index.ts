import type { Writer, WriterSync } from "@std/io";
import { TaskScheduler } from "../task.ts";

import {
  DefaultLogFormatter,
  type FormattedLogEntry,
  type ILogger,
  type ILogWriter,
  Logger,
  type LogLevel,
} from "./common.ts";

export * from "./common.ts";

export type AnyWriter = (Writer | WriterSync) & { isTerminal?: () => boolean };
export type WriterMap = {
  [key in LogLevel]: { writer: AnyWriter; forceColor?: boolean | null };
};

const DEFAULT_WRITERS: WriterMap = {
  debug: { writer: Deno.stdout },
  info: { writer: Deno.stdout },
  warn: { writer: Deno.stderr },
  error: { writer: Deno.stderr },
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
    if ("write" in writer) {
      await writer.write(data);
    } else {
      writer.writeSync(data);
    }
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
  worker.addEventListener(
    "message",
    ({ data }: MessageEvent<{ type: "log"; entry: FormattedLogEntry }>) => {
      if (typeof data === "object" && data.type === "log") {
        const { message, ...rest } = data.entry;
        logger.log({ ...rest, args: [message] });
      }
    },
  );
}
