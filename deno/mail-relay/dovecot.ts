import { Mail, MailDeliverContext, MailDeliverer } from "./mail.ts";

// https://doc.dovecot.org/main/core/man/dovecot-lda.1.html
const ldaExitCodeMessageMap = new Map<number, string>();
ldaExitCodeMessageMap.set(67, "recipient user not known");
ldaExitCodeMessageMap.set(75, "temporary error");

type CommandResult = {
  kind: "exit-success" | "exit-failure";
  status: Deno.CommandStatus;
  logMessage: string;
} | { kind: "throw"; cause: unknown; logMessage: string };

async function runCommand(
  bin: string,
  options: {
    args: string[];
    stdin?: Uint8Array;
    errorCodeMessageMap?: Map<number, string>;
  },
): Promise<CommandResult> {
  const { args, stdin, errorCodeMessageMap } = options;

  console.info(`Run external command ${bin} ${args.join(" ")}`);

  try {
    // Create and spawn process.
    const command = new Deno.Command(bin, {
      args,
      stdin: stdin == null ? "null" : "piped",
    });
    const process = command.spawn();

    // Write stdin if any.
    if (stdin != null) {
      console.info("Write stdin...");
      const writer = process.stdin.getWriter();
      await writer.write(stdin);
      writer.close();
    }

    // Wait for process to exit.
    const status = await process.status;

    // Build log message string.
    let message = `Command exited with code ${status.code}`;
    if (status.signal != null) message += ` (signal: ${status.signal})`;
    if (errorCodeMessageMap != null && errorCodeMessageMap.has(status.code)) {
      message += `, ${errorCodeMessageMap.get(status.code)}`;
    }
    message += ".";
    console.log(message);

    // Return result.
    return {
      kind: status.success ? "exit-success" : "exit-failure",
      status,
      logMessage: message,
    };
  } catch (cause) {
    const message = "Running command threw an error:";
    console.log(message, cause);
    return { kind: "throw", cause, logMessage: message + " " + cause };
  }
}

export class DovecotMailDeliverer extends MailDeliverer {
  readonly name = "dovecot";
  readonly #ldaPath;
  readonly #doveadmPath;

  constructor(
    ldaPath: string,
    doveadmPath: string,
  ) {
    super();
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
      context.result.smtpMessage =
        "Failed to deliver to dovecot, no recipients are specified.";
      return;
    }

    console.info(`Deliver to dovecot users: ${recipients.join(", ")}.`);

    for (const recipient of recipients) {
      const result = await runCommand(
        this.#ldaPath,
        {
          args: ["-d", recipient],
          stdin: utf8Bytes,
        },
      );

      if (result.kind === "exit-success") {
        context.result.recipients.set(recipient, {
          kind: "done",
          message: result.logMessage,
        });
      } else {
        context.result.recipients.set(recipient, {
          kind: "fail",
          message: result.logMessage,
        });
      }
    }

    console.info("Done handling all recipients.");
  }

  #queryArgs(mailbox: string, messageId: string) {
    return ["mailbox", mailbox, "header", "Message-ID", `<${messageId}>`];
  }

  async #deleteMail(
    user: string,
    mailbox: string,
    messageId: string,
  ): Promise<void> {
    console.info(
      `Find and delete mails (user: ${user}, message-id: ${messageId}, mailbox: ${mailbox}).`,
    );
    await runCommand(this.#doveadmPath, {
      args: ["expunge", "-u", user, ...this.#queryArgs(mailbox, messageId)],
    });
  }

  async #saveMail(user: string, mailbox: string, mail: Uint8Array) {
    console.info(`Save a mail (user: ${user}, mailbox: ${mailbox}).`);
    await runCommand(this.#doveadmPath, {
      args: ["save", "-u", user, "-m", mailbox],
      stdin: mail,
    });
  }

  async #markAsRead(user: string, mailbox: string, messageId: string) {
    console.info(
      `Mark mails as \\Seen(user: ${user}, message-id: ${messageId}, mailbox: ${mailbox}, user: ${user}).`,
    );
    await runCommand(this.#doveadmPath, {
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

  async saveNewSent(mail: Mail, messageIdToDelete: string) {
    console.info("Save sent mails and delete ones with old message id.");

    // Try to get from and recipients from headers.
    const headers = mail.startSimpleParse().sections().headers();
    const from = headers.from(),
      recipients = headers.recipients(),
      messageId = headers.messageId();

    if (from == null) {
      console.warn("Failed to determine from from headers, skip saving.");
      return;
    }

    console.info("Parsed from: ", from);

    if (recipients.has(from)) {
      // So the mail should lie in the Inbox.
      console.info(
        "The mail has the sender itself as one of recipients, skip saving.",
      );
      return;
    }

    await this.#saveMail(from, "Sent", mail.toUtf8Bytes());
    if (messageId != null) {
      console.info("Mark sent mail as read.");
      await this.#markAsRead(from, "Sent", messageId);
    } else {
      console.warn(
        "New message id of the mail is not found, skip marking as read.",
      );
    }

    console.info("Schedule deletion of old mails at 15,30,60 seconds later.");
    [15, 30, 60].forEach((seconds) =>
      setTimeout(() => {
        console.info(
          `Try to delete mails in Sent. (message-id: ${messageIdToDelete}, ` +
            `attempt delay: ${seconds}s) ` +
            "Note that the mail may have already been deleted," +
            " in which case failures of deletion can be just ignored.",
        );
        void this.#deleteMail(from, "Sent", messageIdToDelete);
      }, 1000 * seconds)
    );
  }
}
