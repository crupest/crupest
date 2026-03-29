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
import { ILogger } from "@crupest/base/log";

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
  readonly #logger;

  constructor(
    { aws, bucket, logger }: {
      aws: S3ClientConfig;
      bucket: string;
      logger: ILogger;
    },
  ) {
    this.#s3 = new S3Client(aws);
    this.#bucket = bucket;
    this.#logger = logger;
  }

  async listLiveMails(): Promise<string[]> {
    const listCommand = new ListObjectsV2Command({
      Bucket: this.#bucket,
      Prefix: this.#livePrefix,
    });
    const res = await this.#s3.send(listCommand);

    if (res.Contents == null) {
      this.#logger.warn("S3 API returned null Content.");
      return [];
    }

    const result: string[] = [];
    for (const object of res.Contents) {
      if (object.Key == null) {
        this.#logger.warn("S3 API returned null Key.");
        continue;
      }

      if (object.Key.endsWith(AWS_SES_S3_SETUP_TAG)) continue;

      result.push(object.Key.slice(this.#livePrefix.length));
    }
    return result;
  }

  async deliverLiveMail(
    s3Key: string,
    deliverer: MailDeliverer,
    recipients?: string[],
  ) {
    this.#logger.info(`Fetching live mail ${s3Key}...`);
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
        this.#logger.warn(message);
        throw new LiveMailNotFoundError(message);
      }
      throw cause;
    }

    const result = await deliverer.deliver({ mail: rawMail, recipients });

    const { date } = result.mail.parsed;
    const dateString = date != null
      ? DateUtils.toFileNameString(date, true)
      : "invalid-date";
    const newPath = `${this.#archivePrefix}${dateString}/${s3Key}`;

    this.#logger.info(`Archiving live mail ${s3Key} to ${newPath}...`);
    await s3MoveObject(this.#s3, this.#bucket, mailPath, newPath);

    this.#logger.info(`Done deliver live mail ${s3Key}.`);
  }

  async recycleLiveMails(deliverer: MailDeliverer) {
    this.#logger.info("Begin to recycle live mails...");
    const mails = await this.listLiveMails();
    this.#logger.info(`Found ${mails.length} live mails`);
    for (const s3Key of mails) {
      await this.deliverLiveMail(s3Key, deliverer);
    }
  }
}
