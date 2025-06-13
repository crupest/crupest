import { join } from "@std/path";
// @ts-types="npm:@types/yargs"
import yargs from "yargs";

import { TemplateDir } from "./template.ts";

if (import.meta.main) {
  await yargs(Deno.args)
    .scriptName("manage-service")
    .option("project-dir", {
      type: "string",
    })
    .demandOption("project-dir")
    .command({
      command: "gen-tmpl",
      describe: "generate files for templates",
      builder: (builder) => {
        return builder
          .option("dry-run", {
            type: "boolean",
            default: true,
          })
          .strict();
      },
      handler: (argv) => {
        const { projectDir, dryRun } = argv;
        new TemplateDir(
          join(projectDir, "services/templates"),
        ).generateWithVariableFiles(
          [
            join(projectDir, "data/config"),
            join(projectDir, "services/config.template"),
          ],
          dryRun ? undefined : join(projectDir, "services/generated"),
        );
      },
    })
    .demandCommand(1, "One command must be specified.")
    .help()
    .strict()
    .parse();
}
