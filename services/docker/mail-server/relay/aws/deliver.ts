import { SendEmailCommand, SESv2Client } from "@aws-sdk/client-sesv2";

import { AwsContext } from "./context.ts";
import {
  Mail,
  MailDeliverContext,
  MailDeliverer,
  MailDeliverRecipientResult,
} from "./mail.ts";
import log from "../log.ts";

export class AwsMailDeliverer extends MailDeliverer {
  readonly name = "aws";
  readonly #ses;

  constructor(aws: AwsContext) {
    super();
    this.#ses = new SESv2Client(aws);
  }

  protected override async doDeliver(
    mail: Mail,
    context: MailDeliverContext,
  ): Promise<void> {
    log.info("Begin to call aws send-email api...");

    const result: MailDeliverRecipientResult = {
      kind: "done",
      message: "Success to call send-email api of aws.",
    };

    try {
      const sendCommand = new SendEmailCommand({
        Content: {
          Raw: { Data: mail.toUtf8Bytes() },
        },
      });

      const res = await this.#ses.send(sendCommand);
      if (res.MessageId == null) {
        log.warn("Aws send-email returns no message id.");
      }
      mail.awsMessageId = res.MessageId;
    } catch (cause) {
      result.kind = "fail";
      result.message = "An error was thrown when calling aws send-email." +
        cause;
      result.cause = cause;
    }
    context.result.set("*", result);
  }
}
