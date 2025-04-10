/// <reference types="npm:@types/node" />

import {
  GetObjectCommand,
  ListObjectsV2Command,
  S3Client,
} from "@aws-sdk/client-s3";

import log from "../log.ts";
import config from "../config.ts";
import "../better-js.ts";

import { Mail, MailDeliverer } from "../mail.ts";
import { AwsContext, s3MoveObject } from "./context.ts";

const AWS_SES_S3_SETUP_TAG = "AMAZON_SES_SETUP_NOTIFICATION";

export class AwsMailRetriever {
  readonly liveMailPrefix = "mail/live/";
  readonly archiveMailPrefix = "mail/archive/";
  readonly mailBucket = config.get("awsMailBucket");

  readonly #s3;

  constructor(
    aws: AwsContext,
    public readonly inboundDeliverer: MailDeliverer,
  ) {
    this.#s3 = new S3Client(aws);
  }

  async listLiveMails(): Promise<string[]> {
    log.info("Begin to retrieve live mails.");

    const listCommand = new ListObjectsV2Command({
      Bucket: this.mailBucket,
      Prefix: this.liveMailPrefix,
    });
    const res = await this.#s3.send(listCommand);

    if (res.Contents == null) {
      log.warn("Listing live mails in S3 returns null Content.");
      return [];
    }

    const result: string[] = [];
    for (const object of res.Contents) {
      if (object.Key == null) {
        log.warn("Listing live mails in S3 returns an object with no Key.");
        continue;
      }

      if (object.Key.endsWith(AWS_SES_S3_SETUP_TAG)) continue;

      result.push(object.Key.slice(this.liveMailPrefix.length));
    }
    return result;
  }

  async deliverS3Mail(s3Key: string, recipients: string[] = []) {
    log.info(`Begin to deliver s3 mail ${s3Key} to ${recipients.join(" ")}...`);

    log.info(`Fetching s3 mail ${s3Key}...`);
    const mailPath = `${this.liveMailPrefix}${s3Key}`;
    const command = new GetObjectCommand({
      Bucket: this.mailBucket,
      Key: mailPath,
    });
    const res = await this.#s3.send(command);

    if (res.Body == null) {
      throw new Error("S3 mail returns a null body.");
    }

    const rawMail = await res.Body.transformToString();
    log.info(`Done fetching s3 mail ${s3Key}.`);

    log.info(`Delivering s3 mail ${s3Key}...`);
    const mail = new Mail(rawMail);
    await this.inboundDeliverer.deliver({ mail, recipients: recipients });
    log.info(`Done delivering s3 mail ${s3Key}.`);

    const date = mail.startSimpleParse().sections().headers().date();
    const dateString = date?.toFileNameString(true) ?? "invalid-date";
    const newPath = `${this.archiveMailPrefix}${dateString}/${s3Key}`;

    log.info(`Archiving s3 mail ${s3Key} to ${newPath}...`);
    await s3MoveObject(this.#s3, this.mailBucket, mailPath, newPath);
    log.info(`Done delivering s3 mail ${s3Key}...`);
  }

  async recycleLiveMails() {
    log.info("Begin to recycle live mails...");
    const mails = await this.listLiveMails();
    log.info(`Found ${mails.length} live mails`);
    for (const s3Key of mails) {
      await this.deliverS3Mail(s3Key);
    }
  }
}
