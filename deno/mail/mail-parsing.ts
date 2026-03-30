import emailAddresses from "email-addresses";

import { ILogger } from "@crupest/base/log";

class MailParsingError extends Error {}

function parseHeaderSection(section: string) {
  const headers = [] as [key: string, value: string][];

  let field: string | null = null;
  let lineNumber = 1;

  const handleField = () => {
    if (field == null) return;
    const sepPos = field.indexOf(":");
    if (sepPos === -1) {
      throw new MailParsingError(
        `Expect ':' in the header field line: ${field}`,
      );
    }
    headers.push([field.slice(0, sepPos).trim(), field.slice(sepPos + 1)]);
    field = null;
  };

  for (const line of section.trimEnd().split(/\r?\n|\r/)) {
    if (line.match(/^\s/)) {
      if (field == null) {
        throw new MailParsingError("Header section starts with a space.");
      }
      field += line;
    } else {
      handleField();
      field = line;
    }
    lineNumber += 1;
  }

  handleField();

  return headers;
}

function findFirst(fields: readonly [string, string][], key: string) {
  for (const [k, v] of fields) {
    if (key.toLowerCase() === k.toLowerCase()) return v;
  }
  return undefined;
}

function findMessageId(fields: readonly [string, string][], logger: ILogger) {
  const messageIdField = findFirst(fields, "message-id");
  if (messageIdField == null) return undefined;

  const match = messageIdField.match(/\<(.*?)\>/);
  if (match != null) {
    return match[1];
  } else {
    logger.warn(`Invalid syntax in header 'message-id': ${messageIdField}`);
    return undefined;
  }
}

function findDate(fields: readonly [string, string][], logger: ILogger) {
  const dateField = findFirst(fields, "date");
  if (dateField == null) return undefined;

  const date = new Date(dateField);
  if (isNaN(date.getTime())) {
    logger.warn(`Invalid date string in header 'date': ${dateField}`);
    return undefined;
  }
  return date;
}

function findFrom(fields: readonly [string, string][]) {
  const fromField = findFirst(fields, "from");
  if (fromField == null) return undefined;

  const addr = emailAddresses.parseOneAddress(fromField);
  return addr?.type === "mailbox" ? addr.address : undefined;
}

function findRecipients(fields: readonly [string, string][]) {
  const headers = ["to", "cc", "bcc", "x-original-to"];
  const recipients = new Set<string>();
  for (const [key, value] of fields) {
    if (headers.includes(key.toLowerCase())) {
      emailAddresses
        .parseAddressList(value)
        ?.flatMap((a) => (a.type === "mailbox" ? a : a.addresses))
        ?.forEach(({ address }) => recipients.add(address));
    }
  }
  return recipients;
}

function parseSections(raw: string, logger: ILogger) {
  const twoEolMatch = raw.match(/(\r?\n)(\r?\n)/);
  if (twoEolMatch == null) {
    throw new MailParsingError(
      "No header/body section separator (2 successive EOLs) found.",
    );
  }

  const [eol, sep] = [twoEolMatch[1], twoEolMatch[2]];

  if (eol !== sep) {
    logger.warn("Different EOLs (\\r\\n, \\n) found.");
  }

  return {
    header: raw.slice(0, twoEolMatch.index!),
    body: raw.slice(twoEolMatch.index! + eol.length + sep.length),
    eol,
    sep,
  };
}

export type ParsedMail = Readonly<{
  header: string;
  body: string;
  sep: string;
  eol: string;
  headers: readonly [string, string][];
  messageId: string | undefined;
  date: Date | undefined;
  from: string | undefined;
  recipients: readonly string[];
}>;

export function simpleParseMail(raw: string, logger: ILogger): ParsedMail {
  const sections = Object.freeze(parseSections(raw, logger));
  const headers = Object.freeze(parseHeaderSection(sections.header));
  const messageId = findMessageId(headers, logger);
  const date = findDate(headers, logger);
  const from = findFrom(headers);
  const recipients = Object.freeze([...findRecipients(headers)]);
  return Object.freeze({
    ...sections,
    headers,
    messageId,
    date,
    from,
    recipients,
  });
}
