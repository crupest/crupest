using System.Data;
using System.Text;
using Dapper;
using Microsoft.Data.Sqlite;

namespace CrupestApi.Commons.Crud;

public class TableInfo
{
    private readonly IColumnTypeProvider _columnTypeProvider;
    private readonly Lazy<List<string>> _lazyColumnNameList;

    public TableInfo(Type entityType, IColumnTypeProvider columnTypeProvider)
        : this(entityType.Name, entityType, columnTypeProvider)
    {

    }

    public TableInfo(string tableName, Type entityType, IColumnTypeProvider columnTypeProvider)
    {
        _columnTypeProvider = columnTypeProvider;
        TableName = tableName;
        EntityType = entityType;

        var properties = entityType.GetProperties();

        var columnInfos = new List<ColumnInfo>();

        bool hasPrimaryKey = false;
        bool hasId = false;

        foreach (var property in properties)
        {
            var columnInfo = new ColumnInfo(property, _columnTypeProvider);
            columnInfos.Add(columnInfo);
            if (columnInfo.IsPrimaryKey)
                hasPrimaryKey = true;
            if (columnInfo.ColumnName.Equals("id", StringComparison.OrdinalIgnoreCase))
            {
                hasId = true;
            }
        }

        if (!hasPrimaryKey)
        {
            if (hasId) throw new Exception("A column named id already exists but is not primary key.");
            var columnInfo = CreateAutoIdColumn();
            columnInfos.Add(columnInfo);
        }

        ColumnInfos = columnInfos;

        CheckValidity();

        _lazyColumnNameList = new Lazy<List<string>>(() => ColumnInfos.Select(c => c.SqlColumnName).ToList());
    }

    private ColumnInfo CreateAutoIdColumn()
    {
        return new ColumnInfo(EntityType,
                new ColumnAttribute
                {
                    ColumnName = "Id",
                    NotNull = true,
                    IsPrimaryKey = true,
                    IsAutoIncrement = true,
                },
            typeof(long), _columnTypeProvider);
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
            if (sqlNameSet.Contains(column.ColumnName))
                throw new Exception($"Two columns have the same sql name '{column.ColumnName}'.");
            sqlNameSet.Add(column.ColumnName);
        }
    }

    public string GenerateCreateIndexSql(string? dbProviderId = null)
    {
        var sb = new StringBuilder();

        foreach (var column in ColumnInfos)
        {
            if (column.Index == ColumnIndexType.None) continue;

            sb.Append($"CREATE {(column.Index == ColumnIndexType.Unique ? "UNIQUE" : "")} INDEX {TableName}_{column.ColumnName}_index ON {TableName} ({column.ColumnName});\n");
        }

        return sb.ToString();
    }

    public string GenerateCreateTableSql(bool createIndex = true, string? dbProviderId = null)
    {
        var tableName = TableName;
        var columnSql = string.Join(",\n", ColumnInfos.Select(c => c.GenerateCreateTableColumnString(dbProviderId)));

        var sql = $@"
CREATE TABLE {tableName}(
    {columnSql}
);
        ";

        if (createIndex)
        {
            sql += GenerateCreateIndexSql(dbProviderId);
        }

        return sql;
    }

    public bool CheckExistence(IDbConnection connection)
    {
        var tableName = TableName;
        var count = connection.QuerySingle<int>(
            @"SELECT count(*) FROM sqlite_schema WHERE type = 'table' AND tbl_name = @TableName;",
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

    public void CheckRelatedColumns(IClause? clause)
    {
        if (clause is not null)
        {
            var relatedColumns = clause.GetRelatedColumns();
            foreach (var column in relatedColumns)
            {
                if (!ColumnNameList.Contains(column))
                {
                    throw new ArgumentException($"Column {column} is not in the table.");
                }
            }
        }
    }

    public (string sql, DynamicParameters parameters) GenerateSelectSql(IWhereClause? whereClause, IOrderByClause? orderByClause = null, int? skip = null, int? limit = null, string? dbProviderId = null)
    {
        CheckRelatedColumns(whereClause);
        CheckRelatedColumns(orderByClause);

        var parameters = new DynamicParameters();

        StringBuilder result = new StringBuilder()
            .Append("SELECT * FROM ")
            .Append(TableName);

        if (whereClause is not null)
        {
            result.Append(' ');
            var (whereSql, whereParameters) = whereClause.GenerateSql(dbProviderId);
            parameters.AddDynamicParams(whereParameters);
            result.Append(whereSql);
        }

        if (orderByClause is not null)
        {
            result.Append(' ');
            var (orderBySql, orderByParameters) = orderByClause.GenerateSql(dbProviderId);
            parameters.AddDynamicParams(orderByClause);
            result.Append(orderBySql);
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

        return (result.ToString(), parameters);
    }

    public InsertClause GenerateInsertClauseFromObject(object value)
    {
        var insertClause = InsertClause.Create();

        foreach (var column in ColumnInfos)
        {
            var propertyInfo = EntityType.GetProperty(column.ColumnName);
            if (propertyInfo is null)
            {
                if (column.IsAutoIncrement)
                {
                    continue;
                }
                else
                {
                    throw new Exception($"Property {column.ColumnName} not found.");
                }
            }

            var propertyValue = propertyInfo.GetValue(value);
            if (propertyValue is null)
            {
                if (column.IsAutoIncrement)
                {
                    continue;
                }
                else
                {
                    insertClause.Add(column.ColumnName, propertyValue);
                }
            }
        }

        return insertClause;
    }

    public (string sql, DynamicParameters parameters) GenerateInsertSql(IInsertClause insertClause, string? dbProviderId = null)
    {
        CheckRelatedColumns(insertClause);

        var parameters = new DynamicParameters();

        var result = new StringBuilder()
            .Append("INSERT INTO ")
            .Append(TableName)
            .Append(" (")
            .Append(insertClause.GenerateColumnListSql(dbProviderId))
            .Append(") VALUES (");

        var (valueSql, valueParameters) = insertClause.GenerateValueListSql(dbProviderId);
        result.Append(valueSql).Append(");");

        parameters.AddDynamicParams(valueParameters);

        return (result.ToString(), parameters);
    }

    // TODO: Continue...
    public string GenerateUpdateSql(IWhereClause? whereClause, UpdateClause updateClause)
    {
        var relatedColumns = new HashSet<string>();
        if (whereClause is not null)
            relatedColumns.UnionWith(((IClause)whereClause).GetRelatedColumns() ?? Enumerable.Empty<string>());
        relatedColumns.UnionWith(updateClause.GetRelatedColumns());
        foreach (var column in relatedColumns)
        {
            if (!ColumnNameList.Contains(column))
            {
                throw new ArgumentException($"Column {column} is not in the table.");
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

    public string GenerateDeleteSql(WhereClause? whereClause, out DynamicParameters parameters)
    {
        if (whereClause is not null)
        {
            var relatedColumns = ((IClause)whereClause).GetRelatedColumns() ?? new List<string>();
            foreach (var column in relatedColumns)
            {
                if (!ColumnNameList.Contains(column))
                {
                    throw new ArgumentException($"Column {column} is not in the table.");
                }
            }
        }

        parameters = new DynamicParameters();

        StringBuilder sb = new StringBuilder("DELETE FROM ");
        sb.Append(TableName);
        if (whereClause is not null)
        {
            sb.Append(" WHERE ");
            sb.Append(whereClause.GenerateSql(parameters));
        }
        sb.Append(';');

        return sb.ToString();
    }
}
