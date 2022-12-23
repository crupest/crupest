using System.Data;
using System.Diagnostics;
using System.Reflection;
using System.Text;
using Dapper;

namespace CrupestApi.Commons.Crud;

/// <summary>
/// Contains all you need to manipulate a table.
/// </summary>
public class TableInfo
{
    private readonly IColumnTypeProvider _columnTypeProvider;
    private readonly Lazy<List<string>> _lazyColumnNameList;
    private readonly ILoggerFactory _loggerFactory;
    private readonly ILogger<TableInfo> _logger;

    public TableInfo(Type entityType, IColumnTypeProvider columnTypeProvider, ILoggerFactory loggerFactory)
        : this(entityType.Name, entityType, columnTypeProvider, loggerFactory)
    {
    }

    public TableInfo(string tableName, Type entityType, IColumnTypeProvider columnTypeProvider, ILoggerFactory loggerFactory)
    {
        _loggerFactory = loggerFactory;
        _logger = loggerFactory.CreateLogger<TableInfo>();

        _logger.LogInformation("Create TableInfo for entity type '{}'.", entityType.Name);

        _columnTypeProvider = columnTypeProvider;

        TableName = tableName;
        EntityType = entityType;


        var properties = entityType.GetProperties();
        _logger.LogInformation("Find following properties: {}", string.Join(", ", properties.Select(p => p.Name)));

        var columnInfos = new List<ColumnInfo>();

        bool hasId = false;
        ColumnInfo? primaryKeyColumn = null;
        ColumnInfo? keyColumn = null;

        List<PropertyInfo> nonColumnProperties = new();

        foreach (var property in properties)
        {
            _logger.LogInformation("Check property '{}'.", property.Name);
            if (CheckPropertyIsColumn(property))
            {
                _logger.LogInformation("{} is a column, create ColumnInfo for it.", property.Name);
                var columnInfo = new ColumnInfo(this, property, _columnTypeProvider, _loggerFactory);
                columnInfos.Add(columnInfo);
                if (columnInfo.IsPrimaryKey)
                {
                    _logger.LogInformation("Column {} is a primary key.", property.Name);
                    primaryKeyColumn = columnInfo;
                }
                if (columnInfo.ColumnName.Equals("id", StringComparison.OrdinalIgnoreCase))
                {
                    _logger.LogInformation("Column {} has name id.", property.Name);
                    hasId = true;
                }
                if (columnInfo.IsSpecifiedAsKey)
                {
                    if (keyColumn is not null)
                    {
                        throw new Exception("Already exists a key column.");
                    }
                    _logger.LogInformation("Column {} is specified as key.", property.Name);
                    keyColumn = columnInfo;
                }
            }
            else
            {
                _logger.LogInformation("{} is not a column.", property.Name);
                nonColumnProperties.Add(property);
            }
        }

        if (primaryKeyColumn is null)
        {
            if (hasId) throw new Exception("A column named id already exists but is not primary key.");
            _logger.LogInformation("No primary key column found, create one automatically.");
            primaryKeyColumn = CreateAutoIdColumn();
            columnInfos.Add(primaryKeyColumn);
        }

        if (keyColumn is null)
        {
            _logger.LogInformation("No key column is specified, will use primary key.");
            keyColumn = primaryKeyColumn;
        }

        Columns = columnInfos;
        PrimaryKeyColumn = primaryKeyColumn;
        KeyColumn = keyColumn;
        NonColumnProperties = nonColumnProperties;

        _logger.LogInformation("Check table validity.");
        CheckValidity();

        _logger.LogInformation("TableInfo succeeded to create.");

        _lazyColumnNameList = new Lazy<List<string>>(() => Columns.Select(c => c.ColumnName).ToList());
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
            typeof(long), _columnTypeProvider, _loggerFactory);
    }

    public Type EntityType { get; }
    public string TableName { get; }
    public IReadOnlyList<ColumnInfo> Columns { get; }
    public IReadOnlyList<ColumnInfo> PropertyColumns => Columns.Where(c => c.PropertyInfo is not null).ToList();
    public ColumnInfo PrimaryKeyColumn { get; }
    /// <summary>
    /// Maybe not the primary key. But acts as primary key.
    /// </summary>
    /// <seealso cref="ColumnMetadataKeys.ActAsKey"/>
    public ColumnInfo KeyColumn { get; }
    public IReadOnlyList<PropertyInfo> ColumnProperties => PropertyColumns.Select(c => c.PropertyInfo!).ToList();
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
        foreach (var column in Columns)
        {
            if (column.ColumnName.Equals(columnName, StringComparison.OrdinalIgnoreCase))
            {
                return column;
            }
        }
        throw new KeyNotFoundException("No such column with given name.");
    }

    public void CheckGeneratedColumnHasGenerator()
    {
        foreach (var column in Columns)
        {
            if (column.IsOnlyGenerated && column.DefaultValueGeneratorMethod is null)
            {
                throw new Exception($"Column '{column.ColumnName}' is generated but has no generator.");
            }
        }
    }

    public void CheckValidity()
    {
        // Check if there is only one primary key.
        bool hasPrimaryKey = false;
        bool hasKey = false;
        foreach (var column in Columns)
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

        foreach (var column in Columns)
        {
            if (sqlNameSet.Contains(column.ColumnName))
                throw new Exception($"Two columns have the same sql name '{column.ColumnName}'.");
            sqlNameSet.Add(column.ColumnName);
        }

        CheckGeneratedColumnHasGenerator();
    }

    public string GenerateCreateIndexSql(string? dbProviderId = null)
    {
        var sb = new StringBuilder();

        foreach (var column in Columns)
        {
            if (column.Index == ColumnIndexType.None) continue;

            sb.Append($"CREATE {(column.Index == ColumnIndexType.Unique ? "UNIQUE" : "")} INDEX {TableName}_{column.ColumnName}_index ON {TableName} ({column.ColumnName});\n");
        }

        return sb.ToString();
    }

    public string GenerateCreateTableSql(bool createIndex = true, string? dbProviderId = null)
    {
        var tableName = TableName;
        var columnSql = string.Join(",\n", Columns.Select(c => c.GenerateCreateTableColumnString(dbProviderId)));

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
    /// <seealso cref="SelectDynamic"/>
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
            result.Append(" WHERE ");
            var (whereSql, whereParameters) = whereClause.GenerateSql(dbProviderId);
            parameters.AddRange(whereParameters);
            result.Append(whereSql);
        }

        if (orderByClause is not null)
        {
            result.Append(' ');
            var orderBySql = orderByClause.GenerateSql(dbProviderId);
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

    /// <summary>
    /// ConvertParameters. Select. Call hooks.
    /// </summary>
    public virtual List<dynamic> SelectDynamic(IDbConnection dbConnection, string? what = null, IWhereClause? where = null, IOrderByClause? orderBy = null, int? skip = null, int? limit = null)
    {
        var (sql, parameters) = GenerateSelectSql(what, where, orderBy, skip, limit);
        var queryResult = dbConnection.Query<dynamic>(sql, ConvertParameters(parameters));
        return queryResult.ToList();
    }

    public virtual int SelectCount(IDbConnection dbConnection, IWhereClause? where = null, IOrderByClause? orderBy = null, int? skip = null, int? limit = null)
    {
        var (sql, parameters) = GenerateSelectSql("COUNT(*)", where, orderBy, skip, limit);
        var result = dbConnection.QuerySingle<int>(sql, ConvertParameters(parameters));
        return result;
    }

    public virtual TResult MapDynamicTo<TResult>(dynamic d)
    {
        var dict = (IDictionary<string, object?>)d;

        var result = Activator.CreateInstance<TResult>();
        Type resultType = typeof(TResult);

        foreach (var column in Columns)
        {
            var resultProperty = resultType.GetProperty(column.ColumnName);
            if (dict.ContainsKey(column.ColumnName) && resultProperty is not null)
            {
                if (dict[column.ColumnName] is null)
                {
                    resultProperty.SetValue(result, null);
                    continue;
                }
                object? value = Convert.ChangeType(dict[column.ColumnName], column.ColumnType.DatabaseClrType);
                value = column.ColumnType.ConvertFromDatabase(value);
                resultProperty.SetValue(result, value);
            }
        }

        return result;
    }

    /// <summary>
    /// Select and call hooks.
    /// </summary>
    public virtual List<TResult> Select<TResult>(IDbConnection dbConnection, string? what = null, IWhereClause? where = null, IOrderByClause? orderBy = null, int? skip = null, int? limit = null)
    {
        List<dynamic> queryResult = SelectDynamic(dbConnection, what, where, orderBy, skip, limit).ToList();

        return queryResult.Select(MapDynamicTo<TResult>).ToList();
    }

    public IInsertClause ConvertEntityToInsertClause(object entity)
    {
        Debug.Assert(EntityType.IsInstanceOfType(entity));
        var result = new InsertClause();
        foreach (var column in PropertyColumns)
        {
            var value = column.PropertyInfo!.GetValue(entity);
            result.Add(column.ColumnName, value);
        }
        return result;
    }

    /// <summary>
    /// Insert a entity and call hooks.
    /// </summary>
    /// <returns>The key of insert entity.</returns>
    public int Insert(IDbConnection dbConnection, IInsertClause insert, out object key)
    {
        object? finalKey = null;

        var realInsert = InsertClause.Create();

        foreach (var column in Columns)
        {
            InsertItem? item = insert.Items.SingleOrDefault(i => i.ColumnName == column.ColumnName);

            var value = item?.Value;

            if (column.IsOnlyGenerated && value is not null)
            {
                throw new Exception($"The column '{column.ColumnName}' is auto generated. You can't specify it explicitly.");
            }

            if (value is null)
            {
                value = column.GenerateDefaultValue();
            }

            if (value is null && column.IsAutoIncrement)
            {
                continue;
            }

            if (value is null)
            {
                value = DbNullValue.Instance;
            }

            column.InvokeValidator(value);

            InsertItem realInsertItem;

            if (value is DbNullValue)
            {
                if (column.IsNotNull)
                {
                    throw new Exception($"Column '{column.ColumnName}' is not nullable. Please specify a non-null value.");
                }

                realInsertItem = new InsertItem(column.ColumnName, null);
            }
            else
            {
                realInsertItem = new InsertItem(column.ColumnName, value);
            }

            realInsert.Add(realInsertItem);

            if (realInsertItem.ColumnName == KeyColumn.ColumnName)
            {
                finalKey = realInsertItem.Value;
            }
        }

        if (finalKey is null) throw new Exception("No key???");
        key = finalKey;

        var (sql, parameters) = GenerateInsertSql(realInsert);

        var affectedRowCount = dbConnection.Execute(sql, ConvertParameters(parameters));

        if (affectedRowCount != 1)
            throw new Exception("Failed to insert.");

        return affectedRowCount;
    }

    /// <summary>
    /// Upgrade a entity and call hooks.
    /// </summary>
    /// <returns>The key of insert entity.</returns>
    public virtual int Update(IDbConnection dbConnection, IWhereClause? where, IUpdateClause update, out object? newKey)
    {
        newKey = null;

        var realUpdate = UpdateClause.Create();

        foreach (var column in Columns)
        {
            UpdateItem? item = update.Items.FirstOrDefault(i => i.ColumnName == column.ColumnName);
            object? value = item?.Value;

            if (value is not null)
            {
                if (column.IsNoUpdate)
                {
                    throw new Exception($"The column '{column.ColumnName}' can't be update.");
                }

                column.InvokeValidator(value);

                realUpdate.Add(column.ColumnName, value);

                if (column.ColumnName == KeyColumn.ColumnName)
                {
                    newKey = value;
                }
            }
        }

        var (sql, parameters) = GenerateUpdateSql(where, realUpdate);
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
    private readonly ILoggerFactory _loggerFactory;
    private readonly ILogger<TableInfoFactory> _logger;

    public TableInfoFactory(IColumnTypeProvider columnTypeProvider, ILoggerFactory loggerFactory)
    {
        _columnTypeProvider = columnTypeProvider;
        _loggerFactory = loggerFactory;
        _logger = loggerFactory.CreateLogger<TableInfoFactory>();
    }

    // This is thread-safe.
    public TableInfo Get(Type type)
    {
        lock (_cache)
        {
            if (_cache.TryGetValue(type, out var tableInfo))
            {
                _logger.LogDebug("Table info of type '{}' is cached, return it.", type.Name);
                return tableInfo;
            }
            else
            {
                _logger.LogDebug("Table info for type '{}' is not in cache, create it.", type.Name);
                tableInfo = new TableInfo(type, _columnTypeProvider, _loggerFactory);
                _logger.LogDebug("Table info for type '{}' is created, add it to cache.", type.Name);
                _cache.Add(type, tableInfo);
                return tableInfo;
            }
        }
    }
}
