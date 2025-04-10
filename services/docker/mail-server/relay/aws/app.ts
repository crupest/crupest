import { parseArgs } from "@std/cli";
import { z } from "zod";
import { zValidator } from "@hono/zod-validator";

import log from "../log.ts";
import config from "../config.ts";
import { AppBase } from "../app.ts";
import { AwsContext } from "./context.ts";
import { AwsMailDeliverer } from "./deliver.ts";
import { AwsMailRetriever } from "./retriever.ts";

export class AwsRelayApp extends AppBase {
  readonly #aws = new AwsContext();
  readonly #retriever;
  protected readonly outboundDeliverer = new AwsMailDeliverer(this.#aws);

  constructor() {
    super();
    this.#retriever = new AwsMailRetriever(this.#aws, this.inboundDeliverer);

    this.hono.post(
      `/${config.get("awsInboundPath")}`,
      async (ctx, next) => {
        const auth = ctx.req.header("Authorization");
        if (auth !== config.get("awsInboundKey")) {
          return ctx.json({ "msg": "Bad auth!" }, 403);
        }
        await next();
      },
      zValidator(
        "json",
        z.object({
          key: z.string(),
          recipients: z.array(z.string()).optional(),
        }),
      ),
      async (ctx) => {
        const { key, recipients } = ctx.req.valid("json");
        await this.#retriever.deliverS3Mail(key, recipients);
        return ctx.json({ "msg": "Done!" });
      },
    );
  }

  realServe() {
    this.createCron({
      name: "live-mail-recycler",
      interval: 6 * 3600 * 1000,
      callback: () => {
        return this.#retriever.recycleLiveMails();
      },
      startNow: true,
    });

    return this.serve();
  }

  readonly cli = {
    "init": (_: unknown) => {
      log.info("Just init!");
      return Promise.resolve();
    },
    "list-lives": async (_: unknown) => {
      const liveMails = await this.#retriever.listLiveMails();
      log.info(`Total ${liveMails.length}:`);
      log.info(liveMails.join("\n"));
    },
    "recycle-lives": async (_: unknown) => {
      await this.#retriever.recycleLiveMails();
    },
    "serve": async (_: unknown) => {
      await this.serve().http.finished;
    },
    "real-serve": async (_: unknown) => {
      await this.realServe().http.finished;
    },
  } as const;
}

const nonServerCli = {
  "sendmail": async (_: unknown) => {
    const decoder = new TextDecoder();
    let text = "";
    for await (const chunk of Deno.stdin.readable) {
      text += decoder.decode(chunk);
    }

    const res = await fetch(
      `http://localhost:${config.HTTP_PORT}/send/raw`,
      {
        method: "post",
        body: text,
      },
    );
    log.infoOrError(!res.ok, res);
    log.infoOrError(!res.ok, "Body\n" + await res.text());
    if (!res.ok) Deno.exit(-1);
  },
} as const;

if (import.meta.main) {
  const args = parseArgs(Deno.args);

  if (args._.length === 0) {
    throw new Error("You must specify a command.");
  }

  const command = args._[0];

  if (command in nonServerCli) {
    log.info(`Run non-server command ${command}.`);
    await nonServerCli[command as keyof typeof nonServerCli](args);
    Deno.exit(0);
  }

  const app = new AwsRelayApp();
  if (command in app.cli) {
    log.info(`Run command ${command}.`);
    await app.cli[command as keyof AwsRelayApp["cli"]](args);
    Deno.exit(0);
  } else {
    throw new Error(command + " is not a valid command.");
  }
}
