import { join } from "@std/path";
import { z } from "zod";
import { Hono } from "hono";
import { zValidator } from "@hono/zod-validator";
import { FetchHttpHandler } from "@smithy/fetch-http-handler";
// @ts-types="npm:@types/yargs"
import yargs from "yargs";

import { Logger } from "@crupest/base/log";
import { ConfigDefinition, ConfigProvider } from "@crupest/base/config";
import { CronTask } from "@crupest/base/cron";

import { DbService } from "../db.ts";
import { Mail } from "../mail.ts";
import {
  AwsMailMessageIdRewriteHook,
  AwsMailMessageIdSaveHook,
} from "./mail.ts";
import { AwsMailDeliverer } from "./deliver.ts";
import { AwsMailFetcher, AwsS3MailConsumer } from "./fetch.ts";
import { createInbound, createHono, sendMail, createSmtp } from "../app.ts";

const PREFIX = "crupest-mail-server";
const CONFIG_DEFINITIONS = {
  dataPath: {
    description: "Path to save app persistent data.",
    default: ".",
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
    default: "/dovecot/libexec/dovecot/dovecot-lda",
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

function createOutbound(
  awsOptions: ReturnType<typeof createAwsOptions>,
  db: DbService,
) {
  const deliverer = new AwsMailDeliverer(awsOptions);
  deliverer.preHooks.push(
    new AwsMailMessageIdRewriteHook(db.messageIdToAws.bind(db)),
  );
  deliverer.postHooks.push(
    new AwsMailMessageIdSaveHook((original, aws) =>
      db.addMessageIdMap({ message_id: original, aws_message_id: aws }).then(),
    ),
  );
  return deliverer;
}

function setupAwsHono(
  hono: Hono,
  options: {
    path: string;
    auth: string;
    callback: (s3Key: string, recipients?: string[]) => Promise<void>;
  },
) {
  hono.post(
    `/${options.path}`,
    async (ctx, next) => {
      const auth = ctx.req.header("Authorization");
      if (auth !== options.auth) {
        return ctx.json({ msg: "Bad auth!" }, 403);
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
      const { key, recipients } = ctx.req.valid("json");
      await options.callback(key, recipients);
      return ctx.json({ msg: "Done!" });
    },
  );
}

function createCron(fetcher: AwsMailFetcher, consumer: AwsS3MailConsumer) {
  return new CronTask({
    name: "live-mail-recycler",
    interval: 6 * 3600 * 1000,
    callback: () => {
      return fetcher.recycleLiveMails(consumer);
    },
    startNow: true,
  });
}

function createBaseServices() {
  const config = new ConfigProvider(PREFIX, CONFIG_DEFINITIONS);
  Deno.mkdirSync(config.get("dataPath"), { recursive: true });
  const logger = new Logger();
  logger.externalLogDir = join(config.get("dataPath"), "log");
  return { config, logger };
}

function createAwsFetchOnlyServices() {
  const { config, logger } = createBaseServices();
  const awsOptions = createAwsOptions({
    user: config.get("awsUser"),
    password: config.get("awsPassword"),
    region: config.get("awsRegion"),
  });
  const fetcher = new AwsMailFetcher(awsOptions, config.get("awsMailBucket"));
  return { config, logger, awsOptions, fetcher };
}

function createAwsRecycleOnlyServices() {
  const { config, logger, awsOptions, fetcher } = createAwsFetchOnlyServices();

  const inbound = createInbound(logger, {
    fallback: config.getList("inboundFallback"),
    ldaPath: config.get("ldaPath"),
    aliasFile: join(config.get("dataPath"), "aliases.csv"),
    mailDomain: config.get("mailDomain"),
  });

  const recycler = (rawMail: string, _: unknown): Promise<void> =>
    inbound.deliver({ mail: new Mail(rawMail) }).then();

  return { config, logger, awsOptions, fetcher, inbound, recycler };
}
function createAwsServices() {
  const { config, logger, inbound, awsOptions, fetcher, recycler } =
    createAwsRecycleOnlyServices();
  const dbService = new DbService(join(config.get("dataPath"), "db.sqlite"));
  const outbound = createOutbound(awsOptions, dbService);

  return {
    config,
    logger,
    inbound,
    dbService,
    awsOptions,
    fetcher,
    recycler,
    outbound,
  };
}

function createServerServices() {
  const services = createAwsServices();
  const { config, outbound, inbound, fetcher } = services;
  const smtp = createSmtp(outbound);

  const hono = createHono(outbound, inbound);
  setupAwsHono(hono, {
    path: config.get("awsInboundPath"),
    auth: config.get("awsInboundKey"),
    callback: (s3Key, recipients) => {
      return fetcher.consumeS3Mail(s3Key, (rawMail, _) =>
        inbound.deliver({ mail: new Mail(rawMail), recipients }).then(),
      );
    },
  });

  return {
    ...services,
    smtp,
    hono,
  };
}

function serve(cron: boolean = false) {
  const { config, fetcher, recycler, smtp, hono } = createServerServices();
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
    createCron(fetcher, recycler);
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
  const { fetcher, recycler } = createAwsRecycleOnlyServices();
  await fetcher.recycleLiveMails(recycler);
}

if (import.meta.main) {
  await yargs(Deno.args)
    .scriptName("mail-relay")
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
