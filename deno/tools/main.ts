import { Command } from "@cliffy/command";

import { demandCommand } from "@crupest/base-contrib/cliffy-helper";

import vm from "./vm.ts";
import service from "./service.ts";

if (import.meta.main) {
  await new Command()
    .name("crupest")
    .globalOption(
      "--project-dir <projectDir:string>",
      "Project directory. Required by service commands.",
    )
    .action(demandCommand)
    .command("vm", vm)
    .command("service", service)
    .parse(Deno.args);
}
