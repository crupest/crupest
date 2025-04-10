// spellchecker: words kysely insertable updateable introspector

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
    return this.stmt.all(...parameters as sqlite.BindValue[]);
  }

  iterate(parameters: readonly unknown[]): IterableIterator<unknown> {
    return this.stmt.iter(...parameters as sqlite.BindValue[]);
  }

  run(
    parameters: readonly unknown[],
  ): { changes: number | bigint; lastInsertRowid: number | bigint } {
    const { db } = this.stmt;
    const totalChangesBefore = db.totalChanges;
    const changes = this.stmt.run(...parameters as sqlite.BindValue[]);
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

export class DbError extends Error {
}

const NAMES = {
  mail: {
    table: "mail",
    columns: {
      id: "id",
      messageId: "message_id",
      awsMessageId: "aws_message_id",
      date: "date",
      raw: "raw",
    },
  },
} as const;

interface MailTable {
  [NAMES.mail.columns.id]: Generated<number>;
  [NAMES.mail.columns.messageId]: string;
  [NAMES.mail.columns.awsMessageId]: string | null;
  [NAMES.mail.columns.date]: string | null;
  [NAMES.mail.columns.raw]: string;
}

interface Database {
  [NAMES.mail.table]: MailTable;
}

const migrations: Record<string, Migration> = {
  "0001-init": {
    // deno-lint-ignore no-explicit-any
    async up(db: Kysely<any>): Promise<void> {
      await db.schema
        .createTable(NAMES.mail.table)
        .addColumn(
          NAMES.mail.columns.id,
          "integer",
          (col) => col.primaryKey().autoIncrement(),
        )
        .addColumn(
          NAMES.mail.columns.messageId,
          "text",
          (col) => col.notNull().unique(),
        )
        .addColumn(
          NAMES.mail.columns.awsMessageId,
          "text",
          (col) => col.unique(),
        )
        .addColumn(NAMES.mail.columns.date, "text")
        .addColumn(NAMES.mail.columns.raw, "text", (col) => col.notNull())
        .execute();

      for (
        const column of [
          NAMES.mail.columns.messageId,
          NAMES.mail.columns.awsMessageId,
        ]
      ) {
        await db.schema
          .createIndex(`${NAMES.mail.table}_${column}`)
          .on(NAMES.mail.table)
          .column(column)
          .execute();
      }
    },

    // deno-lint-ignore no-explicit-any
    async down(db: Kysely<any>): Promise<void> {
      await db.schema.dropTable(NAMES.mail.table).execute();
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
      dialect: new SqliteDialect(
        { database: new SqliteDatabaseAdapter(this.#db) },
      ),
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

  async addMail(mail: Insertable<MailTable>): Promise<number> {
    const inserted = await this.#kysely.insertInto(NAMES.mail.table).values(
      mail,
    ).executeTakeFirstOrThrow();
    return Number(inserted.insertId!);
  }

  async messageIdToAws(messageId: string): Promise<string | null> {
    const row = await this.#kysely.selectFrom(NAMES.mail.table).where(
      NAMES.mail.columns.messageId,
      "=",
      messageId,
    ).select(NAMES.mail.columns.awsMessageId).executeTakeFirst();
    return row?.aws_message_id ?? null;
  }

  async messageIdFromAws(awsMessageId: string): Promise<string | null> {
    const row = await this.#kysely.selectFrom(NAMES.mail.table).where(
      NAMES.mail.columns.awsMessageId,
      "=",
      awsMessageId,
    ).select(NAMES.mail.columns.messageId).executeTakeFirst();
    return row?.message_id ?? null;
  }
}
