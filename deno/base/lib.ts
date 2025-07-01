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

export const StringUtils = Object.freeze({
  camelCaseToKebabCase,
  prependNonEmpty,
});

function toFileNameString(date: Date, dateOnly?: boolean): string {
  const str = date.toISOString();
  return dateOnly === true
    ? str.slice(0, str.indexOf("T"))
    : str.replaceAll(/:|\./g, "-");
}

export const DateUtils = Object.freeze(
  {
    toFileNameString,
  } as const,
);
