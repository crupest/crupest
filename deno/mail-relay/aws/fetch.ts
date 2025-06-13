import {
  CopyObjectCommand,
  DeleteObjectCommand,
  GetObjectCommand,
  ListObjectsV2Command,
  S3Client,
  S3ClientConfig,
} from "@aws-sdk/client-s3";

import { toFileNameString } from "@crupest/base";

import { Mail } from "../mail.ts";

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

export type AwsS3MailConsumer = (
  rawMail: string,
  s3Key: string,
) => Promise<void>;

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
    console.info("Begin to retrieve live mails.");

    const listCommand = new ListObjectsV2Command({
      Bucket: this.#bucket,
      Prefix: this.#livePrefix,
    });
    const res = await this.#s3.send(listCommand);

    if (res.Contents == null) {
      console.warn("Listing live mails in S3 returns null Content.");
      return [];
    }

    const result: string[] = [];
    for (const object of res.Contents) {
      if (object.Key == null) {
        console.warn("Listing live mails in S3 returns an object with no Key.");
        continue;
      }

      if (object.Key.endsWith(AWS_SES_S3_SETUP_TAG)) continue;

      result.push(object.Key.slice(this.#livePrefix.length));
    }
    return result;
  }

  async consumeS3Mail(s3Key: string, consumer: AwsS3MailConsumer) {
    console.info(`Begin to consume s3 mail ${s3Key} ...`);

    console.info(`Fetching s3 mail ${s3Key}...`);
    const mailPath = `${this.#livePrefix}${s3Key}`;
    const command = new GetObjectCommand({
      Bucket: this.#bucket,
      Key: mailPath,
    });
    const res = await this.#s3.send(command);

    if (res.Body == null) {
      throw new Error("S3 mail returns a null body.");
    }

    const rawMail = await res.Body.transformToString();
    console.info(`Done fetching s3 mail ${s3Key}.`);

    console.info(`Calling consumer...`);
    await consumer(rawMail, s3Key);
    console.info(`Done consuming s3 mail ${s3Key}.`);

    const date = new Mail(rawMail)
      .startSimpleParse()
      .sections()
      .headers()
      .date();
    const dateString = date != null
      ? toFileNameString(date, true)
      : "invalid-date";
    const newPath = `${this.#archivePrefix}${dateString}/${s3Key}`;

    console.info(`Archiving s3 mail ${s3Key} to ${newPath}...`);
    await s3MoveObject(this.#s3, this.#bucket, mailPath, newPath);
    console.info(`Done archiving s3 mail ${s3Key}.`);

    console.info(`Done consuming s3 mail ${s3Key}.`);
  }

  async recycleLiveMails(consumer: AwsS3MailConsumer) {
    console.info("Begin to recycle live mails...");
    const mails = await this.listLiveMails();
    console.info(`Found ${mails.length} live mails`);
    for (const s3Key of mails) {
      await this.consumeS3Mail(s3Key, consumer);
    }
  }
}
