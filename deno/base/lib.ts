export function camelCaseToKebabCase(str: string): string {
  return str.replace(/[A-Z]/g, (m) => "-" + m.toLowerCase());
}

export function toFileNameString(date: Date, dateOnly?: boolean): string {
  const str = date.toISOString();
  return dateOnly === true
    ? str.slice(0, str.indexOf("T"))
    : str.replaceAll(/:|\./g, "-");
}
