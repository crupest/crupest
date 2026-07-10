import { describe, expect, it } from "vitest";

import { DbService } from "./db.js";

describe("DbService", () => {
  const mockRow = {
    message_id: "mock-message-id@mock.mock",
    new_message_id: "mock-new-message-id@mock.mock",
  };

  it("works", async () => {
    const db = new DbService(":memory:");
    await db.migrate();
    await db.addMessageIdMap(mockRow);
    expect(await db.messageIdToNew(mockRow.message_id)).toBe(
      mockRow.new_message_id,
    );
    expect(await db.messageIdFromNew(mockRow.new_message_id)).toBe(
      mockRow.message_id,
    );
    await db.close();
  });
});
