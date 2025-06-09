import { parseArgs } from "@std/cli";
import { loadVariables, TemplateDir } from "./template.ts";
import { join } from "@std/path";

if (import.meta.main) {
  const args = parseArgs(Deno.args, {
    string: ["project-dir"],
    boolean: ["no-dry-run"],
  });

  if (args._.length === 0) {
    throw new Error("You must specify a command.");
  }

  const projectDir = args["project-dir"];
  if (projectDir == null) {
    throw new Error("You must specify project-dir.");
  }

  const command = String(args._[0]);

  switch (command) {
    case "gen-tmpl":
      new TemplateDir(
        join(projectDir, "services/templates"),
      ).generateWithVariableFiles(
        [
          join(projectDir, "data/config"),
          join(projectDir, "services/config.template"),
        ],
        args["no-dry-run"] === true
          ? join(projectDir, "services/generated")
          : undefined,
      );
      break;
    default:
      throw new Error(command + " is not a valid command.");
  }
}
