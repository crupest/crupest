import { basename } from "@std/path";

import { LogFileProvider } from "@crupest/base/log";

import { Mail, MailDeliverContext, MailDeliverer } from "./mail.ts";

export class DovecotMailDeliverer extends MailDeliverer {
  readonly name = "dovecot";
  readonly #logFileProvider;
  readonly #ldaPath;
  readonly #doveadmPath;

  constructor(
    logFileProvider: LogFileProvider,
    ldaPath: string,
    doveadmPath: string,
  ) {
    super();
    this.#logFileProvider = logFileProvider;
    this.#ldaPath = ldaPath;
    this.#doveadmPath = doveadmPath;
  }

  protected override async doDeliver(
    mail: Mail,
    context: MailDeliverContext,
  ): Promise<void> {
    const ldaPath = this.#ldaPath;
    const ldaBinName = basename(ldaPath);
    const utf8Stream = mail.toUtf8Bytes();

    const recipients = [...context.recipients];

    if (recipients.length === 0) {
      context.result.message =
        "Failed to deliver to dovecot, no recipients are specified.";
      return;
    }

    console.info(`Deliver to dovecot users: ${recipients.join(", ")}.`);

    for (const recipient of recipients) {
      try {
        const commandArgs = ["-d", recipient];
        console.info(`Run ${ldaBinName} ${commandArgs.join(" ")}...`);

        const ldaCommand = new Deno.Command(ldaPath, {
          args: commandArgs,
          stdin: "piped",
          stdout: "piped",
          stderr: "piped",
        });

        const ldaProcess = ldaCommand.spawn();
        using logFiles = await this.#logFileProvider
          .createExternalLogStreamsForProgram(
            ldaBinName,
          );
        ldaProcess.stdout.pipeTo(logFiles.stdout);
        ldaProcess.stderr.pipeTo(logFiles.stderr);

        const stdinWriter = ldaProcess.stdin.getWriter();
        await stdinWriter.write(utf8Stream);
        await stdinWriter.close();

        const status = await ldaProcess.status;

        if (status.success) {
          context.result.recipients.set(recipient, {
            kind: "done",
            message: `${ldaBinName} exited with success.`,
          });
        } else {
          let message = `${ldaBinName} exited with error code ${status.code}`;

          if (status.signal != null) {
            message += ` (signal ${status.signal})`;
          }

          // https://doc.dovecot.org/main/core/man/dovecot-lda.1.html
          switch (status.code) {
            case 67:
              message += ", recipient user not known";
              break;
            case 75:
              message += ", temporary error";
              break;
          }

          message += ".";

          context.result.recipients.set(recipient, { kind: "fail", message });
        }
      } catch (cause) {
        context.result.recipients.set(recipient, {
          kind: "fail",
          message: "An error is thrown when running lda: " + cause,
          cause,
        });
      }
    }

    console.info("Done handling all recipients.");
  }

  async #deleteMail(
    user: string,
    mailbox: string,
    messageId: string,
  ): Promise<void> {
    try {
      const args = [
        "expunge",
        "-u",
        user,
        "mailbox",
        mailbox,
        "header",
        "Message-ID",
        `<${messageId}>`,
      ];
      console.info(
        `Run external command ${this.#doveadmPath} ${args.join(" ")} ...`,
      );
      const command = new Deno.Command(this.#doveadmPath, { args });
      const status = await command.spawn().status;
      if (status.success) {
        console.info("Expunged successfully.");
      } else {
        console.warn("Expunging failed with exit code %d.", status.code);
      }
    } catch (cause) {
      console.warn("Expunging failed with an error thrown: ", cause);
    }
  }

  async #saveMail(user: string, mailbox: string, mail: Uint8Array) {
    try {
      const args = ["save", "-u", user, "-m", mailbox];
      console.info(
        `Run external command ${this.#doveadmPath} ${args.join(" ")} ...`,
      );
      const command = new Deno.Command(this.#doveadmPath, {
        args,
        stdin: "piped",
      });
      const process = command.spawn();
      const stdinWriter = process.stdin.getWriter();
      await stdinWriter.write(mail);
      await stdinWriter.close();
      const status = await process.status;

      if (status.success) {
        console.info("Saved successfully.");
      } else {
        console.warn("Saving failed with exit code %d.", status.code);
      }
    } catch (cause) {
      console.warn("Saving failed with an error thrown: ", cause);
    }
  }

  async saveNewSent(originalMessageId: string, mail: Mail) {
    console.info(
      "Try to save mail with new id and delete mail with old id in Sent box.",
    );
    const from = mail.startSimpleParse().sections().headers()
      .from();
    if (from != null) {
      console.info("Parsed sender (from): ", from);
      await this.#saveMail(from, "Sent", mail.toUtf8Bytes());
      setTimeout(() => {
        console.info(
          "Try to delete mail in Sent box that has old message id.",
        );
        this.#deleteMail(from, "Sent", originalMessageId);
      }, 1000 * 15);
    } else {
      console.warn("Failed to determine from.");
    }
  }
}
