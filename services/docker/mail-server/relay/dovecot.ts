import { basename } from "@std/path";

import config from "./config.ts";
import log from "./log.ts";
import {
  Mail,
  MailDeliverContext,
  MailDeliverer,
  MailDeliverRecipientResult,
  RecipientFromHeadersHook,
} from "./mail.ts";

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
      throw new Error("No recipients found.");
    }

    log.info(`Deliver to ${recipients.join(", ")}.`);

    for (const recipient of recipients) {
      log.info(`Call ${ldaBinName} for ${recipient}...`);

      const result: MailDeliverRecipientResult = {
        kind: "done",
        message: `${ldaBinName} exited with success.`,
      };

      try {
        const ldaCommand = new Deno.Command(ldaPath, {
          args: ["-d", recipient],
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

        if (!status.success) {
          result.kind = "fail";
          result.message =
            `${ldaBinName} exited with error code ${status.code}`;

          if (status.signal != null) {
            result.message += ` (signal ${status.signal})`;
          }

          // https://doc.dovecot.org/main/core/man/dovecot-lda.1.html
          switch (status.code) {
            case 67:
              result.message += ", recipient user not known";
              break;
            case 75:
              result.kind = "retry";
              break;
          }

          result.message += ".";
        }
      } catch (e) {
        result.kind = "fail";
        result.message = "An error was thrown when running lda process: " + e;
        result.cause = e;
      }
      context.result.set(recipient, result);
    }
  }
}
