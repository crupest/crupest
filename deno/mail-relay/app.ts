import { join } from "@std/path";
import { Hono } from "hono";
import { logger as honoLogger } from "hono/logger";

import log from "./log.ts";
import config from "./config.ts";
import { DbService } from "./db.ts";
import {
  AliasRecipientMailHook,
  FallbackRecipientHook,
  MailDeliverer,
} from "./mail.ts";
import { DovecotMailDeliverer } from "./dovecot/deliver.ts";
import { CronTask, CronTaskConfig } from "./cron.ts";
import { DumbSmtpServer } from "./dumb-smtp-server.ts";

export abstract class AppBase {
  protected readonly db: DbService;
  protected readonly crons: CronTask[] = [];
  protected readonly routes: Hono[] = [];
  protected readonly inboundDeliverer: MailDeliverer;
  protected readonly hono = new Hono();

  protected abstract readonly outboundDeliverer: MailDeliverer;

  constructor() {
    const dataPath = config.get("dataPath");
    Deno.mkdirSync(dataPath, { recursive: true });
    log.path = join(dataPath, "log");
    log.info(config);

    this.db = new DbService(join(dataPath, "db.sqlite"));
    this.inboundDeliverer = new DovecotMailDeliverer();
    this.inboundDeliverer.preHooks.push(
      new FallbackRecipientHook(new Set(config.getList("inboundFallback"))),
      new AliasRecipientMailHook(join(dataPath, "aliases.csv")),
    );

    this.hono.onError((err, c) => {
      log.error(err);
      return c.json({ msg: "Server error, check its log." }, 500);
    });

    this.hono.use(honoLogger());
    this.hono.post("/send/raw", async (context) => {
      const body = await context.req.text();
      if (body.trim().length === 0) {
        return context.json({ msg: "Can't send an empty mail." }, 400);
      } else {
        const result = await this.outboundDeliverer.deliverRaw(body);
        return context.json({
          awsMessageId: result.awsMessageId,
        });
      }
    });
    this.hono.post("/receive/raw", async (context) => {
      await this.inboundDeliverer.deliverRaw(await context.req.text());
      return context.json({ "msg": "Done!" });
    });
  }

  createCron(config: CronTaskConfig): CronTask {
    const cron = new CronTask(config);
    this.crons.push(cron);
    return cron;
  }

  async setup() {
    await this.db.migrate()
  }

  serve(): { smtp: DumbSmtpServer; http: Deno.HttpServer } {
    const smtp = new DumbSmtpServer(this.outboundDeliverer);
    smtp.serve();
    const http = Deno.serve({
      hostname: config.HTTP_HOST,
      port: config.HTTP_PORT,
    }, this.hono.fetch);
    return { smtp, http };
  }
}
