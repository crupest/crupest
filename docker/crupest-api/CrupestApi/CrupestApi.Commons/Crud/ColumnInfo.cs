using System.Diagnostics;
using System.Reflection;
using System.Text;

namespace CrupestApi.Commons.Crud;

public class ColumnHooks
{
    // value:
    //   null => not specified
    //   DbNullValue => specified as NULL
    //   other => specified as value
    public delegate void ColumnHookAction(ColumnInfo column, ref object? value);

    public ColumnHooks(ColumnHookAction afterSelect, ColumnHookAction beforeInsert, ColumnHookAction beforeUpdate)
    {
        AfterSelect = afterSelect;
        BeforeInsert = beforeInsert;
        BeforeUpdate = beforeUpdate;
    }

    /// <summary>Called after SELECT. Please use multicast if you want to customize it because there are many default behavior in it.</summary 
    public ColumnHookAction AfterSelect;

    /// <summary>Called before INSERT. Please use multicast if you want to customize it because there are many default behavior in it.</summary>
    public ColumnHookAction BeforeInsert;

    /// <summary>Called before UPDATE. Please use multicast if you want to customize it because there are many default behavior in it.</summary 
    /// <remarks>Set value to null to delete the update item so it will not change. Set value to <see cref="DbNullValue"/> to update the column to  NULL.</remarks>
    public ColumnHookAction BeforeUpdate;
}

public class ColumnInfo
{
    private readonly AggregateColumnMetadata _metadata = new AggregateColumnMetadata();

    /// <summary>
    /// Initialize a column without corresponding property.
    /// </summary>
    public ColumnInfo(TableInfo table, IColumnMetadata metadata, Type clrType, IColumnTypeProvider typeProvider)
    {
        Table = table;
        _metadata.Add(metadata);
        ColumnType = typeProvider.Get(clrType);

        Hooks = new ColumnHooks(
            new ColumnHooks.ColumnHookAction(OnAfterSelect),
            new ColumnHooks.ColumnHookAction(OnBeforeInsert),
            new ColumnHooks.ColumnHookAction(OnBeforeUpdate)
        );
    }

    /// <summary>
    /// Initialize a column with corresponding property.
    /// </summary>
    public ColumnInfo(TableInfo table, PropertyInfo propertyInfo, IColumnTypeProvider typeProvider)
    {
        Table = table;
        PropertyInfo = propertyInfo;
        ColumnType = typeProvider.Get(propertyInfo.PropertyType);

        var columnAttribute = propertyInfo.GetCustomAttribute<ColumnAttribute>();
        if (columnAttribute is not null)
        {
            _metadata.Add(columnAttribute);
        }

        Hooks = new ColumnHooks(
            new ColumnHooks.ColumnHookAction(OnAfterSelect),
            new ColumnHooks.ColumnHookAction(OnBeforeInsert),
            new ColumnHooks.ColumnHookAction(OnBeforeUpdate)
        );
    }

    public TableInfo Table { get; }

    // If null, there is no corresponding property.
    public PropertyInfo? PropertyInfo { get; } = null;

    public IColumnMetadata Metadata => _metadata;

    public IColumnTypeInfo ColumnType { get; }

    public ColumnHooks Hooks { get; }

    public bool IsPrimaryKey => Metadata.GetValueOrDefault(ColumnMetadataKeys.IsPrimaryKey) is true;
    public bool IsAutoIncrement => Metadata.GetValueOrDefault(ColumnMetadataKeys.IsAutoIncrement) is true;
    public bool IsNotNull => IsPrimaryKey || Metadata.GetValueOrDefault(ColumnMetadataKeys.NotNull) is true;
    public bool IsClientGenerate => Metadata.GetValueOrDefault(ColumnMetadataKeys.ClientGenerate) is true;
    public bool IsNoUpdate => Metadata.GetValueOrDefault(ColumnMetadataKeys.NoUpdate) is true;
    /// <summary>
    /// This only returns metadata value. It doesn't not fall back to primary column. If you want to get the real key column, go to table info.
    /// </summary>
    /// <seealso cref="ColumnMetadataKeys.ActAsKey"/>
    /// <seealso cref="TableInfo.KeyColumn"/>
    public bool IsSpecifiedAsKey => Metadata.GetValueOrDefault(ColumnMetadataKeys.ActAsKey) is true;
    public ColumnIndexType Index => Metadata.GetValueOrDefault<ColumnIndexType?>(ColumnMetadataKeys.Index) ?? ColumnIndexType.None;
    public UpdateBehavior UpdateBehavior => Metadata.GetValueOrDefault<UpdateBehavior?>(ColumnMetadataKeys.UpdateBehavior) ?? UpdateBehavior.NullIsNotUpdate;

    /// <summary>
    /// The real column name. Maybe set in metadata or just the property name.
    /// </summary>
    /// <value></value>
    public string ColumnName
    {
        get
        {
            object? value = Metadata.GetValueOrDefault(ColumnMetadataKeys.ColumnName);
            Debug.Assert(value is null || value is string);
            return ((string?)value ?? PropertyInfo?.Name) ?? throw new Exception("Failed to get column name.");
        }
    }

    public MethodInfo? DefaultValueGeneratorMethod
    {
        get
        {
            object? value = Metadata.GetValueOrDefault(ColumnMetadataKeys.DefaultValueGenerator);
            Debug.Assert(value is null || value is string);
            MethodInfo? result;
            if (value is null)
            {
                string methodName = ColumnName + "DefaultValueGenerator";
                result = Table.EntityType.GetMethod(methodName, BindingFlags.Static);
            }
            else
            {
                string methodName = (string)value;
                result = Table.EntityType.GetMethod(methodName, BindingFlags.Static) ?? throw new Exception("The default value generator does not exist.");
            }

            return result;
        }
    }

    private void TryCoerceStringFromNullToEmpty(ref object? value)
    {
        if (ColumnType.ClrType == typeof(string) && (Metadata.GetValueOrDefault<bool?>(ColumnMetadataKeys.DefaultEmptyForString) is true) && value is DbNullValue)
        {
            value = "";
        }
    }

    protected void OnAfterSelect(ColumnInfo column, ref object? value)
    {
        TryCoerceStringFromNullToEmpty(ref value);
    }

    protected void OnBeforeInsert(ColumnInfo column, ref object? value)
    {
        if (column.IsClientGenerate && value is not null)
        {
            throw new Exception($"'{column.ColumnName}' can't be set manually. It is auto generated.");
        }

        var defaultValueGenerator = DefaultValueGeneratorMethod;
        if (defaultValueGenerator is not null && value is null)
        {
            value = defaultValueGenerator.Invoke(null, null);
        }

        TryCoerceStringFromNullToEmpty(ref value);

        if (IsNotNull && (value is null || value is DbNullValue))
        {
            throw new Exception($"'{column.ColumnName}' can't be null.");
        }
    }

    protected void OnBeforeUpdate(ColumnInfo column, ref object? value)
    {
        if (column.IsNoUpdate && value is not null)
        {
            throw new Exception($"'{column.ColumnName}' is not updatable.");
        }

        TryCoerceStringFromNullToEmpty(ref value);

        if (IsNotNull && value is DbNullValue)
        {
            throw new Exception($"'{column.ColumnName}' can't be null.");
        }
    }

    public string GenerateCreateTableColumnString(string? dbProviderId = null)
    {
        StringBuilder result = new StringBuilder();
        result.Append(ColumnName);
        result.Append(' ');
        result.Append(ColumnType.GetSqlTypeString(dbProviderId));
        if (IsPrimaryKey)
        {
            result.Append(' ');
            result.Append("PRIMARY KEY");
        }
        else if (IsNotNull)
        {
            result.Append(' ');
            result.Append(" NOT NULL");
        }

        if (IsAutoIncrement)
        {
            result.Append(' ');
            result.Append("AUTOINCREMENT");
        }

        return result.ToString();
    }
}
