/// <reference no-default-lib="true" />
/// <reference lib="esnext" />
/// <reference lib="deno.worker" />

import {
  DefaultLogFormatter,
  type FormattedLogEntry,
  type ILogWriter,
  Logger,
} from "./common.ts";

export class WorkerLogWriter implements ILogWriter {
  write(entry: FormattedLogEntry): Promise<void> {
    self.postMessage({ type: "log", entry });
    return Promise.resolve();
  }
}

let defaultWorkerLogger: Logger | null = null;

export function getDefaultWorkerLogger(): Logger {
  if (!defaultWorkerLogger) {
    defaultWorkerLogger = new Logger({
      formatter: new DefaultLogFormatter(false),
      writer: new WorkerLogWriter(),
    });
  }
  return defaultWorkerLogger;
}
