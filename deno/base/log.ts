import { join } from "@std/path";

import { toFileNameString } from "./date.ts";

export type LogLevel = "error" | "warn" | "info";

export interface LogOptions {
  level?: LogLevel;
  cause?: unknown;
}

export interface ExternalLogStream extends Disposable {
  stream: WritableStream;
}

export class Logger {
  #defaultLevel = "info" as const;
  #externalLogDir?: string;

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

  write(message: string, options?: LogOptions): void {
    const logFunction = console[options?.level ?? this.#defaultLevel];
    if (options?.cause != null) {
      logFunction.call(console, message, options.cause);
    } else {
      logFunction.call(console, message);
    }
  }

  info(message: string) {
    this.write(message, { level: "info" });
  }

  tagInfo(tag: string, message: string) {
    this.info(tag + " " + message);
  }

  warn(message: string) {
    this.write(message, { level: "warn" });
  }

  tagWarn(tag: string, message: string) {
    this.warn(tag + " " + message);
  }

  error(message: string, cause?: unknown) {
    this.write(message, { level: "info", cause });
  }

  tagError(tag: string, message: string, cause?: unknown) {
    this.error(tag + " " + message, cause);
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
