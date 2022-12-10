using System.Diagnostics;
using System.Reflection;
using System.Text;

namespace CrupestApi.Commons.Crud;

public class ColumnHooks
{
    public delegate void ColumnHookAction(ColumnInfo column, ref object? value);

    public ColumnHooks(ColumnHookAction afterSelect, ColumnHookAction beforeInsert, ColumnHookAction beforeUpdate)
    {
        AfterSelect = afterSelect;
        BeforeInsert = beforeInsert;
        BeforeUpdate = beforeUpdate;
    }

    // Called after SELECT.
    public ColumnHookAction AfterSelect;

    // Called before INSERT.
    public ColumnHookAction BeforeInsert;

    // Called before UPDATE
    public ColumnHookAction BeforeUpdate;
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
            new ColumnHooks.ColumnHookAction(OnAfterSelect),
            new ColumnHooks.ColumnHookAction(OnBeforeInsert),
            new ColumnHooks.ColumnHookAction(OnBeforeUpdate)
        );
    }

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

    private void TryCoerceStringFromNullToEmpty(ref object? value)
    {
        if (ColumnType.ClrType == typeof(string) && (Metadata.GetValueOrDefault<bool?>(ColumnMetadataKeys.DefaultEmptyForString) ?? false) && value is null)
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
        TryCoerceStringFromNullToEmpty(ref value);
        if (column.IsNotNull && !column.IsAutoIncrement)
        {
            throw new Exception($"Column {column.ColumnName} can't be empty.");
        }
    }

    protected void OnBeforeUpdate(ColumnInfo column, ref object? value)
    {
        TryCoerceStringFromNullToEmpty(ref value);
    }

    public string ColumnName
    {
        get
        {
            object? value = Metadata.GetValueOrDefault(ColumnMetadataKeys.ColumnName);
            Debug.Assert(value is null || value is string);
            return ((string?)value ?? PropertyInfo?.Name) ?? throw new Exception("Failed to get column name.");
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
