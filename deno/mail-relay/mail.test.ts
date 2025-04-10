import { describe, it } from "@std/testing/bdd";
import { expect, fn } from "@std/expect";

import { Mail, MailDeliverContext, MailDeliverer } from "./mail.ts";

const mockDate = "Fri, 02 May 2025 08:33:02 +0000";
const mockMessageId = "mock-message-id@from.mock";
const mockMessageId2 = "mock-message-id-2@from.mock";
const mockFromAddress = "mock@from.mock";
const mockCcAddress = "mock@cc.mock";
const mockBodyStr = `This is body content.
Line 2 ${mockMessageId2}

Line 4`;
const mockHeaders = [
  ["Content-Disposition", "inline"],
  ["Content-Transfer-Encoding", "quoted-printable"],
  ["MIME-Version", "1.0"],
  ["X-Mailer", "MIME-tools 5.509 (Entity 5.509)"],
  ["Content-Type", "text/plain; charset=utf-8"],
  ["From", `"Mock From" <${mockFromAddress}>`],
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
  ["CC", `Mock CC <${mockCcAddress}>`],
  ["Subject", "A very long mock\n subject"],
  ["Message-ID", `<${mockMessageId}>`],
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

describe("Mail", () => {
  it("simple parse", () => {
    const parsed = new Mail(mockMailStr).startSimpleParse().sections();
    expect(parsed.header).toEqual(mockHeaderStr);
    expect(parsed.body).toEqual(mockBodyStr);
    expect(parsed.sep).toBe("\n");
    expect(parsed.eol).toBe("\n");
  });

  it("simple parse crlf", () => {
    const parsed = new Mail(mockCrlfMailStr).startSimpleParse().sections();
    expect(parsed.sep).toBe("\r\n");
    expect(parsed.eol).toBe("\r\n");
  });

  it("simple parse date", () => {
    expect(new Mail(mockMailStr).startSimpleParse().sections().headers().date())
      .toEqual(new Date(mockDate));
  });

  it("simple parse headers", () => {
    expect(
      new Mail(mockMailStr).startSimpleParse().sections().headers(),
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
    expect([...mail.startSimpleParse().sections().headers().recipients()])
      .toEqual([
        ...mockToAddresses,
        mockCcAddress,
      ]);
    expect([
      ...mail.startSimpleParse().sections().headers().recipients({
        domain: "example.com",
      }),
    ]).toEqual([
      ...mockToAddresses,
      mockCcAddress,
    ].filter((a) => a.endsWith("example.com")));
  });

  it("find all addresses", () => {
    const mail = new Mail(mockMailStr);
    expect(mail.simpleFindAllAddresses()).toEqual([
      "mock@from.mock",
      "john@example.com",
      "alice+work@example.com",
      "team@company.com",
      "escape@test.com",
      "just@email.com",
      "comment@domain.net",
      "mock@cc.mock",
      "mock-message-id@from.mock",
      "mock-message-id-2@from.mock",
    ]);
  });
});

describe("MailDeliverer", () => {
  class MockMailDeliverer extends MailDeliverer {
    name = "mock";
    override doDeliver = fn((_: Mail, ctx: MailDeliverContext) => {
      ctx.result.recipients.set("*", { kind: "done", message: "success" });
      return Promise.resolve();
    }) as MailDeliverer["doDeliver"];
  }
  const mockDeliverer = new MockMailDeliverer();

  it("deliver success", async () => {
    await mockDeliverer.deliverRaw(mockMailStr);
    expect(mockDeliverer.doDeliver).toHaveBeenCalledTimes(1);
  });
});
