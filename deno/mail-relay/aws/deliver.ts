// spellchecker: words sesv2 amazonses

import { SendEmailCommand, SESv2Client } from "@aws-sdk/client-sesv2";

import log from "../log.ts";
import { DbService } from "../db.ts";
import {
  Mail,
  MailDeliverContext,
  MailDeliverHook,
  SyncMailDeliverer,
} from "../mail.ts";
import { AwsContext } from "./context.ts";

declare module "../mail.ts" {
  interface MailDeliverResult {
    awsMessageId?: string;
  }
}

export class AwsMailMessageIdRewriteHook implements MailDeliverHook {
  readonly #db;

  constructor(db: DbService) {
    this.#db = db;
  }

  async callback(context: MailDeliverContext): Promise<void> {
    log.info("Rewrite message ids...");
    const addresses = context.mail.simpleFindAllAddresses();
    log.info(`Addresses found in mail: ${addresses.join(", ")}.`);
    for (const address of addresses) {
      const awsMessageId = await this.#db.messageIdToAws(address);
      if (awsMessageId != null && awsMessageId.length !== 0) {
        log.info(`Rewrite ${address} to ${awsMessageId}.`);
        context.mail.raw = context.mail.raw.replaceAll(address, awsMessageId);
      }
    }
    log.info("Done rewrite message ids.");
  }
}

export class AwsMailMessageIdSaveHook implements MailDeliverHook {
  readonly #db;

  constructor(db: DbService) {
    this.#db = db;
  }

  async callback(context: MailDeliverContext): Promise<void> {
    log.info("Save aws message ids...");
    const messageId = context.mail.startSimpleParse().sections().headers()
      .messageId();
    if (messageId == null) {
      log.info("Original mail does not have message id. Skip saving.");
      return;
    }
    if (context.result.awsMessageId != null) {
      log.info(`Saving ${messageId} => ${context.result.awsMessageId}.`);
      await this.#db.addMessageIdMap({
        message_id: messageId,
        aws_message_id: context.result.awsMessageId,
      });
    }
    log.info("Done save message ids.");
  }
}

export class AwsMailDeliverer extends SyncMailDeliverer {
  readonly name = "aws";
  readonly #aws;
  readonly #ses;

  constructor(aws: AwsContext) {
    super();
    this.#aws = aws;
    this.#ses = new SESv2Client(aws);
  }

  protected override async doDeliver(
    mail: Mail,
    context: MailDeliverContext,
  ): Promise<void> {
    log.info("Begin to call aws send-email api...");

    try {
      const sendCommand = new SendEmailCommand({
        Content: {
          Raw: { Data: mail.toUtf8Bytes() },
        },
      });

      const res = await this.#ses.send(sendCommand);
      if (res.MessageId == null) {
        log.warn("Aws send-email returns no message id.");
      } else {
        context.result.awsMessageId =
          `${res.MessageId}@${this.#aws.region}.amazonses.com`;
      }

      context.result.recipients.set("*", {
        kind: "done",
        message:
          `Successfully called aws send-email, message id ${context.result.awsMessageId}.`,
      });
    } catch (cause) {
      context.result.recipients.set("*", {
        kind: "fail",
        message: "An error was thrown when calling aws send-email." + cause,
        cause,
      });
    }
  }
}
