import {
  CopyObjectCommand,
  DeleteObjectCommand,
  S3Client,
} from "@aws-sdk/client-s3";
import { FetchHttpHandler } from "@smithy/fetch-http-handler";

import config from "../config.ts";

export class AwsContext {
  readonly credentials = () =>
    Promise.resolve({
      accessKeyId: config.get("awsUser"),
      secretAccessKey: config.get("awsPassword"),
    });
  readonly requestHandler = new FetchHttpHandler();

  get region() {
    return config.get("awsRegion");
  }
}

export async function s3MoveObject(
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
