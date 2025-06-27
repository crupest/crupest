import yargs, { DEMAND_COMMAND_MESSAGE } from "./yargs.ts";
import vm from "./vm.ts";
import service from "./service.ts";

if (import.meta.main) {
  await yargs(Deno.args)
    .scriptName("crupest")
    .command(vm)
    .command(service)
    .demandCommand(1, DEMAND_COMMAND_MESSAGE)
    .help()
    .strict()
    .parse();
}
