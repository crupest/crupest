function camelCaseToKebabCase(str: string): string {
  return str.replace(/[A-Z]/g, (m) => "-" + m.toLowerCase());
}

function prependNonEmpty<T>(
  object: T | null | undefined,
  prefix: string = " ",
): string {
  if (object == null) return "";
  const string = typeof object === "string" ? object : String(object);
  return string.length === 0 ? "" : prefix + string;
}

export const StringUtils = {
  camelCaseToKebabCase,
  prependNonEmpty,
} as const;

function toFileNameString(date: Date, dateOnly?: boolean): string {
  const str = date.toISOString();
  return dateOnly === true
    ? str.slice(0, str.indexOf("T"))
    : str.replaceAll(/:|\./g, "-");
}

export const DateUtils = {
  toFileNameString,
} as const;

function delay(duration: number): Promise<void>;
function delay<T>(duration: number, value: T): Promise<T>;
function delay<T>(duration: number, value?: T): Promise<T | void> {
  return new Promise((resolve) => {
    setTimeout(() => resolve(value), duration);
  });
}

function timeout(
  promise: Promise<unknown>,
  duration: number,
): Promise<boolean> {
  return Promise.any([promise.then(() => true), delay(duration, false)]);
}

function promise<T>(): [
  promise: Promise<T>,
  resolve: (value: T) => void,
  reject: (reason?: unknown) => void,
] {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return [promise, resolve, reject];
}

export const Utils = {
  delay,
  timeout,
  promise,
};
