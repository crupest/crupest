import { describe, it } from "@std/testing/bdd";
import { expect } from "@std/expect/expect";

import { DbService } from "./db.ts";

describe("DbService", () => {
  const mockRow = {
    message_id: "mock-message-id@mock.mock",
    aws_message_id: "mock-aws-message-id@mock.mock",
  };

  it("works", async () => {
    const db = new DbService(":memory:");
    await db.migrate();
    await db.addMessageIdMap(mockRow);
    expect(await db.messageIdToAws(mockRow.message_id)).toBe(
      mockRow.aws_message_id,
    );
    expect(await db.messageIdFromAws(mockRow.aws_message_id)).toBe(
      mockRow.message_id,
    );
  });
});
