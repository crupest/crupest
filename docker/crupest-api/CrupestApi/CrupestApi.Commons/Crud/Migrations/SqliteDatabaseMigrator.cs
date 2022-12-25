using System.Data;
using System.Text;
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

    public Table GetTable(IDbConnection dbConnection, string name)
    {
        CheckTableName(name);

        var table = new Table(name);
        var queryColumns = dbConnection.Query<dynamic>($"PRAGMA table_info({name})");

        foreach (var column in queryColumns)
        {
            var columnName = (string)column.name;
            var columnType = (string)column.type;
            var isNullable = (bool)column.notnull;
            var primaryKey = (long)column.pk;

            table.Columns.Add(new TableColumn(columnName, columnType, isNullable, (int)primaryKey));
        }

        return table;
    }

    public Table ConvertTableInfoToTable(TableInfo tableInfo)
    {
        var table = new Table(tableInfo.TableName);

        foreach (var columnInfo in tableInfo.Columns)
        {
            table.Columns.Add(new TableColumn(columnInfo.ColumnName, columnInfo.ColumnType.GetSqlTypeString(),
                !columnInfo.IsNotNull, columnInfo.IsPrimaryKey ? 1 : 0));
        }

        return table;
    }

    public bool CanAutoMigrate(IDbConnection dbConnection, TableInfo tableInfo)
    {
        if (!TableExists(dbConnection, tableInfo.TableName)) return true;

        var databaseTable = GetTable(dbConnection, tableInfo.TableName);
        var wantedTable = ConvertTableInfoToTable(tableInfo);
        var databaseTableColumns = new HashSet<TableColumn>(databaseTable.Columns);
        var wantedTableColumns = new HashSet<TableColumn>(wantedTable.Columns);

        if (databaseTableColumns.IsSubsetOf(wantedTableColumns))
        {
            var addColumns = wantedTableColumns.Except(databaseTableColumns);
            foreach (var column in addColumns)
            {
                if (tableInfo.GetColumn(column.Name) is not null)
                {
                    var columnInfo = tableInfo.GetColumn(column.Name);
                    if (!columnInfo.CanBeGenerated)
                    {
                        return false;
                    }
                }

            }
            return true;
        }
        else
        {
            return false;
        }
    }

    public string GenerateCreateTableSql(string tableName, IEnumerable<TableColumn> columns)
    {
        CheckTableName(tableName);

        var columnSql = string.Join(",\n", columns.Select(GenerateCreateTableColumnSqlSegment));

        var sql = $@"
CREATE TABLE {tableName}(
    {columnSql}
);
        ";

        return sql;

    }

    public void AutoMigrate(IDbConnection dbConnection, TableInfo tableInfo)
    {
        if (!CanAutoMigrate(dbConnection, tableInfo))
        {
            throw new Exception("The table can't be auto migrated.");
        }

        // We are sqlite, so it's a little bit difficult.
        using var transaction = dbConnection.BeginTransaction();

        var tableName = tableInfo.TableName;

        var wantedTable = ConvertTableInfoToTable(tableInfo);
        var wantedTableColumns = new HashSet<TableColumn>(wantedTable.Columns);

        var exist = TableExists(dbConnection, tableName);
        if (exist)
        {
            var databaseTable = GetTable(dbConnection, tableName);
            var databaseTableColumns = new HashSet<TableColumn>(databaseTable.Columns);
            var addColumns = wantedTableColumns.Except(databaseTableColumns);

            var tempTableName = tableInfo.TableName + "_temp";
            dbConnection.Execute($"ALTER TABLE {tableName} RENAME TO {tempTableName}", new { TableName = tableName, tempTableName });

            var createTableSql = GenerateCreateTableSql(tableName, wantedTableColumns.ToList());
            dbConnection.Execute(createTableSql);

            // Copy old data to new table.
            var originalRows = dbConnection.Query<dynamic>($"SELECT * FROM {tempTableName}").Cast<IDictionary<string, object?>>().ToList();
            foreach (var originalRow in originalRows)
            {
                var parameters = new DynamicParameters();

                var originalColumnNames = originalRow.Keys.ToList();
                foreach (var columnName in originalColumnNames)
                {
                    parameters.Add(columnName, originalRow[columnName]);
                }
                var addColumnNames = addColumns.Select(c => c.Name).ToList();
                foreach (var columnName in addColumnNames)
                {
                    parameters.Add(columnName, tableInfo.GetColumn(columnName).GenerateDefaultValue());
                }

                string columnSql = string.Join(", ", wantedTableColumns.Select(c => c.Name));
                string valuesSql = string.Join(", ", wantedTableColumns.Select(c => "@" + c.Name));

                string sql = $"INSERT INTO {tableName} ({columnSql}) VALUES {valuesSql})";
                dbConnection.Execute(sql, parameters);
            }

            // Finally drop old table
            dbConnection.Execute($"DROP TABLE {tempTableName}");
        }
        else
        {
            var createTableSql = GenerateCreateTableSql(tableName, wantedTableColumns.ToList());
            dbConnection.Execute(createTableSql);
        }

        // Commit transaction.
        transaction.Commit();
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
        else if (!column.IsNullable)
        {
            result.Append(" NOT NULL");
        }

        return result.ToString();
    }

    public bool NeedMigrate(IDbConnection dbConnection, TableInfo tableInfo)
    {
        if (!TableExists(dbConnection, tableInfo.TableName)) return true;

        var tableName = tableInfo.TableName;
        var databaseTable = GetTable(dbConnection, tableName);
        var wantedTable = ConvertTableInfoToTable(tableInfo);
        var databaseTableColumns = new HashSet<TableColumn>(databaseTable.Columns);
        var wantedTableColumns = new HashSet<TableColumn>(wantedTable.Columns);
        return databaseTableColumns != wantedTableColumns;
    }

    public bool TableExists(IDbConnection connection, string tableName)
    {
        var count = connection.QuerySingle<int>(
            "SELECT count(*) FROM sqlite_schema WHERE type = 'table' AND tbl_name = @TableName;",
            new { TableName = tableName });
        if (count == 0)
        {
            return false;
        }
        else if (count > 1)
        {
            throw new Exception($"More than 1 table has name {tableName}. What happened?");
        }
        else
        {
            return true;
        }
    }
}
