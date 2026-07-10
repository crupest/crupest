import yargs from "yargs";

import { listLives, recycleLives, sendMailViaServer, serve } from "./app.js";

await yargs(process.argv.slice(2))
  .scriptName("mail")
  .command({
    command: "sendmail",
    describe: "send mail via this server's endpoint",
    handler: sendMailViaServer,
  })
  .command({
    command: "live",
    describe: "work with live mails",
    builder: (builder) => {
      return builder
        .command({
          command: "list",
          describe: "list live mails",
          handler: listLives,
        })
        .command({
          command: "recycle",
          describe: "recycle all live mails",
          handler: recycleLives,
        })
        .demandCommand(1, "One command must be specified.");
    },
    handler: () => {},
  })
  .command({
    command: "serve",
    describe: "start the http and smtp servers",
    builder: (builder) => builder.option("real", { type: "boolean" }),
    handler: (arguments_) => serve(arguments_.real),
  })
  .demandCommand(1, "One command must be specified.")
  .help()
  .strict()
  .parse();
