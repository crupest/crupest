using System.Data;
using System.Diagnostics;
using System.Reflection;
using System.Text;
using Dapper;

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

        List<PropertyInfo> columnProperties = new();
        List<PropertyInfo> nonColumnProperties = new();

        foreach (var property in properties)
        {
            if (PropertyIsColumn(property))
            {
                var columnInfo = new ColumnInfo(this, property, _columnTypeProvider);
                columnInfos.Add(columnInfo);
                if (columnInfo.IsPrimaryKey)
                    hasPrimaryKey = true;
                if (columnInfo.ColumnName.Equals("id", StringComparison.OrdinalIgnoreCase))
                {
                    hasId = true;
                }
                columnProperties.Add(property);
            }
            else
            {
                nonColumnProperties.Add(property);
            }
        }

        if (!hasPrimaryKey)
        {
            if (hasId) throw new Exception("A column named id already exists but is not primary key.");
            var columnInfo = CreateAutoIdColumn();
            columnInfos.Add(columnInfo);
        }

        ColumnInfos = columnInfos;
        ColumnProperties = columnProperties;
        NonColumnProperties = nonColumnProperties;

        CheckValidity();

        _lazyColumnNameList = new Lazy<List<string>>(() => ColumnInfos.Select(c => c.ColumnName).ToList());
    }

    private ColumnInfo CreateAutoIdColumn()
    {
        return new ColumnInfo(this,
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
    public IReadOnlyList<PropertyInfo> ColumnProperties { get; }
    public IReadOnlyList<PropertyInfo> NonColumnProperties { get; }
    public IReadOnlyList<string> ColumnNameList => _lazyColumnNameList.Value;

    protected bool PropertyIsColumn(PropertyInfo property)
    {
        var columnAttribute = property.GetCustomAttribute<ColumnAttribute>();
        if (columnAttribute is null) return false;
        return true;
    }

    public ColumnInfo GetColumn(string columnName)
    {
        foreach (var column in ColumnInfos)
        {
            if (column.ColumnName.Equals(columnName, StringComparison.OrdinalIgnoreCase))
            {
                return column;
            }
        }
        throw new KeyNotFoundException("No such column with given name.");
    }

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

    public void CheckColumnName(string columnName)
    {
        foreach (var c in columnName)
        {
            if (char.IsWhiteSpace(c))
            {
                throw new Exception("White space found in column name, which might be an sql injection attack!");
            }
        }
    }

    public void CheckRelatedColumns(IClause? clause)
    {
        if (clause is not null)
        {
            var relatedColumns = clause.GetRelatedColumns();
            foreach (var column in relatedColumns)
            {
                CheckColumnName(column);
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

    public (string sql, DynamicParameters parameters) GenerateUpdateSql(IWhereClause? whereClause, IUpdateClause updateClause)
    {
        CheckRelatedColumns(whereClause);
        CheckRelatedColumns(updateClause);

        var parameters = new DynamicParameters();

        StringBuilder sb = new StringBuilder("UPDATE ");
        sb.Append(TableName);
        sb.Append(" SET ");
        var (updateSql, updateParameters) = updateClause.GenerateSql();
        sb.Append(updateSql);
        parameters.AddDynamicParams(updateParameters);
        if (whereClause is not null)
        {
            sb.Append(" WHERE ");
            var (whereSql, whereParameters) = whereClause.GenerateSql();
            sb.Append(whereSql);
            parameters.AddDynamicParams(whereParameters);
        }
        sb.Append(';');

        return (sb.ToString(), parameters);
    }

    public (string sql, DynamicParameters parameters) GenerateDeleteSql(IWhereClause? whereClause)
    {
        CheckRelatedColumns(whereClause);

        var parameters = new DynamicParameters();

        StringBuilder sb = new StringBuilder("DELETE FROM ");
        sb.Append(TableName);
        if (whereClause is not null)
        {
            sb.Append(" WHERE ");
            var (whereSql, whereParameters) = whereClause.GenerateSql();
            parameters.AddDynamicParams(whereParameters);
            sb.Append(whereSql);
        }
        sb.Append(';');

        return (sb.ToString(), parameters);
    }

    private object? ClearNonColumnProperties(object? entity)
    {
        Debug.Assert(entity is null || entity.GetType() == EntityType);
        if (entity is null) return entity;
        foreach (var property in NonColumnProperties)
        {
            // Clear any non-column properties.
            property.SetValue(entity, Activator.CreateInstance(property.PropertyType));
        }
        return entity;
    }

    private object? CallColumnHook(object? entity, string hookName)
    {
        Debug.Assert(entity is null || entity.GetType() == EntityType);
        if (entity is null) return entity;
        foreach (var column in ColumnInfos)
        {
            var property = column.PropertyInfo;
            if (property is not null)
            {
                var value = property.GetValue(entity);

                switch (hookName)
                {
                    case "AfterGet":
                        column.Hooks.AfterGet(column, ref value);
                        break;
                    case "BeforeSet":
                        column.Hooks.BeforeSet(column, ref value);
                        break;
                    default:
                        throw new Exception("Unknown hook.");
                };

                property.SetValue(entity, value);
            }

        }
        return entity;
    }

    public virtual IEnumerable<object?> Select(IDbConnection dbConnection, IWhereClause? where = null, IOrderByClause? orderBy = null, int? skip = null, int? limit = null)
    {
        var (sql, parameters) = GenerateSelectSql(where, orderBy, skip, limit);
        return dbConnection.Query(EntityType, sql, parameters).Select(e => CallColumnHook(ClearNonColumnProperties(e), "AfterGet"));
    }

    public virtual int Insert(IDbConnection dbConnection, IInsertClause insert)
    {
        var (sql, parameters) = GenerateInsertSql(insert);

        foreach (var item in insert.Items)
        {
            var column = GetColumn(item.ColumnName);
            var value = item.Value;
            column.Hooks.BeforeSet?.Invoke(column, ref value);
            item.Value = value;
        }

        return dbConnection.Execute(sql, parameters);
    }

    public virtual int Update(IDbConnection dbConnection, IWhereClause? where, IUpdateClause update)
    {
        var (sql, parameters) = GenerateUpdateSql(where, update);

        foreach (var item in update.Items)
        {
            var column = GetColumn(item.ColumnName);
            var value = item.Value;
            column.Hooks.BeforeSet?.Invoke(column, ref value);
            item.Value = value;
        }
        return dbConnection.Execute(sql, parameters);
    }

    public virtual int Delete(IDbConnection dbConnection, IWhereClause? where)
    {
        var (sql, parameters) = GenerateDeleteSql(where);
        return dbConnection.Execute(sql, parameters);
    }
}

// TODO: Implement and register this service.
public interface ITableInfoFactory
{
    TableInfo Get(Type type);
}
