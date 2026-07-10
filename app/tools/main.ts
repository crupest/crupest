import yargs, { DEMAND_COMMAND_MESSAGE } from "./yargs.js";
import geosite from "./geosite.js";
import service from "./service.js";
import vm from "./vm.js";

await yargs(process.argv.slice(2))
  .scriptName("crupest")
  .command(geosite)
  .command(vm)
  .command(service)
  .demandCommand(1, DEMAND_COMMAND_MESSAGE)
  .help()
  .strict()
  .parse();
