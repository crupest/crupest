import { mkdirSync } from "node:fs";
import { createServer, type Server as HttpServer } from "node:http";
import type { Server as TcpServer } from "node:net";
import { join } from "node:path";

import express, { type Express } from "express";
import yargs from "yargs";
import * as z from "zod";

import { type ConfigDefinition, ConfigProvider } from "@crupest/base/config";
import { CronTask } from "@crupest/base/cron";
import { getDefaultLogger, type ILogger } from "@crupest/base/log";
import { Duration, isMain } from "@crupest/base/runtime";

import { createApp, createInbound, createSmtp, sendMail } from "../app.js";
import { DbService } from "../db.js";
import type { DovecotMailDeliverer } from "../dovecot.js";
import {
  type MailDeliverer,
  MessageIdRewriteHook,
  MessageIdSaveHook,
} from "../mail.js";
import { AwsMailDeliverer } from "./deliver.js";
import { AwsMailFetcher, LiveMailNotFoundError } from "./fetch.js";

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
    credentials: {
      accessKeyId: user,
      secretAccessKey: password,
    },
    region,
  };
}

function createOutbound({
  logger,
  aws: awsOptions,
  db,
  local,
}: {
  logger: ILogger;
  aws: ReturnType<typeof createAwsOptions>;
  db: DbService;
  local: DovecotMailDeliverer;
}) {
  const deliverer = new AwsMailDeliverer({ logger, aws: awsOptions });
  deliverer.preHooks.push(new MessageIdRewriteHook(db.messageIdToNew.bind(db)));
  deliverer.postHooks.push(
    new MessageIdSaveHook(async (original, newMessageId, context) => {
      await db.addMessageIdMap({
        message_id: original,
        new_message_id: newMessageId,
      });
      void local.saveNewSent(context.logger, context.mail, original);
    }),
  );
  return deliverer;
}

const inboundRequestSchema = z.object({
  key: z.string(),
  recipients: z.array(z.string()).optional(),
});

function setupAwsApp(
  app: Express,
  options: {
    path: string;
    auth: string;
    fetcher: AwsMailFetcher;
    deliverer: MailDeliverer;
  },
) {
  app.post(
    `/${options.path}`,
    (request, response, next) => {
      if (request.header("Authorization") !== options.auth) {
        response.status(403).json({ message: "Bad auth!" });
        return;
      }
      next();
    },
    express.json({ limit: "1mb" }),
    async (request, response) => {
      const parsed = inboundRequestSchema.safeParse(request.body);
      if (!parsed.success) {
        response.status(400).json({
          message: "Invalid request body.",
          issues: parsed.error.issues,
        });
        return;
      }

      const { key, recipients } = parsed.data;
      try {
        await options.fetcher.deliverLiveMail(
          key,
          options.deliverer,
          recipients,
        );
      } catch (error) {
        if (error instanceof LiveMailNotFoundError) {
          response.json({ message: error.message });
          return;
        }
        throw error;
      }
      response.json({ message: "Done!" });
    },
  );
}

function createCron(fetcher: AwsMailFetcher, deliverer: MailDeliverer) {
  return new CronTask({
    name: "live-mail-recycler",
    interval: Duration.hours(6),
    callback: () => fetcher.recycleLiveMails(deliverer),
    enableNow: true,
  });
}

function closeServer(server: HttpServer | TcpServer): Promise<void> {
  if (!server.listening) return Promise.resolve();
  return new Promise((resolve, reject) => {
    server.close((error) => {
      if (error == null) resolve();
      else reject(error);
    });
  });
}

function createBaseServices() {
  const config = new ConfigProvider(PREFIX, CONFIG_DEFINITIONS);
  mkdirSync(config.get("dataPath"), { recursive: true });
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
    logger,
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
  const app = createApp({ logger, outbound, inbound });

  setupAwsApp(app, {
    path: config.get("awsInboundPath"),
    auth: config.get("awsInboundKey"),
    fetcher,
    deliverer: inbound,
  });

  return { ...services, smtp, app };
}

async function serve(cron = false) {
  const { config, logger, fetcher, inbound, smtp, db, app } =
    createServerServices();

  await db.migrate();

  const smtpServer = smtp.serve({
    hostname: config.get("smtpHost"),
    port: config.getInt("smtpPort"),
  });
  const httpServer = createServer(app);
  httpServer.listen(config.getInt("httpPort"), config.get("httpHost"));

  const cronTask = cron ? createCron(fetcher, inbound) : undefined;

  let shutdownPromise: Promise<void> | undefined;
  const shutdown = () => {
    if (shutdownPromise == null) {
      cronTask?.disable();
      shutdownPromise = (async () => {
        await Promise.all([closeServer(smtpServer), closeServer(httpServer)]);
        await db.close();
      })();
    }
    return shutdownPromise;
  };
  const handleShutdown = () => {
    void shutdown().catch((error) => {
      logger.error("Mail server shutdown failed.", error);
      process.exitCode = 1;
    });
  };
  process.once("SIGINT", handleShutdown);
  process.once("SIGTERM", handleShutdown);
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

if (isMain(import.meta.url)) {
  await yargs(process.argv.slice(2))
    .scriptName("mail")
    .command({
      command: "sendmail",
      describe: "send mail via this server's endpoint",
      handler: async () => {
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
      handler: (arguments_) => serve(arguments_.real),
    })
    .demandCommand(1, "One command must be specified.")
    .help()
    .strict()
    .parse();
}
