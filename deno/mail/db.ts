import {
  Generated,
  Insertable,
  Kysely,
  Migration,
  Migrator,
  SqliteDatabase,
  SqliteDialect,
  SqliteStatement,
} from "kysely";
import * as sqlite from "@db/sqlite";

class SqliteStatementAdapter implements SqliteStatement {
  constructor(public readonly stmt: sqlite.Statement) {}

  get reader(): boolean {
    return this.stmt.columnNames().length >= 1;
  }

  all(parameters: readonly unknown[]): unknown[] {
    return this.stmt.all(...(parameters as sqlite.BindValue[]));
  }

  iterate(parameters: readonly unknown[]): IterableIterator<unknown> {
    return this.stmt.iter(...(parameters as sqlite.BindValue[]));
  }

  run(parameters: readonly unknown[]): {
    changes: number | bigint;
    lastInsertRowid: number | bigint;
  } {
    const { db } = this.stmt;
    const totalChangesBefore = db.totalChanges;
    const changes = this.stmt.run(...(parameters as sqlite.BindValue[]));
    return {
      changes: totalChangesBefore === db.totalChanges ? 0 : changes,
      lastInsertRowid: db.lastInsertRowId,
    };
  }
}

class SqliteDatabaseAdapter implements SqliteDatabase {
  constructor(public readonly db: sqlite.Database) {}

  prepare(sql: string): SqliteStatementAdapter {
    return new SqliteStatementAdapter(this.db.prepare(sql));
  }

  close(): void {
    this.db.close();
  }
}

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
    // deno-lint-ignore no-explicit-any
    async up(db: Kysely<any>): Promise<void> {
      await db.schema
        .createTable("message_id_map")
        .addColumn("id", "integer", (col) => col.primaryKey().autoIncrement())
        .addColumn("message_id", "text", (col) => col.notNull().unique())
        .addColumn("new_message_id", "text", (col) => col.notNull().unique())
        .execute();

      for (const column of ["message_id", "new_message_id"]) {
        await db.schema
          .createIndex(`message_id_map_${column}`)
          .on("message_id_map")
          .column(column)
          .execute();
      }
    },

    // deno-lint-ignore no-explicit-any
    async down(db: Kysely<any>): Promise<void> {
      await db.schema.dropTable("message_id_map").execute();
    },
  },
};

export class DbService {
  #db;
  #kysely;
  #migrator;

  constructor(public readonly path: string) {
    this.#db = new sqlite.Database(path);
    this.#kysely = new Kysely<Database>({
      dialect: new SqliteDialect({
        database: new SqliteDatabaseAdapter(this.#db),
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
    await this.#migrator.migrateToLatest();
  }

  async addMessageIdMap(
    mail: Insertable<MessageIdMapTable>,
  ): Promise<number> {
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
}
