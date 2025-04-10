import { describe, it } from "@std/testing/bdd";
import { expect, fn } from "@std/expect";

import { Mail, MailDeliverer } from "./mail.ts";

const mockDate = "Fri, 02 May 2025 08:33:02 +0000";
const mockBodyStr = `This is body content.
Line 2

Line 4`;
const mockHeaders = [
  ["Content-Disposition", "inline"],
  ["Content-Transfer-Encoding", "quoted-printable"],
  ["MIME-Version", "1.0"],
  ["X-Mailer", "MIME-tools 5.509 (Entity 5.509)"],
  ["Content-Type", "text/plain; charset=utf-8"],
  ["From", '"Mock From" <mock@from.mock>'],
  [
    "To",
    `"John \\"Big\\" Doe" <john@example.com>, "Alice (Work)" <alice+work@example.com>,
 undisclosed-recipients:;, "Group: Team" <team@company.com>,
 "Escaped, Name" <escape@test.com>, just@email.com,
 "Comment (This is valid)" <comment@domain.net>,
 "Odd @Chars" <weird!#$%'*+-/=?^_\`{|}~@char-test.com>,
 "Non-ASCII 用户" <user@例子.中国>,
 admin@[192.168.1.1]`,
  ],
  ["CC", "Mock CC <mock@cc.mock>"],
  ["Subject", "A very long mock\n subject"],
  ["Message-ID", "<abcdef@from.mock>"],
  ["Date", mockDate],
];
const mockHeaderStr = mockHeaders.map((h) => h[0] + ": " + h[1]).join("\n");
const mockMailStr = mockHeaderStr + "\n\n" + mockBodyStr;
const mockCrlfMailStr = mockMailStr.replaceAll("\n", "\r\n");
const mockToAddresses = [
  "john@example.com",
  "alice+work@example.com",
  "team@company.com",
  "escape@test.com",
  "just@email.com",
  "comment@domain.net",
  "weird!#$%'*+-/=?^_`{|}~@char-test.com",
  "user@例子.中国",
  "admin@[192.168.1.1]",
];
const mockCcAddresses = ["mock@cc.mock"];

describe("Mail", () => {
  it("simple parse", () => {
    const parsed = new Mail(mockMailStr).simpleParse();
    expect(parsed.sections.header).toEqual(mockHeaderStr);
    expect(parsed.sections.body).toEqual(mockBodyStr);
    expect(parsed.sep).toBe("\n");
    expect(parsed.eol).toBe("\n");
  });

  it("simple parse crlf", () => {
    const parsed = new Mail(mockCrlfMailStr).simpleParse();
    expect(parsed.sep).toBe("\r\n");
    expect(parsed.eol).toBe("\r\n");
  });

  it("simple parse date", () => {
    expect(new Mail(mockMailStr).simpleParseDate()).toEqual(new Date(mockDate));
  });

  it("simple parse headers", () => {
    expect(
      new Mail(mockMailStr).simpleParseHeaders(),
    ).toEqual(mockHeaders.map(
      (h) => [h[0], " " + h[1].replaceAll("\n", "")],
    ));
  });

  it("append headers", () => {
    const mail = new Mail(mockMailStr);
    const mockMoreHeaders = [["abc", "123"], ["def", "456"]] satisfies [
      string,
      string,
    ][];
    mail.appendHeaders(mockMoreHeaders);

    expect(mail.raw).toBe(
      mockHeaderStr + "\n" +
        mockMoreHeaders.map((h) => h[0] + ": " + h[1]).join("\n") +
        "\n\n" + mockBodyStr,
    );
  });

  it("parse recipients", () => {
    const mail = new Mail(mockMailStr);
    expect(mail.simpleParseRecipients()).toEqual([
      ...mockToAddresses,
      ...mockCcAddresses,
    ]);
    expect(mail.simpleParseRecipients({domain: "example.com"})).toEqual([
      ...mockToAddresses,
      ...mockCcAddresses,
    ].filter(a => a.endsWith("example.com")));
  });
});

describe("MailDeliverer", () => {
  class MockMailDeliverer extends MailDeliverer {
    name = "mock";
    override doDeliver = fn() as MailDeliverer["doDeliver"];
  }
  const mockDeliverer = new MockMailDeliverer();

  it("deliver success", async () => {
    await mockDeliverer.deliverRaw(mockMailStr);
    expect(mockDeliverer.doDeliver).toHaveBeenCalledTimes(1);
  });
});
