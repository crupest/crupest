import BetterSqlite3 from "better-sqlite3";
import { type Generated, type Insertable, Kysely, SqliteDialect } from "kysely";
import { type Migration, Migrator } from "kysely/migration";

export class DbError extends Error {}

interface MessageIdMapTable {
  id: Generated<number>;
  message_id: string;
  new_message_id: string;
}

interface Database {
  message_id_map: MessageIdMapTable;
}

const migrations: Record<string, Migration> = {
  "0001-init": {
    async up(db: Kysely<unknown>): Promise<void> {
      await db.schema
        .createTable("message_id_map")
        .addColumn("id", "integer", (col) => col.primaryKey().autoIncrement())
        .addColumn("message_id", "text", (col) => col.notNull().unique())
        .addColumn("new_message_id", "text", (col) => col.notNull().unique())
        .execute();

      for (const column of ["message_id", "new_message_id"] as const) {
        await db.schema
          .createIndex(`message_id_map_${column}`)
          .on("message_id_map")
          .column(column)
          .execute();
      }
    },

    async down(db: Kysely<unknown>): Promise<void> {
      await db.schema.dropTable("message_id_map").execute();
    },
  },
};

export class DbService {
  readonly #kysely: Kysely<Database>;
  readonly #migrator: Migrator;

  constructor(public readonly path: string) {
    this.#kysely = new Kysely<Database>({
      dialect: new SqliteDialect({
        database: new BetterSqlite3(path),
      }),
    });
    this.#migrator = new Migrator({
      db: this.#kysely,
      provider: {
        getMigrations(): Promise<Record<string, Migration>> {
          return Promise.resolve(migrations);
        },
      },
    });
  }

  async migrate(): Promise<void> {
    const result = await this.#migrator.migrateToLatest();
    if (result.error != null) {
      throw new DbError("Failed to migrate mail database.", {
        cause: result.error,
      });
    }
  }

  async addMessageIdMap(mail: Insertable<MessageIdMapTable>): Promise<number> {
    const inserted = await this.#kysely
      .insertInto("message_id_map")
      .values(mail)
      .executeTakeFirstOrThrow();
    return Number(inserted.insertId!);
  }

  async messageIdToNew(messageId: string): Promise<string | null> {
    const row = await this.#kysely
      .selectFrom("message_id_map")
      .where("message_id", "=", messageId)
      .select("new_message_id")
      .executeTakeFirst();
    return row?.new_message_id ?? null;
  }

  async messageIdFromNew(newMessageId: string): Promise<string | null> {
    const row = await this.#kysely
      .selectFrom("message_id_map")
      .where("new_message_id", "=", newMessageId)
      .select("message_id")
      .executeTakeFirst();
    return row?.message_id ?? null;
  }

  async close(): Promise<void> {
    await this.#kysely.destroy();
  }
}
