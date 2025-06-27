import {
  CopyObjectCommand,
  DeleteObjectCommand,
  GetObjectCommand,
  ListObjectsV2Command,
  NoSuchKey,
  S3Client,
  S3ClientConfig,
} from "@aws-sdk/client-s3";

import { DateUtils } from "@crupest/base";

import { Mail } from "../mail.ts";
import { MailDeliverer } from "../mail.ts";

export class LiveMailNotFoundError extends Error {}

async function s3MoveObject(
  client: S3Client,
  bucket: string,
  path: string,
  newPath: string,
): Promise<void> {
  const copyCommand = new CopyObjectCommand({
    Bucket: bucket,
    Key: newPath,
    CopySource: `${bucket}/${path}`,
  });
  await client.send(copyCommand);

  const deleteCommand = new DeleteObjectCommand({
    Bucket: bucket,
    Key: path,
  });
  await client.send(deleteCommand);
}

const AWS_SES_S3_SETUP_TAG = "AMAZON_SES_SETUP_NOTIFICATION";

export class AwsMailFetcher {
  readonly #livePrefix = "mail/live/";
  readonly #archivePrefix = "mail/archive/";
  readonly #s3;
  readonly #bucket;

  constructor(aws: S3ClientConfig, bucket: string) {
    this.#s3 = new S3Client(aws);
    this.#bucket = bucket;
  }

  async listLiveMails(): Promise<string[]> {
    const listCommand = new ListObjectsV2Command({
      Bucket: this.#bucket,
      Prefix: this.#livePrefix,
    });
    const res = await this.#s3.send(listCommand);

    if (res.Contents == null) {
      console.warn("S3 API returned null Content.");
      return [];
    }

    const result: string[] = [];
    for (const object of res.Contents) {
      if (object.Key == null) {
        console.warn("S3 API returned null Key.");
        continue;
      }

      if (object.Key.endsWith(AWS_SES_S3_SETUP_TAG)) continue;

      result.push(object.Key.slice(this.#livePrefix.length));
    }
    return result;
  }

  async deliverLiveMail(
    logTag: string,
    s3Key: string,
    deliverer: MailDeliverer,
    recipients?: string[],
  ) {
    console.info(logTag, `Fetching live mail ${s3Key}...`);
    const mailPath = `${this.#livePrefix}${s3Key}`;
    const command = new GetObjectCommand({
      Bucket: this.#bucket,
      Key: mailPath,
    });

    let rawMail;

    try {
      const res = await this.#s3.send(command);
      if (res.Body == null) {
        throw new Error("S3 API returns a null body.");
      }
      rawMail = await res.Body.transformToString();
    } catch (cause) {
      if (cause instanceof NoSuchKey) {
        const message =
          `Live mail  ${s3Key} is not found. Perhaps already delivered?`;
        console.error(message, cause);
        throw new LiveMailNotFoundError(message);
      }
      throw cause;
    }

    const mail = new Mail(rawMail);
    await deliverer.deliver({ mail, recipients });

    const { date } = new Mail(rawMail).parsed;
    const dateString = date != null
      ? DateUtils.toFileNameString(date, true)
      : "invalid-date";
    const newPath = `${this.#archivePrefix}${dateString}/${s3Key}`;

    console.info(logTag, `Archiving live mail ${s3Key} to ${newPath}...`);
    await s3MoveObject(this.#s3, this.#bucket, mailPath, newPath);

    console.info(logTag, `Done deliver live mail ${s3Key}.`);
  }

  async recycleLiveMails(deliverer: MailDeliverer) {
    console.info("Begin to recycle live mails...");
    const mails = await this.listLiveMails();
    console.info(`Found ${mails.length} live mails`);
    let counter = 1;
    for (const s3Key of mails) {
      await this.deliverLiveMail(
        `[${counter++}/${mails.length}]`,
        s3Key,
        deliverer,
      );
    }
  }
}
