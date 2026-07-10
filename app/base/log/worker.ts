import { parentPort } from "node:worker_threads";

import {
  DefaultLogFormatter,
  type FormattedLogEntry,
  type ILogWriter,
  Logger,
} from "./common.js";

export class WorkerLogWriter implements ILogWriter {
  write(entry: FormattedLogEntry): Promise<void> {
    parentPort?.postMessage({ type: "log", entry });
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
