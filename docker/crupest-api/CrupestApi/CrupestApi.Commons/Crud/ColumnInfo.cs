using System.Diagnostics;
using System.Reflection;
using System.Text;

namespace CrupestApi.Commons.Crud;

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
    }

    public TableInfo Table { get; }

    public Type EntityType => Table.EntityType;

    // If null, there is no corresponding property.
    public PropertyInfo? PropertyInfo { get; } = null;

    public IColumnMetadata Metadata => _metadata;

    public IColumnTypeInfo ColumnType { get; }

    public bool IsPrimaryKey => Metadata.GetValueOrDefault(ColumnMetadataKeys.IsPrimaryKey) is true;
    public bool IsAutoIncrement => Metadata.GetValueOrDefault(ColumnMetadataKeys.IsAutoIncrement) is true;
    public bool IsNotNull => IsPrimaryKey || Metadata.GetValueOrDefault(ColumnMetadataKeys.NotNull) is true;
    public bool IsGenerated => Metadata.GetValueOrDefault(ColumnMetadataKeys.Generated) is true;
    public bool IsNoUpdate => Metadata.GetValueOrDefault(ColumnMetadataKeys.NoUpdate) is true;
    public bool CanBeGenerated => (bool?)Metadata.GetValueOrDefault(ColumnMetadataKeys.CanBeGenerated) ?? (DefaultValueGeneratorMethod is not null);
    /// <summary>
    /// This only returns metadata value. It doesn't not fall back to primary column. If you want to get the real key column, go to table info.
    /// </summary>
    /// <seealso cref="ColumnMetadataKeys.ActAsKey"/>
    /// <seealso cref="TableInfo.KeyColumn"/>
    public bool IsSpecifiedAsKey => Metadata.GetValueOrDefault(ColumnMetadataKeys.ActAsKey) is true;
    public ColumnIndexType Index => Metadata.GetValueOrDefault<ColumnIndexType?>(ColumnMetadataKeys.Index) ?? ColumnIndexType.None;

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

    public MethodInfo? ValidatorMethod
    {
        get
        {
            object? value = Metadata.GetValueOrDefault(ColumnMetadataKeys.DefaultValueGenerator);
            Debug.Assert(value is null || value is string);
            MethodInfo? result;
            if (value is null)
            {
                string methodName = ColumnName + "Validator";
                result = Table.EntityType.GetMethod(methodName, BindingFlags.Static);
            }
            else
            {
                string methodName = (string)value;
                result = Table.EntityType.GetMethod(methodName, BindingFlags.Static) ?? throw new Exception("The validator does not exist.");
            }

            return result;
        }
    }

    public void InvokeValidator(object value)
    {
        ValidatorMethod?.Invoke(null, new object?[] { this, value });
    }

    public object? InvokeDefaultValueGenerator()
    {
        return DefaultValueGeneratorMethod?.Invoke(null, new object?[] { this });
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
