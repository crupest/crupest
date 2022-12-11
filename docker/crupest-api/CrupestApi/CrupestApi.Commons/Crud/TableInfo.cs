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

        bool hasId = false;
        ColumnInfo? primaryKeyColumn = null;
        ColumnInfo? keyColumn = null;

        List<PropertyInfo> columnProperties = new();
        List<PropertyInfo> nonColumnProperties = new();

        foreach (var property in properties)
        {
            if (CheckPropertyIsColumn(property))
            {
                var columnInfo = new ColumnInfo(this, property, _columnTypeProvider);
                columnInfos.Add(columnInfo);
                if (columnInfo.IsPrimaryKey)
                {
                    primaryKeyColumn = columnInfo;
                }
                if (columnInfo.ColumnName.Equals("id", StringComparison.OrdinalIgnoreCase))
                {
                    hasId = true;
                }
                if (columnInfo.IsSpecifiedAsKey)
                {
                    if (keyColumn is not null)
                    {
                        throw new Exception("Already exists a key column.");
                    }
                    keyColumn = columnInfo;
                }
                columnProperties.Add(property);
            }
            else
            {
                nonColumnProperties.Add(property);
            }
        }

        if (primaryKeyColumn is null)
        {
            if (hasId) throw new Exception("A column named id already exists but is not primary key.");
            primaryKeyColumn = CreateAutoIdColumn();
            columnInfos.Add(primaryKeyColumn);
        }

        if (keyColumn is null)
        {
            keyColumn = primaryKeyColumn;
        }

        ColumnInfos = columnInfos;
        PrimaryKeyColumn = primaryKeyColumn;
        KeyColumn = keyColumn;
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
    public ColumnInfo PrimaryKeyColumn { get; }
    /// <summary>
    /// Maybe not the primary key. But acts as primary key.
    /// </summary>
    /// <seealso cref="ColumnMetadataKeys.ActAsKey"/>
    public ColumnInfo KeyColumn { get; }
    public IReadOnlyList<PropertyInfo> ColumnProperties { get; }
    public IReadOnlyList<PropertyInfo> NonColumnProperties { get; }
    public IReadOnlyList<string> ColumnNameList => _lazyColumnNameList.Value;

    protected bool CheckPropertyIsColumn(PropertyInfo property)
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
        bool hasKey = false;
        foreach (var column in ColumnInfos)
        {
            if (column.IsPrimaryKey)
            {
                if (hasPrimaryKey) throw new Exception("More than one columns are primary key.");
                hasPrimaryKey = true;
            }

            if (column.IsSpecifiedAsKey)
            {
                if (hasKey) throw new Exception("More than one columns are specified as key column.");
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
        if (!ColumnNameList.Contains(columnName))
        {
            throw new ArgumentException($"Column {columnName} is not in the table.");
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
            }
        }
    }

    /// <summary>
    /// If you call this manually, it's your duty to call hooks.
    /// </summary>
    /// <seealso cref="Select"/>
    public (string sql, ParamList parameters) GenerateSelectSql(string? selectWhat, IWhereClause? whereClause, IOrderByClause? orderByClause = null, int? skip = null, int? limit = null, string? dbProviderId = null)
    {
        CheckRelatedColumns(whereClause);
        CheckRelatedColumns(orderByClause);

        var parameters = new ParamList();

        StringBuilder result = new StringBuilder()
            .Append($"SELECT {selectWhat ?? "*"} FROM ")
            .Append(TableName);

        if (whereClause is not null)
        {
            result.Append(' ');
            var (whereSql, whereParameters) = whereClause.GenerateSql(dbProviderId);
            parameters.AddRange(whereParameters);
            result.Append(whereSql);
        }

        if (orderByClause is not null)
        {
            result.Append(' ');
            var (orderBySql, orderByParameters) = orderByClause.GenerateSql(dbProviderId);
            parameters.AddRange(orderByParameters);
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

    /// <summary>
    /// If you call this manually, it's your duty to call hooks.
    /// </summary>
    /// <seealso cref="Insert"/>
    public (string sql, ParamList parameters) GenerateInsertSql(IInsertClause insertClause, string? dbProviderId = null)
    {
        CheckRelatedColumns(insertClause);

        var parameters = new ParamList();

        var result = new StringBuilder()
            .Append("INSERT INTO ")
            .Append(TableName)
            .Append(" (")
            .Append(insertClause.GenerateColumnListSql(dbProviderId))
            .Append(") VALUES (");

        var (valueSql, valueParameters) = insertClause.GenerateValueListSql(dbProviderId);
        result.Append(valueSql).Append(");");

        parameters.AddRange(valueParameters);

        return (result.ToString(), parameters);
    }

    /// <summary>
    /// If you call this manually, it's your duty to call hooks.
    /// </summary>
    /// <seealso cref="Update"/>
    public (string sql, ParamList parameters) GenerateUpdateSql(IWhereClause? whereClause, IUpdateClause updateClause)
    {
        CheckRelatedColumns(whereClause);
        CheckRelatedColumns(updateClause);

        var parameters = new ParamList();

        StringBuilder sb = new StringBuilder("UPDATE ");
        sb.Append(TableName);
        sb.Append(" SET ");
        var (updateSql, updateParameters) = updateClause.GenerateSql();
        sb.Append(updateSql);
        parameters.AddRange(updateParameters);
        if (whereClause is not null)
        {
            sb.Append(" WHERE ");
            var (whereSql, whereParameters) = whereClause.GenerateSql();
            sb.Append(whereSql);
            parameters.AddRange(whereParameters);
        }
        sb.Append(';');

        return (sb.ToString(), parameters);
    }

    /// <summary>
    /// If you call this manually, it's your duty to call hooks.
    /// </summary>
    /// <seealso cref="Delete"/>
    public (string sql, ParamList parameters) GenerateDeleteSql(IWhereClause? whereClause)
    {
        CheckRelatedColumns(whereClause);

        var parameters = new ParamList();

        StringBuilder sb = new StringBuilder("DELETE FROM ");
        sb.Append(TableName);
        if (whereClause is not null)
        {
            sb.Append(" WHERE ");
            var (whereSql, whereParameters) = whereClause.GenerateSql();
            parameters.AddRange(whereParameters);
            sb.Append(whereSql);
        }
        sb.Append(';');

        return (sb.ToString(), parameters);
    }

    private DynamicParameters ConvertParameters(ParamList parameters)
    {
        var result = new DynamicParameters();
        foreach (var param in parameters)
        {
            if (param.Value is null || param.Value is DbNullValue)
            {
                result.Add(param.Name, null);
                continue;
            }

            var columnName = param.ColumnName;
            IColumnTypeInfo typeInfo;
            if (columnName is not null)
            {
                typeInfo = GetColumn(columnName).ColumnType;
            }
            else
            {
                typeInfo = _columnTypeProvider.Get(param.Value.GetType());
            }

            result.Add(param.Name, typeInfo.ConvertToDatabase(param.Value), typeInfo.DbType);
        }
        return result;
    }

    public virtual int SelectCount(IDbConnection dbConnection, IWhereClause? where = null, IOrderByClause? orderBy = null, int? skip = null, int? limit = null)
    {
        var (sql, parameters) = GenerateSelectSql("COUNT(*)", where, orderBy, skip, limit);
        return dbConnection.QuerySingle<int>(sql, parameters);

    }

    public virtual IEnumerable<object?> Select(IDbConnection dbConnection, IWhereClause? where = null, IOrderByClause? orderBy = null, int? skip = null, int? limit = null)
    {
        return Select<IEnumerable<object?>>(dbConnection, null, where, orderBy, skip, limit);
    }

    /// <summary>
    /// Select and call hooks.
    /// </summary>
    public virtual IEnumerable<TResult> Select<TResult>(IDbConnection dbConnection, string? what, IWhereClause? where = null, IOrderByClause? orderBy = null, int? skip = null, int? limit = null)
    {
        var (sql, parameters) = GenerateSelectSql(what, where, orderBy, skip, limit);
        return dbConnection.Query<dynamic>(sql, parameters).Select(d =>
        {
            Type dynamicType = d.GetType();

            var result = Activator.CreateInstance<TResult>();

            foreach (var column in ColumnInfos)
            {
                object? value = null;
                var dynamicProperty = dynamicType.GetProperty(column.ColumnName);
                if (dynamicProperty is not null) value = dynamicProperty.GetValue(d);
                if (value is not null)
                    value = column.ColumnType.ConvertFromDatabase(value);
                column.Hooks.AfterSelect(column, ref value);
                var propertyInfo = column.PropertyInfo;
                if (propertyInfo is not null)
                {
                    propertyInfo.SetValue(result, value);
                }
            }

            return result;
        });
    }

    /// <summary>
    /// Insert a entity and call hooks.
    /// </summary>
    /// <returns>The key of insert entity.</returns>
    public object Insert(IDbConnection dbConnection, IInsertClause insert)
    {
        object? key = null;
        foreach (var column in ColumnInfos)
        {
            InsertItem? item = insert.Items.FirstOrDefault(i => i.ColumnName == column.ColumnName);
            var value = item?.Value;
            column.Hooks.BeforeInsert(column, ref value);
            if (item is null)
            {
                item = new InsertItem(column.ColumnName, value);
                insert.Items.Add(item);
            }
            else
            {
                item.Value = value;
            }

            if (item.ColumnName == KeyColumn.ColumnName)
            {
                key = item.Value;
            }
        }

        var (sql, parameters) = GenerateInsertSql(insert);

        dbConnection.Execute(sql, ConvertParameters(parameters));

        return key ?? throw new Exception("No key???");
    }

    /// <summary>
    /// Upgrade a entity and call hooks.
    /// </summary>
    /// <returns>The key of insert entity.</returns>
    public virtual int Update(IDbConnection dbConnection, IWhereClause? where, IUpdateClause update)
    {
        var (sql, parameters) = GenerateUpdateSql(where, update);

        foreach (var column in ColumnInfos)
        {
            UpdateItem? item = update.Items.FirstOrDefault(i => i.ColumnName == column.ColumnName);
            var value = item?.Value;
            column.Hooks.BeforeUpdate(column, ref value);
            if (item is null)
            {
                if (value is not null)
                    update.Items.Add(new UpdateItem(column.ColumnName, value));
            }
            else
            {
                item.Value = value;
            }
        }

        return dbConnection.Execute(sql, ConvertParameters(parameters));
    }

    public virtual int Delete(IDbConnection dbConnection, IWhereClause? where)
    {
        var (sql, parameters) = GenerateDeleteSql(where);
        return dbConnection.Execute(sql, ConvertParameters(parameters));
    }
}

public interface ITableInfoFactory
{
    TableInfo Get(Type type);
}

public class TableInfoFactory : ITableInfoFactory
{
    private readonly Dictionary<Type, TableInfo> _cache = new Dictionary<Type, TableInfo>();
    private readonly IColumnTypeProvider _columnTypeProvider;

    public TableInfoFactory(IColumnTypeProvider columnTypeProvider)
    {
        _columnTypeProvider = columnTypeProvider;
    }

    // This is thread-safe.
    public TableInfo Get(Type type)
    {
        lock (_cache)
        {
            if (_cache.TryGetValue(type, out var tableInfo))
            {
                return tableInfo;
            }
            else
            {
                tableInfo = new TableInfo(type, _columnTypeProvider);
                _cache.Add(type, tableInfo);
                return tableInfo;
            }
        }
    }
}
