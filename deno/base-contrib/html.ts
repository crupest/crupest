import { escape } from "@std/html";

export class Html {
  constructor(public value: string, public escaped: boolean) {}

  toEscapedString(): string {
    return this.escaped ? this.value : escape(this.value);
  }
}

export function htmlAnyToString(value: unknown): string {
  switch (typeof value) {
    case "undefined":
    case "boolean":
      return "";
    case "string":
      return escape(value);
    case "number":
    case "bigint":
      return String(value);
    default:
      if (value === null) return "";
      if (value instanceof Html) {
        return value.toEscapedString();
      }
      if (Array.isArray(value)) {
        return value.map(htmlAnyToString).join("");
      }
      return escape(String(value));
  }
}

export function html(
  strings: TemplateStringsArray,
  ...values: unknown[]
): Html {
  let result = "";
  for (let i = 0; i < strings.length; i++) {
    result += strings[i];
    if (i < values.length) {
      result += htmlAnyToString(values[i]);
    }
  }
  return new Html(result, true);
}

export function raw(str: string): Html {
  return new Html(str, true);
}
