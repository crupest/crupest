import { join } from "@std/path";

import { toFileNameString } from "./date.ts";

export interface ExternalLogStream extends Disposable {
  stream: WritableStream;
}

export class Logger {
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
