import { isMain } from "@crupest/base/runtime";

import yargs, { DEMAND_COMMAND_MESSAGE } from "./yargs.js";
import service from "./service.js";
import vm from "./vm.js";

if (isMain(import.meta.url)) {
  await yargs(process.argv.slice(2))
    .scriptName("crupest")
    .command(vm)
    .command(service)
    .demandCommand(1, DEMAND_COMMAND_MESSAGE)
    .help()
    .strict()
    .parse();
}
