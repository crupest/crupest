import { basename } from "@std/path";

import { Logger } from "@crupest/base/log";

import { Mail, MailDeliverContext, MailDeliverer } from "./mail.ts";

export class DovecotMailDeliverer extends MailDeliverer {
  readonly name = "dovecot";
  readonly #logger;
  readonly #ldaPath;

  constructor(logger: Logger, ldaPath: string) {
    super();
    this.#logger = logger;
    this.#ldaPath = ldaPath;
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
        using logFiles =
          await this.#logger.createExternalLogStreamsForProgram(ldaBinName);
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
}
