export * from "../mail.ts";

declare module "../mail.ts" {
  interface Mail {
    awsMessageId?: string;
  }
}
