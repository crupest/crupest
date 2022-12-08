using System.Diagnostics;
using System.Reflection;
using System.Text;

namespace CrupestApi.Commons.Crud;

public class ColumnHooks
{
    public delegate void ColumnHookAction(ColumnInfo column, ref object? value);

    public ColumnHooks(ColumnHookAction afterGet, ColumnHookAction beforeSet)
    {
        AfterGet = afterGet;
        BeforeSet = beforeSet;
    }

    // Called after SELECT.
    public ColumnHookAction AfterGet;

    // Called before UPDATE and INSERT.
    public ColumnHookAction BeforeSet;
}

public class ColumnInfo
{
    private readonly AggregateColumnMetadata _metadata = new AggregateColumnMetadata();

    public ColumnInfo(TableInfo table, IColumnMetadata metadata, Type clrType, IColumnTypeProvider typeProvider)
    {
        Table = table;
        _metadata.Add(metadata);
        ColumnType = typeProvider.Get(clrType);

        Hooks = new ColumnHooks(
            new ColumnHooks.ColumnHookAction(OnAfterGet),
            new ColumnHooks.ColumnHookAction(OnBeforeSet)
        );
    }

    public ColumnInfo(TableInfo table, PropertyInfo propertyInfo, IColumnTypeProvider typeProvider)
    {
        Table = table;
        ColumnType = typeProvider.Get(propertyInfo.PropertyType);

        var columnAttribute = propertyInfo.GetCustomAttribute<ColumnAttribute>();
        if (columnAttribute is not null)
        {
            _metadata.Add(columnAttribute);
        }

        Hooks = new ColumnHooks(
            new ColumnHooks.ColumnHookAction(OnAfterGet),
            new ColumnHooks.ColumnHookAction(OnBeforeSet)
        );
    }

    public TableInfo Table { get; }
    // If null, there is no corresponding property.
    public PropertyInfo? PropertyInfo { get; } = null;

    public IColumnMetadata Metadata => _metadata;

    public IColumnTypeInfo ColumnType { get; }

    public ColumnHooks Hooks { get; }

    private void TryCoerceStringFromNullToEmpty(ref object? value)
    {
        if (ColumnType.ClrType == typeof(string) && (Metadata.GetValueOrDefault<bool?>(ColumnMetadataKeys.DefaultEmptyForString) ?? false) && value is null)
        {
            value = "";
        }
    }

    protected void OnAfterGet(ColumnInfo column, ref object? value)
    {
        TryCoerceStringFromNullToEmpty(ref value);
    }

    protected void OnBeforeSet(ColumnInfo column, ref object? value)
    {
        TryCoerceStringFromNullToEmpty(ref value);
    }

    public string ColumnName
    {
        get
        {
            object? value = Metadata.GetValueOrDefault(ColumnMetadataKeys.ColumnName);
            Debug.Assert(value is null || value is string);
            return (string?)value ?? PropertyInfo?.Name ?? throw new Exception("Failed to get column name.");
        }
    }

    public bool IsPrimaryKey => Metadata.GetValueOrDefault(ColumnMetadataKeys.IsPrimaryKey) is true;
    public bool IsAutoIncrement => Metadata.GetValueOrDefault(ColumnMetadataKeys.IsAutoIncrement) is true;
    public bool IsNotNull => IsPrimaryKey || Metadata.GetValueOrDefault(ColumnMetadataKeys.NotNull) is true;

    public ColumnIndexType Index => Metadata.GetValueOrDefault<ColumnIndexType?>(ColumnMetadataKeys.Index) ?? ColumnIndexType.None;

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
