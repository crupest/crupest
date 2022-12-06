using System.Text;
using Dapper;
using Microsoft.Data.Sqlite;

namespace CrupestApi.Commons.Crud;

public class TableInfo
{
    private readonly Lazy<List<string>> _lazyColumnNameList;

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

        _lazyColumnNameList = new Lazy<List<string>>(() => ColumnInfos.Select(c => c.SqlColumnName).ToList());
    }

    public Type EntityType { get; }
    public string TableName { get; }
    public IReadOnlyList<ColumnInfo> ColumnInfos { get; }
    public IReadOnlyList<string> ColumnNameList => _lazyColumnNameList.Value;

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

    public string GenerateCreateIndexSql()
    {
        var sb = new StringBuilder();

        foreach (var column in ColumnInfos)
        {
            if (column.IndexType == ColumnIndexType.None) continue;

            sb.Append($"CREATE {(column.IndexType == ColumnIndexType.Unique ? "UNIQUE" : "")} INDEX {TableName}_{column.SqlColumnName}_index ON {TableName} ({column.SqlColumnName});\n");
        }

        return sb.ToString();
    }

    public string GenerateCreateTableSql(bool createIndex = true)
    {
        var tableName = TableName;
        var columnSql = string.Join(",\n", ColumnInfos.Select(c => c.GenerateCreateTableColumnString()));

        var sql = $@"
CREATE TABLE {tableName}(
    {columnSql}
);
        ";

        if (createIndex)
        {
            sql += GenerateCreateIndexSql();
        }

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

    public string GenerateSelectSql(WhereClause? whereClause, OrderByClause? orderByClause, int? skip, int? limit, out DynamicParameters parameters)
    {
        if (whereClause is not null)
        {
            var relatedFields = ((IWhereClause)whereClause).GetRelatedColumns();
            if (relatedFields is not null)
            {
                foreach (var field in relatedFields)
                {
                    if (!ColumnNameList.Contains(field))
                    {
                        throw new ArgumentException($"Field {field} is not in the table.");
                    }
                }
            }
        }

        parameters = new DynamicParameters();

        StringBuilder result = new StringBuilder()
            .Append("SELECT * FROM ")
            .Append(TableName);

        if (whereClause is not null)
        {
            result.Append(' ');
            result.Append(whereClause.GenerateSql(parameters));
        }

        if (orderByClause is not null)
        {
            result.Append(' ');
            result.Append(orderByClause.GenerateSql());
        }


        if (limit is not null)
        {
            result.Append(" LIMIT @Limit");
            parameters.Add("Limit", limit.Value);
        }

        if (skip is not null)
        {
            result.Append(" OFFSET @Skip");
            parameters.Add("Skip", skip.Value);
        }

        result.Append(';');

        return result.ToString();
    }

    public string GenerateUpdateSql(WhereClause? whereClause, UpdateClause updateClause, out DynamicParameters parameters)
    {
        var relatedColumns = new HashSet<string>();
        if (whereClause is not null)
            relatedColumns.UnionWith(((IWhereClause)whereClause).GetRelatedColumns() ?? Enumerable.Empty<string>());
        relatedColumns.UnionWith(updateClause.GetRelatedColumns());
        foreach (var column in relatedColumns)
        {
            if (!ColumnNameList.Contains(column))
            {
                throw new ArgumentException($"Field {column} is not in the table.");
            }
        }

        parameters = new DynamicParameters();

        StringBuilder sb = new StringBuilder("UPDATE ");
        sb.Append(TableName);
        sb.Append(" SET ");
        sb.Append(updateClause.GenerateSql(parameters));
        if (whereClause is not null)
        {
            sb.Append(" WHERE ");
            sb.Append(whereClause.GenerateSql(parameters));
        }
        sb.Append(';');

        return sb.ToString();
    }
}