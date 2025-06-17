import {
  SendEmailCommand,
  SESv2Client,
  SESv2ClientConfig,
} from "@aws-sdk/client-sesv2";

import { Mail, MailDeliverContext, MailDeliverer } from "../mail.ts";

declare module "../mail.ts" {
  interface MailDeliverResult {
    awsMessageId?: string;
  }
}

export class AwsMailDeliverer extends MailDeliverer {
  readonly name = "aws";
  readonly #aws;
  readonly #ses;

  constructor(aws: SESv2ClientConfig) {
    super(true);
    this.#aws = aws;
    this.#ses = new SESv2Client(aws);
  }

  protected override async doDeliver(
    mail: Mail,
    context: MailDeliverContext,
  ): Promise<void> {
    try {
      const sendCommand = new SendEmailCommand({
        Content: {
          Raw: { Data: mail.toUtf8Bytes() },
        },
      });

      console.info(context.logTag, "Calling aws send-email api...");
      const res = await this.#ses.send(sendCommand);
      if (res.MessageId == null) {
        console.warn(
          context.logTag,
          "AWS send-email returned null message id.",
        );
      } else {
        context.result.awsMessageId =
          `${res.MessageId}@${this.#aws.region}.amazonses.com`;
      }

      context.result.smtpMessage =
        `AWS Message ID: ${context.result.awsMessageId}`;
      context.result.recipients.set("*", {
        kind: "success",
        message: `Succeeded to call aws send-email api.`,
      });
    } catch (cause) {
      context.result.recipients.set("*", {
        kind: "failure",
        message: "A JS error was thrown when calling aws send-email." + cause,
        cause,
      });
    }
  }
}
