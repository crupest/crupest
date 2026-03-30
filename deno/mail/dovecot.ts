import { ILogger, NULL_LOGGER } from "@crupest/base/log";

import { Mail, MailDeliverContext, MailDeliverer } from "./mail.ts";

// https://doc.dovecot.org/main/core/man/dovecot-lda.1.html
const ldaExitCodeMessageMap = new Map<number, string>();
ldaExitCodeMessageMap.set(67, "recipient user not known");
ldaExitCodeMessageMap.set(75, "temporary error");

async function runCommand(
  bin: string,
  options: {
    logger: ILogger;
    args: string[];
    stdin?: Uint8Array;
    errorCodeMessageMap?: Map<number, string>;
  },
): Promise<{
  success: boolean;
  message: string;
}> {
  const { logger, args, stdin, errorCodeMessageMap } = options;

  logger.info(`Run external command ${bin} ${args.join(" ")}`);

  try {
    // Create and spawn process.
    const command = new Deno.Command(bin, {
      args,
      stdin: stdin == null ? "null" : "piped",
    });
    const process = command.spawn();

    // Write stdin if any.
    if (stdin != null) {
      const writer = process.stdin.getWriter();
      await writer.write(stdin);
      writer.close();
    }

    // Wait for process to exit.
    const status = await process.status;
    const success = status.success;

    // Build log message string.
    let message = `External command exited with code ${status.code}`;
    if (status.signal != null) message += ` (signal: ${status.signal})`;
    if (errorCodeMessageMap != null && errorCodeMessageMap.has(status.code)) {
      message += `, ${errorCodeMessageMap.get(status.code)}`;
    }

    logger[success ? "info" : "error"](message);

    // Return result.
    return { success, message };
  } catch (cause) {
    const message = "A JS error was thrown when invoking external command " +
      cause;
    logger.error(message);
    return { success: false, message };
  }
}

export class DovecotMailDeliverer extends MailDeliverer {
  readonly name = "dovecot";
  readonly #ldaPath;
  readonly #doveadmPath;

  constructor({ ldaPath, doveadmPath, logger }: {
    ldaPath: string;
    doveadmPath: string;
    logger: ILogger;
  }) {
    super({ sync: false, logger });
    this.#ldaPath = ldaPath;
    this.#doveadmPath = doveadmPath;
  }

  protected override async doDeliver(
    mail: Mail,
    context: MailDeliverContext,
  ): Promise<void> {
    const utf8Bytes = mail.toUtf8Bytes();

    const recipients = [...context.recipients];

    if (recipients.length === 0) {
      throw new Error(
        "Failed to deliver to dovecot, no recipients are specified.",
      );
    }

    for (const recipient of recipients) {
      const result = await runCommand(
        this.#ldaPath,
        {
          logger: NULL_LOGGER,
          args: ["-d", recipient],
          stdin: utf8Bytes,
          errorCodeMessageMap: ldaExitCodeMessageMap,
        },
      );

      context.result.recipients.set(recipient, {
        kind: result.success ? "success" : "failure",
        message: result.message,
      });
    }
  }

  #queryArgs(mailbox: string, messageId: string) {
    return ["mailbox", mailbox, "header", "Message-ID", `<${messageId}>`];
  }

  async #deleteMail(
    logger: ILogger,
    user: string,
    mailbox: string,
    messageId: string,
  ): Promise<void> {
    await runCommand(this.#doveadmPath, {
      logger,
      args: ["expunge", "-u", user, ...this.#queryArgs(mailbox, messageId)],
    });
  }

  async #saveMail(
    logger: ILogger,
    user: string,
    mailbox: string,
    mail: Uint8Array,
  ) {
    await runCommand(this.#doveadmPath, {
      logger,
      args: ["save", "-u", user, "-m", mailbox],
      stdin: mail,
    });
  }

  async #markAsRead(
    logger: ILogger,
    user: string,
    mailbox: string,
    messageId: string,
  ) {
    await runCommand(this.#doveadmPath, {
      logger,
      args: [
        "flags",
        "add",
        "-u",
        user,
        "\\Seen",
        ...this.#queryArgs(mailbox, messageId),
      ],
    });
  }

  async saveNewSent(logger: ILogger, mail: Mail, messageIdToDelete: string) {
    logger.info("Save sent mail and delete ones with old message id.");

    // Try to get from and recipients from headers.
    const { messageId, from, recipients } = mail.parsed;

    if (from == null) {
      logger.warn("Failed to get sender (from) in headers, skip saving.");
      return;
    }

    if (recipients.includes(from)) {
      // So the mail should lie in the Inbox.
      logger.info(
        "One recipient of the mail is the sender itself, skip saving.",
      );
      return;
    }

    await this.#saveMail(logger, from, "Sent", mail.toUtf8Bytes());
    if (messageId != null) {
      await this.#markAsRead(logger, from, "Sent", messageId);
    } else {
      logger.warn(
        "Message id of the mail is not found, skip marking as read.",
      );
    }

    logger.info(
      "Schedule deletion of old mails (no logging) at 5,15,30,60 seconds later.",
    );
    [5, 15, 30, 60].forEach((seconds) =>
      setTimeout(() => {
        void this.#deleteMail(NULL_LOGGER, from, "Sent", messageIdToDelete);
      }, 1000 * seconds)
    );
  }
}
