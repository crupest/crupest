import { join } from "@std/path";
import { z } from "zod";
import { Hono } from "hono";
import { zValidator } from "@hono/zod-validator";
import { FetchHttpHandler } from "@smithy/fetch-http-handler";
// @ts-types="npm:@types/yargs"
import yargs from "yargs";

import { ConfigDefinition, ConfigProvider } from "@crupest/base/config";
import { CronTask } from "@crupest/base/cron";
import { getDefaultLogger, ILogger } from "@crupest/base/log";

import { DbService } from "../db.ts";
import { createHono, createInbound, createSmtp, sendMail } from "../app.ts";
import { DovecotMailDeliverer } from "../dovecot.ts";
import { MailDeliverer } from "../mail.ts";
import { MessageIdRewriteHook, MessageIdSaveHook } from "../mail.ts";
import { AwsMailDeliverer } from "./deliver.ts";
import { AwsMailFetcher, LiveMailNotFoundError } from "./fetch.ts";

const PREFIX = "crupest-mail-server";
const CONFIG_DEFINITIONS = {
  dataPath: {
    description: "Path to save app persistent data.",
    default: "/data",
  },
  mailDomain: {
    description:
      "The part after `@` of an address. Used to determine local recipients.",
  },
  httpHost: {
    description: "Listening address for http server.",
    default: "0.0.0.0",
  },
  httpPort: { description: "Listening port for http server.", default: "2345" },
  smtpHost: {
    description: "Listening address for dumb smtp server.",
    default: "127.0.0.1",
  },
  smtpPort: {
    description: "Listening port for dumb smtp server.",
    default: "2346",
  },
  ldaPath: {
    description: "full path of lda executable",
    default: "/usr/lib/dovecot/dovecot-lda",
  },
  doveadmPath: {
    description: "full path of doveadm executable",
    default: "/usr/bin/doveadm",
  },
  inboundFallback: {
    description: "comma separated addresses used as fallback recipients",
    default: "",
  },
  awsInboundPath: {
    description: "(random set) path for aws sns",
  },
  awsInboundKey: {
    description: "(random set) http header Authorization for aws sns",
  },
  awsRegion: {
    description: "aws region",
  },
  awsUser: {
    description: "aws access key id",
  },
  awsPassword: {
    description: "aws secret access key",
    secret: true,
  },
  awsMailBucket: {
    description: "aws s3 bucket saving raw mails",
    secret: true,
  },
} as const satisfies ConfigDefinition;

function createAwsOptions({
  user,
  password,
  region,
}: {
  user: string;
  password: string;
  region: string;
}) {
  return {
    credentials: () =>
      Promise.resolve({
        accessKeyId: user,
        secretAccessKey: password,
      }),
    requestHandler: new FetchHttpHandler(),
    region,
  };
}

function createOutbound({ logger, aws: awsOptions, db, local }: {
  logger: ILogger;
  aws: ReturnType<typeof createAwsOptions>;
  db: DbService;
  local: DovecotMailDeliverer;
}) {
  const deliverer = new AwsMailDeliverer({ logger, aws: awsOptions });
  deliverer.preHooks.push(
    new MessageIdRewriteHook(db.messageIdToNew.bind(db)),
  );
  deliverer.postHooks.push(
    new MessageIdSaveHook(
      async (original, new_message_id, context) => {
        await db.addMessageIdMap({ message_id: original, new_message_id });
        void local.saveNewSent(context.logger, context.mail, original);
      },
    ),
  );
  return deliverer;
}

function setupAwsHono(
  hono: Hono,
  options: {
    path: string;
    auth: string;
    fetcher: AwsMailFetcher;
    deliverer: MailDeliverer;
  },
) {
  hono.post(
    `/${options.path}`,
    async (ctx, next) => {
      const auth = ctx.req.header("Authorization");
      if (auth !== options.auth) {
        return ctx.json({ message: "Bad auth!" }, 403);
      }
      await next();
    },
    zValidator(
      "json",
      z.object({
        key: z.string(),
        recipients: z.optional(z.array(z.string())),
      }),
    ),
    async (ctx) => {
      const { fetcher, deliverer } = options;
      const { key, recipients } = ctx.req.valid("json");
      try {
        await fetcher.deliverLiveMail(
          key,
          deliverer,
          recipients,
        );
      } catch (e) {
        if (e instanceof LiveMailNotFoundError) {
          return ctx.json({ message: e.message });
        }
        throw e;
      }
      return ctx.json({ message: "Done!" });
    },
  );
}

function createCron(fetcher: AwsMailFetcher, deliverer: MailDeliverer) {
  return new CronTask({
    name: "live-mail-recycler",
    interval: Temporal.Duration.from({ hours: 6 }),
    callback: () => {
      return fetcher.recycleLiveMails(deliverer);
    },
    enableNow: true,
  });
}

function createBaseServices() {
  const config = new ConfigProvider(PREFIX, CONFIG_DEFINITIONS);
  Deno.mkdirSync(config.get("dataPath"), { recursive: true });
  return { config, logger: getDefaultLogger() };
}

function createAwsFetchOnlyServices() {
  const services = createBaseServices();
  const { config, logger } = services;

  const aws = createAwsOptions({
    user: config.get("awsUser"),
    password: config.get("awsPassword"),
    region: config.get("awsRegion"),
  });
  const fetcher = new AwsMailFetcher({
    logger,
    aws,
    bucket: config.get("awsMailBucket"),
  });

  return { ...services, aws, fetcher };
}

function createAwsRecycleOnlyServices() {
  const services = createAwsFetchOnlyServices();
  const { config, logger } = services;

  const inbound = createInbound({
    logger,
    fallback: config.getList("inboundFallback"),
    ldaPath: config.get("ldaPath"),
    doveadmPath: config.get("doveadmPath"),
    aliasFile: join(config.get("dataPath"), "postfix-virtual"),
    mailDomain: config.get("mailDomain"),
  });

  return { ...services, inbound };
}

function createAwsServices() {
  const services = createAwsRecycleOnlyServices();
  const { logger, config, aws, inbound } = services;

  const db = new DbService(join(config.get("dataPath"), "crupest-mail.sqlite"));
  const outbound = createOutbound({
    logger: logger,
    aws,
    db,
    local: inbound,
  });

  return { ...services, db, outbound };
}

function createServerServices() {
  const services = createAwsServices();
  const { logger, config, outbound, inbound, fetcher } = services;

  const smtp = createSmtp({ logger, outbound });
  const hono = createHono({ logger, outbound, inbound });

  setupAwsHono(hono, {
    path: config.get("awsInboundPath"),
    auth: config.get("awsInboundKey"),
    fetcher,
    deliverer: inbound,
  });

  return { ...services, smtp, hono };
}

async function serve(cron: boolean = false) {
  const { config, fetcher, inbound, smtp, db, hono } = createServerServices();

  await db.migrate();

  smtp.serve({
    hostname: config.get("smtpHost"),
    port: config.getInt("smtpPort"),
  });
  Deno.serve(
    {
      hostname: config.get("httpHost"),
      port: config.getInt("httpPort"),
    },
    hono.fetch,
  );

  if (cron) {
    createCron(fetcher, inbound);
  }
}

async function listLives() {
  const { fetcher } = createAwsFetchOnlyServices();
  const liveMails = await fetcher.listLiveMails();
  console.info(`Total ${liveMails.length}:`);
  if (liveMails.length !== 0) {
    console.info(liveMails.join("\n"));
  }
}

async function recycleLives() {
  const { fetcher, inbound } = createAwsRecycleOnlyServices();
  await fetcher.recycleLiveMails(inbound);
}

if (import.meta.main) {
  await yargs(Deno.args)
    .scriptName("mail")
    .command({
      command: "sendmail",
      describe: "send mail via this server's endpoint",
      handler: async (_argv) => {
        const { config } = createBaseServices();
        await sendMail(config.getInt("httpPort"));
      },
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
      handler: (argv) => serve(argv.real),
    })
    .demandCommand(1, "One command must be specified.")
    .help()
    .strict()
    .parse();
}
