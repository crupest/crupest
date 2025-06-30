import { Mail, MailDeliverContext, MailDeliverer } from "./mail.ts";

// https://doc.dovecot.org/main/core/man/dovecot-lda.1.html
const ldaExitCodeMessageMap = new Map<number, string>();
ldaExitCodeMessageMap.set(67, "recipient user not known");
ldaExitCodeMessageMap.set(75, "temporary error");

type CommandResult = {
  kind: "exit";
  status: Deno.CommandStatus;
  logMessage: string;
} | { kind: "throw"; cause: unknown; logMessage: string };

async function runCommand(
  bin: string,
  options: {
    logTag: string;
    args: string[];
    stdin?: Uint8Array;
    suppressResultLog?: boolean;
    errorCodeMessageMap?: Map<number, string>;
  },
): Promise<CommandResult> {
  const { logTag, args, stdin, suppressResultLog, errorCodeMessageMap } =
    options;

  console.info(logTag, `Run external command ${bin} ${args.join(" ")}`);

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

    // Build log message string.
    let message = `External command exited with code ${status.code}`;
    if (status.signal != null) message += ` (signal: ${status.signal})`;
    if (errorCodeMessageMap != null && errorCodeMessageMap.has(status.code)) {
      message += `, ${errorCodeMessageMap.get(status.code)}`;
    }
    message += ".";
    if (suppressResultLog !== true) console.log(logTag, message);

    // Return result.
    return {
      kind: "exit",
      status,
      logMessage: message,
    };
  } catch (cause) {
    const message = `A JS error was thrown when invoking external command:`;
    if (suppressResultLog !== true) console.log(logTag, message);
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
    super(false);
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
          logTag: context.logTag,
          args: ["-d", recipient],
          stdin: utf8Bytes,
          suppressResultLog: true,
          errorCodeMessageMap: ldaExitCodeMessageMap,
        },
      );

      if (result.kind === "exit" && result.status.success) {
        context.result.recipients.set(recipient, {
          kind: "success",
          message: result.logMessage,
        });
      } else {
        context.result.recipients.set(recipient, {
          kind: "failure",
          message: result.logMessage,
        });
      }
    }
  }

  #queryArgs(mailbox: string, messageId: string) {
    return ["mailbox", mailbox, "header", "Message-ID", `<${messageId}>`];
  }

  async #deleteMail(
    logTag: string,
    user: string,
    mailbox: string,
    messageId: string,
  ): Promise<void> {
    await runCommand(this.#doveadmPath, {
      logTag,
      args: ["expunge", "-u", user, ...this.#queryArgs(mailbox, messageId)],
    });
  }

  async #saveMail(
    logTag: string,
    user: string,
    mailbox: string,
    mail: Uint8Array,
  ) {
    await runCommand(this.#doveadmPath, {
      logTag,
      args: ["save", "-u", user, "-m", mailbox],
      stdin: mail,
    });
  }

  async #markAsRead(
    logTag: string,
    user: string,
    mailbox: string,
    messageId: string,
  ) {
    await runCommand(this.#doveadmPath, {
      logTag,
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

  async saveNewSent(logTag: string, mail: Mail, messageIdToDelete: string) {
    console.info(logTag, "Save sent mail and delete ones with old message id.");

    // Try to get from and recipients from headers.
    const { messageId, from, recipients } = mail.parsed;

    if (from == null) {
      console.warn(
        logTag,
        "Failed to get sender (from) in headers, skip saving.",
      );
      return;
    }

    if (recipients.includes(from)) {
      // So the mail should lie in the Inbox.
      console.info(
        logTag,
        "One recipient of the mail is the sender itself, skip saving.",
      );
      return;
    }

    await this.#saveMail(logTag, from, "Sent", mail.toUtf8Bytes());
    if (messageId != null) {
      await this.#markAsRead(logTag, from, "Sent", messageId);
    } else {
      console.warn(
        "Message id of the mail is not found, skip marking as read.",
      );
    }

    console.info(
      logTag,
      "Schedule deletion of old mails at 15,30,60 seconds later.",
    );
    [15, 30, 60].forEach((seconds) =>
      setTimeout(() => {
        void this.#deleteMail(logTag, from, "Sent", messageIdToDelete);
      }, 1000 * seconds)
    );
  }
}
