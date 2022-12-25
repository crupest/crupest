using System.Data;
using System.Text;
using System.Text.Json;
using System.Text.RegularExpressions;
using Dapper;

namespace CrupestApi.Commons.Crud.Migrations;

public class SqliteDatabaseMigrator : IDatabaseMigrator
{
    private void CheckTableName(string name)
    {
        if (Regex.Match(name, @"^[_0-9a-zA-Z]+$").Success is false)
        {
            throw new ArgumentException("Fxxk, what have you passed as table name.");
        }
    }

    private const string MigrationHistoryTableName = "migration_history";

    private class MigrationRecordEntity
    {
        public string TableName { get; set; } = string.Empty;
        public int Version { get; set; }
        public string Structure { get; set; } = string.Empty;
    }

    private void EnsureHistoryDatabase(IDbConnection dbConnection)
    {
        var exist = dbConnection.Query<int>($"SELECT count(*) FROM sqlite_master WHERE type='table' AND name='{MigrationHistoryTableName}';").Single() == 1;
        if (!exist)
        {
            dbConnection.Execute($@"
                CREATE TABLE {MigrationHistoryTableName} (
                    Id INTEGER PRIMARY KEY AUTOINCREMENT,
                    TableName TEXT NOT NULL,
                    Version INT NOT NULL,
                    Structure TEXT NOT NULL
                );
            ");
        }
    }

    public List<MigrationRecord> GetRecords(IDbConnection dbConnection, string tableName)
    {
        CheckTableName(tableName);
        EnsureHistoryDatabase(dbConnection);

        var recordEntities = dbConnection.Query<MigrationRecordEntity>(
            $"SELECT * FROM {MigrationHistoryTableName} WHERE TableName = @TableName ORDER BY Version ASC;",
            new { TableName = tableName }
        ).ToList();

        var records = recordEntities.Select(entity =>
        {
            var structure = JsonSerializer.Deserialize<Table>(entity.Structure);
            if (structure is null) throw new Exception("Migration record is corrupted. Failed to convert structure.");
            return new MigrationRecord
            {
                TableName = entity.TableName,
                Version = entity.Version,
                Structure = structure
            };
        }).ToList();

        return records;
    }


    public Table? GetTable(IDbConnection dbConnection, string tableName)
    {
        CheckTableName(tableName);

        var count = dbConnection.QuerySingle<int>(
            "SELECT count(*) FROM sqlite_schema WHERE type = 'table' AND tbl_name = @TableName;",
            new { TableName = tableName });
        if (count == 0)
        {
            return null;
        }
        else if (count > 1)
        {
            throw new Exception($"More than 1 table has name {tableName}. What happened?");
        }
        else
        {

            var table = new Table(tableName);
            var queryColumns = dbConnection.Query<dynamic>($"PRAGMA table_info({tableName})");

            foreach (var column in queryColumns)
            {
                var columnName = (string)column.name;
                var columnType = (string)column.type;
                var isNullable = Convert.ToBoolean(column.notnull);
                var primaryKey = Convert.ToInt32(column.pk);

                table.Columns.Add(new TableColumn(columnName, columnType, isNullable, primaryKey));
            }

            return table;
        }
    }

    public Table ConvertTableInfoToTable(TableInfo tableInfo)
    {
        var table = new Table(tableInfo.TableName);

        foreach (var columnInfo in tableInfo.Columns)
        {
            table.Columns.Add(new TableColumn(columnInfo.ColumnName, columnInfo.ColumnType.GetSqlTypeString(),
                columnInfo.IsNotNull, columnInfo.IsPrimaryKey ? 1 : 0));
        }

        return table;
    }

    public string GenerateCreateTableColumnSqlSegment(TableColumn column)
    {
        StringBuilder result = new StringBuilder();
        result.Append(column.Name);
        result.Append(' ');
        result.Append(column.Type);
        if (column.PrimaryKey is not 0)
        {
            result.Append(" PRIMARY KEY AUTOINCREMENT");
        }
        else if (column.NotNull)
        {
            result.Append(" NOT NULL");
        }

        return result.ToString();
    }

    public string GenerateCreateTableSql(string tableName, IEnumerable<TableColumn> columns)
    {
        CheckTableName(tableName);

        var columnSql = string.Join(",\n", columns.Select(GenerateCreateTableColumnSqlSegment));

        var sql = $@"
CREATE TABLE {tableName} (
    {columnSql}
);
        ";

        return sql;

    }

    public void AutoMigrate(IDbConnection dbConnection, TableInfo tableInfo)
    {
        var tableName = tableInfo.TableName;
        var databaseTable = GetTable(dbConnection, tableName);
        var wantedTable = ConvertTableInfoToTable(tableInfo);
        var databaseTableColumnNames = databaseTable is null ? new List<string>() : databaseTable.Columns.Select(column => column.Name).ToList();
        var wantedTableColumnNames = wantedTable.Columns.Select(column => column.Name).ToList();

        var notChangeColumns = wantedTableColumnNames.Where(column => databaseTableColumnNames.Contains(column)).ToList();
        var addColumns = wantedTableColumnNames.Where(column => !databaseTableColumnNames.Contains(column)).ToList();

        if (databaseTable is not null && dbConnection.Query<int>($"SELECT count(*) FROM {tableName}").Single() > 0)
        {
            foreach (var columnName in addColumns)
            {
                var columnInfo = tableInfo.GetColumn(columnName);
                if (!columnInfo.CanBeGenerated)
                {
                    throw new Exception($"Column {columnName} cannot be generated. So we can't auto-migrate.");
                }
            }
        }

        // We are sqlite, so it's a little bit difficult.
        using var transaction = dbConnection.BeginTransaction();

        if (databaseTable is not null)
        {
            var tempTableName = tableInfo.TableName + "_temp";
            dbConnection.Execute($"ALTER TABLE {tableName} RENAME TO {tempTableName}", new { TableName = tableName, tempTableName });

            var createTableSql = GenerateCreateTableSql(tableName, wantedTable.Columns);
            dbConnection.Execute(createTableSql);

            // Copy old data to new table.
            var originalRows = dbConnection.Query<dynamic>($"SELECT * FROM {tempTableName}").Cast<IDictionary<string, object?>>().ToList();
            foreach (var originalRow in originalRows)
            {
                var parameters = new DynamicParameters();

                foreach (var columnName in notChangeColumns)
                {
                    parameters.Add(columnName, originalRow[columnName]);
                }

                foreach (var columnName in addColumns)
                {
                    parameters.Add(columnName, tableInfo.GetColumn(columnName).GenerateDefaultValue());
                }

                string columnSql = string.Join(", ", wantedTableColumnNames);
                string valuesSql = string.Join(", ", wantedTableColumnNames.Select(c => "@" + c));

                string sql = $"INSERT INTO {tableName} ({columnSql}) VALUES {valuesSql})";
                dbConnection.Execute(sql, parameters);
            }

            // Finally drop old table
            dbConnection.Execute($"DROP TABLE {tempTableName}");
        }
        else
        {
            var createTableSql = GenerateCreateTableSql(tableName, wantedTable.Columns);
            dbConnection.Execute(createTableSql);
        }

        // Commit transaction.
        transaction.Commit();
    }

    public bool NeedMigrate(IDbConnection dbConnection, TableInfo tableInfo)
    {
        var tableName = tableInfo.TableName;
        var databaseTable = GetTable(dbConnection, tableName);
        var wantedTable = ConvertTableInfoToTable(tableInfo);
        var databaseTableColumns = databaseTable is null ? new HashSet<string>() : new HashSet<string>(databaseTable.Columns.Select(c => c.Name));
        var wantedTableColumns = new HashSet<string>(wantedTable.Columns.Select(c => c.Name));
        return !databaseTableColumns.SetEquals(wantedTableColumns);
    }
}
