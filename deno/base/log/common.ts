export const LOG_LEVELS = ["debug", "info", "warn", "error"] as const;
export type LogLevel = typeof LOG_LEVELS[number];

export interface LogOptions {
  time?: Date;
  tag?: string;
  level: LogLevel;
  args: unknown[];
}

export type LogEntry = Required<LogOptions>;

export type FormattedLogEntry = Omit<LogEntry, "args"> & { message: string };

export interface ILogFormatter {
  format(entry: LogEntry): Promise<string>;
}

export interface ILogWriter {
  write(entry: FormattedLogEntry): Promise<void>;
}

export class DefaultLogFormatter implements ILogFormatter {
  #decorated: boolean;

  constructor(decorated = true) {
    this.#decorated = decorated;
  }

  format({ level, time, tag, args }: LogEntry): Promise<string> {
    const message = args.map((arg) =>
      typeof arg === "object" ? Deno.inspect(arg, { depth: 3 }) : String(arg)
    ).join(" ");

    if (!this.#decorated) {
      return Promise.resolve(message);
    }

    const headList = [time.toISOString(), level.toUpperCase()];
    if (tag) headList.push(tag);
    return Promise.resolve(`[${headList.join(" ")}] ${message}`);
  }
}

export class NullLogFormatter implements ILogFormatter {
  format(_entry: LogEntry): Promise<string> {
    return Promise.resolve("");
  }
}

export class NullLogWriter implements ILogWriter {
  write(_entry: FormattedLogEntry): Promise<void> {
    return Promise.resolve();
  }
}

export interface ILogger {
  readonly formatter: ILogFormatter;
  readonly writer: ILogWriter;
  defaultTag: string;
  withDefaultTag(tag: string): Logger;
  log(options: LogOptions): Promise<void>;
  debug(...args: unknown[]): Promise<void>;
  info(...args: unknown[]): Promise<void>;
  warn(...args: unknown[]): Promise<void>;
  error(...args: unknown[]): Promise<void>;
  tagDebug(tag: string, ...args: unknown[]): Promise<void>;
  tagInfo(tag: string, ...args: unknown[]): Promise<void>;
  tagWarn(tag: string, ...args: unknown[]): Promise<void>;
  tagError(tag: string, ...args: unknown[]): Promise<void>;
}

export class Logger implements ILogger {
  #defaultTag: string;
  #formatter: ILogFormatter;
  #writer: ILogWriter;

  constructor({ defaultTag, formatter, writer }: {
    defaultTag?: string;
    formatter: ILogFormatter;
    writer: ILogWriter;
  }) {
    this.#defaultTag = defaultTag ?? "";
    this.#formatter = formatter;
    this.#writer = writer;
  }

  get formatter(): ILogFormatter {
    return this.#formatter;
  }

  get writer(): ILogWriter {
    return this.#writer;
  }

  get defaultTag(): string {
    return this.#defaultTag;
  }

  set defaultTag(value: string | null | undefined) {
    this.#defaultTag = value ?? "";
  }

  withDefaultTag(tag: string): Logger {
    const logger = new Logger({
      defaultTag: tag,
      formatter: this.formatter,
      writer: this.writer,
    });
    return logger;
  }

  async log({ time, tag, level, args }: LogOptions): Promise<void> {
    time = time ?? new Date();
    tag = tag ?? this.defaultTag;
    const message = await this.#formatter.format({ time, tag, level, args });
    await this.#writer.write({ time, tag, level, message });
  }

  debug(...args: unknown[]) {
    return this.log({ level: "debug", args });
  }

  info(...args: unknown[]) {
    return this.log({ level: "info", args });
  }

  warn(...args: unknown[]) {
    return this.log({ level: "warn", args });
  }

  error(...args: unknown[]) {
    return this.log({ level: "error", args });
  }

  tagDebug(tag: string, ...args: unknown[]) {
    return this.log({ level: "debug", tag, args });
  }

  tagInfo(tag: string, ...args: unknown[]) {
    return this.log({ level: "info", tag, args });
  }

  tagWarn(tag: string, ...args: unknown[]) {
    return this.log({ level: "warn", tag, args });
  }

  tagError(tag: string, ...args: unknown[]) {
    return this.log({ level: "error", tag, args });
  }
}

export const NULL_LOGGER = new Logger({
  formatter: new NullLogFormatter(),
  writer: new NullLogWriter(),
});
