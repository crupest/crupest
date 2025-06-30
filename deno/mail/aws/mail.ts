import { MailDeliverContext, MailDeliverHook } from "../mail.ts";

export class AwsMailMessageIdRewriteHook implements MailDeliverHook {
  readonly #lookup;

  constructor(lookup: (origin: string) => Promise<string | null>) {
    this.#lookup = lookup;
  }

  async callback(context: MailDeliverContext): Promise<void> {
    const addresses = context.mail.simpleFindAllAddresses();
    for (const address of addresses) {
      const awsMessageId = await this.#lookup(address);
      if (awsMessageId != null && awsMessageId.length !== 0) {
        console.info(
          context.logTag,
          `Rewrite address-line string in mail: ${address} => ${awsMessageId}.`,
        );
        context.mail.raw = context.mail.raw.replaceAll(address, awsMessageId);
      }
    }
  }
}

export class AwsMailMessageIdSaveHook implements MailDeliverHook {
  readonly #record;

  constructor(
    record: (
      original: string,
      aws: string,
      context: MailDeliverContext,
    ) => Promise<void>,
  ) {
    this.#record = record;
  }

  async callback(context: MailDeliverContext): Promise<void> {
    const { messageId } = context.mail.parsed;
    if (messageId == null) {
      console.warn(
        context.logTag,
        "Original mail doesn't have message id, skip saving message id map.",
      );
      return;
    }
    if (context.result.awsMessageId != null) {
      console.info(
        context.logTag,
        `Save message id map: ${messageId} => ${context.result.awsMessageId}.`,
      );
      context.mail.raw = context.mail.raw.replaceAll(
        messageId,
        context.result.awsMessageId,
      );
      await this.#record(messageId, context.result.awsMessageId, context);
    }
  }
}
