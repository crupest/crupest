import { resolve } from "node:path";
import { fileURLToPath } from "node:url";

export const Duration = {
  milliseconds: (value: number): number => value,
  seconds: (value: number): number => value * 1_000,
  minutes: (value: number): number => value * 60_000,
  hours: (value: number): number => value * 3_600_000,
  days: (value: number): number => value * 86_400_000,
} as const;

export function isMain(metaUrl: string): boolean {
  const entrypoint = process.argv[1];
  return (
    entrypoint != null &&
    resolve(fileURLToPath(metaUrl)) === resolve(entrypoint)
  );
}

export function isErrnoException(
  error: unknown,
  code?: string,
): error is NodeJS.ErrnoException {
  if (!(error instanceof Error) || !("code" in error)) return false;
  return code == null || error.code === code;
}
