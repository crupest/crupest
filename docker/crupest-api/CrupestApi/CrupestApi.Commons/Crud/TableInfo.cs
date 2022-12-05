using Dapper;
using Microsoft.Data.Sqlite;

namespace CrupestApi.Commons.Crud;

public class TableInfo
{
    // For custom name.
    public TableInfo(Type entityType)
        : this(entityType.Name, entityType)
    {

    }

    public TableInfo(string tableName, Type entityType)
    {
        TableName = tableName;
        EntityType = entityType;

        var properties = entityType.GetProperties();

        var columnInfos = new List<ColumnInfo>();

        bool hasPrimaryKey = false;
        bool hasId = false;

        foreach (var property in properties)
        {
            var columnInfo = new ColumnInfo(entityType, property.Name);
            columnInfos.Add(columnInfo);
            if (columnInfo.IsPrimaryKey)
                hasPrimaryKey = true;
            if (columnInfo.SqlColumnName.Equals("id", StringComparison.OrdinalIgnoreCase))
            {
                hasId = true;
            }
        }

        if (!hasPrimaryKey)
        {
            if (hasId) throw new Exception("A column named id already exists but is not primary key.");
            var columnInfo = new ColumnInfo(entityType, "id", true, true, ColumnTypeInfoRegistry.Singleton.GetRequiredByDataType(typeof(int)));
            columnInfos.Add(columnInfo);
        }

        ColumnInfos = columnInfos;

        CheckValidity();
    }

    public Type EntityType { get; }
    public string TableName { get; }
    public IReadOnlyList<ColumnInfo> ColumnInfos { get; }

    public void CheckValidity()
    {
        // Check if there is only one primary key.
        bool hasPrimaryKey = false;
        foreach (var column in ColumnInfos)
        {
            if (column.IsPrimaryKey)
            {
                if (hasPrimaryKey) throw new Exception("Two columns are primary key.");
                hasPrimaryKey = true;
            }
        }

        if (!hasPrimaryKey) throw new Exception("No column is primary key.");

        // Check two columns have the same sql name.
        HashSet<string> sqlNameSet = new HashSet<string>();

        foreach (var column in ColumnInfos)
        {
            if (sqlNameSet.Contains(column.SqlColumnName))
                throw new Exception($"Two columns have the same sql name '{column.SqlColumnName}'.");
            sqlNameSet.Add(column.SqlColumnName);
        }
    }

    public string GenerateCreateTableSql()
    {
        var tableName = TableName;
        var columnSql = string.Join(",\n", ColumnInfos.Select(c => c.GenerateCreateTableColumnString()));

        var sql = $@"
CREATE TABLE {tableName}(
    {columnSql}
);
        ";

        return sql;
    }

    public async Task<bool> CheckExistence(SqliteConnection connection)
    {
        var tableName = TableName;
        var count = (await connection.QueryAsync<int>(
            @"SELECT count(*) FROM sqlite_schema WHERE type = 'table' AND tbl_name = @TableName;",
            new { TableName = tableName })).Single();
        if (count == 0)
        {
            return false;
        }
        else if (count > 1)
        {
            throw new DatabaseInternalException($"More than 1 table has name {tableName}. What happened?");
        }
        else
        {
            return true;
        }

    }
}