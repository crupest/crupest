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

function delay(duration: number | Temporal.Duration): Promise<void>;
function delay<T>(duration: number | Temporal.Duration, value: T): Promise<T>;
function delay<T>(
  duration: number | Temporal.Duration,
  value?: T,
): Promise<T | void> {
  if (duration instanceof Temporal.Duration) {
    duration = duration.total("milliseconds");
  }
  return new Promise((resolve) => {
    setTimeout(() => resolve(value), duration);
  });
}

function timeout(
  promise: Promise<unknown>,
  duration: number | Temporal.Duration,
): Promise<boolean> {
  return Promise.any([
    promise.then(() => true),
    delay(duration, false),
  ]);
}

export const Utils = {
  delay,
  timeout,
};
