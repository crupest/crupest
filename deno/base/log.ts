import { join } from "@std/path";

import { toFileNameString } from "./date.ts";

export type LogLevel = "error" | "warn" | "info";

export interface LogEntry {
  content: [unknown, ...unknown[]];
  level?: LogLevel;
  cause?: unknown;
}

export interface LogEntryBuilder {
  withLevel(level: LogLevel): LogEntryBuilder;
  withCause(cause: unknown): LogEntryBuilder;
  setError(error: boolean): LogEntryBuilder;
  write(): void;
}

export interface ExternalLogStream extends Disposable {
  stream: WritableStream;
}

export class Logger {
  #indentSize = 2;
  #externalLogDir?: string;

  #contextStack: { depth: number; level: LogLevel }[] = [
    { depth: 0, level: "info" },
  ];

  get #context() {
    return this.#contextStack.at(-1)!;
  }

  get indentSize() {
    return this.#indentSize;
  }

  set indentSize(value: number) {
    this.#indentSize = value;
  }

  get externalLogDir() {
    return this.#externalLogDir;
  }

  set externalLogDir(value: string | undefined) {
    this.#externalLogDir = value;
    if (value != null) {
      Deno.mkdirSync(value, {
        recursive: true,
      });
    }
  }

  write(entry: LogEntry): void {
    const { content, level, cause } = entry;
    const [message, ...rest] = content;
    console[level ?? this.#context.level](
      " ".repeat(this.#indentSize * this.#context.depth) + String(message),
      ...(cause != null ? [cause, ...rest] : rest),
    );
  }

  push(entry: LogEntry): Disposable {
    this.write(entry);
    this.#contextStack.push({
      depth: this.#context.depth + 1,
      level: entry.level ?? this.#context.level,
    });
    return {
      [Symbol.dispose]: () => {
        this.#contextStack.pop();
      },
    };
  }

  info(message: unknown, ...args: unknown[]) {
    this.write({ level: "info", content: [message, ...args] });
  }

  warn(message: unknown, ...args: unknown[]) {
    this.write({ level: "warn", content: [message, ...args] });
  }

  error(message: unknown, ...args: unknown[]) {
    this.write({ level: "error", content: [message, ...args] });
  }

  builder(message: unknown, ...args: unknown[]): LogEntryBuilder {
    const entry: LogEntry = {
      content: [message, ...args],
      level: "info",
      cause: undefined,
    };
    const builder: LogEntryBuilder = {
      withCause: (cause) => {
        entry.cause = cause;
        return builder;
      },
      withLevel: (level) => {
        entry.level = level;
        return builder;
      },
      setError: (error) => {
        if (error) entry.level = "error";
        return builder;
      },
      write: () => {
        this.write(entry);
      },
    };
    return builder;
  }

  async createExternalLogStream(
    name: string,
    options?: {
      noTime?: boolean;
    },
  ): Promise<ExternalLogStream> {
    if (name.includes("/")) {
      throw new Error(`External log stream's name (${name}) contains '/'.`);
    }
    if (this.#externalLogDir == null) {
      throw new Error("External log directory is not set.");
    }

    const logPath = join(
      this.#externalLogDir,
      options?.noTime === true
        ? name
        : `${name}-${toFileNameString(new Date())}`,
    );

    const file = await Deno.open(logPath, {
      read: false,
      write: true,
      append: true,
      create: true,
    });
    return {
      stream: file.writable,
      [Symbol.dispose]: file[Symbol.dispose].bind(file),
    };
  }

  async createExternalLogStreamsForProgram(
    program: string,
  ): Promise<{ stdout: WritableStream; stderr: WritableStream } & Disposable> {
    const stdout = await this.createExternalLogStream(`${program}-stdout`);
    const stderr = await this.createExternalLogStream(`${program}-stderr`);
    return {
      stdout: stdout.stream,
      stderr: stderr.stream,
      [Symbol.dispose]: () => {
        stdout[Symbol.dispose]();
        stderr[Symbol.dispose]();
      },
    };
  }
}
