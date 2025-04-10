import { basename } from "@std/path";

import config from "../config.ts";
import log from "../log.ts";
import {
  Mail,
  MailDeliverContext,
  MailDeliverer,
  RecipientFromHeadersHook,
} from "../mail.ts";

export class DovecotMailDeliverer extends MailDeliverer {
  readonly name = "dovecot";

  constructor() {
    super();
    this.preHooks.push(
      new RecipientFromHeadersHook(),
    );
  }

  protected override async doDeliver(
    mail: Mail,
    context: MailDeliverContext,
  ): Promise<void> {
    const ldaPath = config.get("ldaPath");
    const ldaBinName = basename(ldaPath);
    const utf8Stream = mail.toUtf8Bytes();

    const recipients = [...context.recipients];

    if (recipients.length === 0) {
      context.result.message =
        "Failed to deliver to dovecot, no recipients are specified.";
      return;
    }

    log.info(`Deliver to dovecot users: ${recipients.join(", ")}.`);

    for (const recipient of recipients) {
      try {
        const commandArgs = ["-d", recipient];
        log.info(
          `Run ${ldaBinName} ${commandArgs.join(" ")}...`,
        );

        const ldaCommand = new Deno.Command(ldaPath, {
          args: commandArgs,
          stdin: "piped",
          stdout: "piped",
          stderr: "piped",
        });

        const ldaProcess = ldaCommand.spawn();
        using logFiles = await log.openLogForProgram(ldaBinName);
        ldaProcess.stdout.pipeTo(logFiles.stdout.writable);
        ldaProcess.stderr.pipeTo(logFiles.stderr.writable);

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

    log.info("Done handling all recipients.");
  }
}
