export function demandCommand(this: { showHelp: () => void }) {
  this.showHelp();
  console.error("No command is specified");
  Deno.exit(1);
}
