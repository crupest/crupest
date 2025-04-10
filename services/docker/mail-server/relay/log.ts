import { join } from "@std/path";
import { toWritableStream, Writer } from "@std/io";

import "./better-js.ts";

export interface LogOptions {
  time?: Date;
  error?: boolean;
}

export type LogFile = Pick<Deno.FsFile, "writable"> & Disposable;

export class Log {
  #path: string | null = null;

  #wrapWriter(writer: Writer): LogFile {
    return {
      writable: toWritableStream(writer, { autoClose: false }),
      [Symbol.dispose]() {},
    };
  }

  #stdoutWrapper: LogFile = this.#wrapWriter(Deno.stdout);
  #stderrWrapper: LogFile = this.#wrapWriter(Deno.stderr);

  constructor() {
  }

  get path() {
    return this.#path;
  }

  set path(path) {
    this.#path = path;
    if (path != null) {
      Deno.mkdirSync(path, { recursive: true });
    }
  }

  infoOrError(isError: boolean, ...args: unknown[]) {
    this[isError ? "error" : "info"].call(this, ...args);
  }

  info(...args: unknown[]) {
    console.log(...args);
  }

  warn(...args: unknown[]) {
    console.warn(...args);
  }

  error(...args: unknown[]) {
    console.error(...args);
  }

  #extractOptions(options?: LogOptions): Required<LogOptions> {
    return {
      time: options?.time ?? new Date(),
      error: options?.error ?? false,
    };
  }

  async openLog(
    prefix: string,
    suffix: string,
    options?: LogOptions,
  ): Promise<LogFile> {
    if (prefix.includes("/")) {
      throw new Error(`Log file prefix ${prefix} contains '/'.`);
    }
    if (suffix.includes("/")) {
      throw new Error(`Log file suffix ${suffix} contains '/'.`);
    }

    const { time, error } = this.#extractOptions(options);
    if (this.#path == null) {
      return error ? this.#stderrWrapper : this.#stdoutWrapper;
    }

    const logPath = join(
      this.#path,
      `${prefix}-${time.toFileNameString()}-${suffix}`,
    );
    return await Deno.open(logPath, {
      read: false,
      write: true,
      append: true,
      create: true,
    });
  }

  async openLogForProgram(
    program: string,
    options?: Omit<LogOptions, "error">,
  ): Promise<{ stdout: LogFile; stderr: LogFile } & Disposable> {
    const stdout = await this.openLog(program, "stdout", {
      ...options,
      error: false,
    });
    const stderr = await this.openLog(program, "stderr", {
      ...options,
      error: true,
    });
    return {
      stdout,
      stderr,
      [Symbol.dispose]: () => {
        stdout[Symbol.dispose]();
        stderr[Symbol.dispose]();
      },
    };
  }
}

const log = new Log();
export default log;
