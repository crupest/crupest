import {
  SendEmailCommand,
  SESv2Client,
  SESv2ClientConfig,
} from "@aws-sdk/client-sesv2";

import { Mail, MailDeliverContext, SyncMailDeliverer } from "../mail.ts";

declare module "../mail.ts" {
  interface MailDeliverResult {
    awsMessageId?: string;
  }
}

export class AwsMailDeliverer extends SyncMailDeliverer {
  readonly name = "aws";
  readonly #aws;
  readonly #ses;

  constructor(aws: SESv2ClientConfig) {
    super();
    this.#aws = aws;
    this.#ses = new SESv2Client(aws);
  }

  protected override async doDeliver(
    mail: Mail,
    context: MailDeliverContext,
  ): Promise<void> {
    console.info("Begin to call aws send-email api...");

    try {
      const sendCommand = new SendEmailCommand({
        Content: {
          Raw: { Data: mail.toUtf8Bytes() },
        },
      });

      const res = await this.#ses.send(sendCommand);
      if (res.MessageId == null) {
        console.warn("Aws send-email returns no message id.");
      } else {
        context.result.awsMessageId = `${res.MessageId}@${
          this.#aws.region
        }.amazonses.com`;
      }

      context.result.recipients.set("*", {
        kind: "done",
        message: `Successfully called aws send-email, message id ${context.result.awsMessageId}.`,
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
