import type { CommandModule } from "yargs";

export { default } from "yargs";
export * from "yargs";

export function defineYargsModule<T, U>(
  module: CommandModule<T, U>,
): CommandModule<T, U> {
  return module;
}

export const DEMAND_COMMAND_MESSAGE = "No command is specified";
