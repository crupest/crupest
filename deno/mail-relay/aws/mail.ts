import { MailDeliverContext, MailDeliverHook } from "../mail.ts";

export class AwsMailMessageIdRewriteHook implements MailDeliverHook {
  readonly #lookup;

  constructor(lookup: (origin: string) => Promise<string | null>) {
    this.#lookup = lookup;
  }

  async callback(context: MailDeliverContext): Promise<void> {
    console.info("Rewrite message ids...");
    const addresses = context.mail.simpleFindAllAddresses();
    console.info(`Addresses found in mail: ${addresses.join(", ")}.`);
    for (const address of addresses) {
      const awsMessageId = await this.#lookup(address);
      if (awsMessageId != null && awsMessageId.length !== 0) {
        console.info(`Rewrite ${address} to ${awsMessageId}.`);
        context.mail.raw = context.mail.raw.replaceAll(address, awsMessageId);
      }
    }
    console.info("Done rewrite message ids.");
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
    console.info("Save aws message ids...");
    const messageId = context.mail
      .startSimpleParse()
      .sections()
      .headers()
      .messageId();
    if (messageId == null) {
      console.info("Original mail does not have message id. Skip saving.");
      return;
    }
    if (context.result.awsMessageId != null) {
      console.info(`Saving ${messageId} => ${context.result.awsMessageId}.`);
      context.mail.raw = context.mail.raw.replaceAll(
        messageId,
        context.result.awsMessageId,
      );
      await this.#record(messageId, context.result.awsMessageId, context);
    }
    console.info("Done save message ids.");
  }
}
