namespace CrupestApi.Commons.Crud;

public static class ColumnMetadataKeys
{
    public const string ColumnName = nameof(ColumnAttribute.ColumnName);
    public const string NotNull = nameof(ColumnAttribute.NotNull);
    public const string IsPrimaryKey = nameof(ColumnAttribute.IsPrimaryKey);
    public const string IsAutoIncrement = nameof(ColumnAttribute.IsAutoIncrement);
    public const string Index = nameof(ColumnAttribute.Index);

    /// <summary>
    /// This will add hooks for string type column to coerce null to ""(empty string) when get or set. No effect on non-string type.
    /// </summary> 
    public const string DefaultEmptyForString = nameof(ColumnAttribute.DefaultEmptyForString);

    /// <summary>
    /// This indicates that you take care of generate this column value when create entity. User calling the api can not specify the value.
    /// </summary>
    public const string OnlyGenerated = nameof(ColumnAttribute.OnlyGenerated);

    /// <summary>
    /// The default value generator method name in entity type. Default to null, aka, search for ColumnNameDefaultValueGenerator. 
    /// Generator has signature <code>static void DefaultValueGenerator(ColumnInfo column)</code>
    /// </summary>
    public const string DefaultValueGenerator = nameof(ColumnAttribute.DefaultValueGenerator);

    /// <summary>
    /// The validator method name in entity type. Default to null, aka, the default validator.
    /// Validator has signature <code>static void Validator(ColumnInfo column, object value)</code>
    /// Value param is never null. If you want to mean NULL, it should be a <see cref="DbNullValue"/>.
    /// </summary>
    public const string Validator = nameof(ColumnAttribute.Validator);

    /// <summary>
    /// The column can only be set when inserted, can't be changed in update.
    /// </summary>
    /// <returns></returns>
    public const string NoUpdate = nameof(ColumnAttribute.NoUpdate);

    /// <summary>
    /// This column acts as key when get one entity for http get method in path. 
    /// </summary>
    public const string ActAsKey = nameof(ColumnAttribute.ActAsKey);

    /// <summary>
    /// The default value used for the column.
    /// </summary>
    public const string DefaultValue = nameof(ColumnAttribute.DefaultValue);
}

public interface IColumnMetadata
{
    bool TryGetValue(string key, out object? value);

    object? GetValueOrDefault(string key)
    {
        if (TryGetValue(key, out var value))
        {
            return value;
        }
        else
        {
            return null;
        }
    }

    T? GetValueOrDefault<T>(string key)
    {
        return (T?)GetValueOrDefault(key);
    }

    object? this[string key]
    {
        get
        {
            if (TryGetValue(key, out var value))
            {
                return value;
            }
            else
            {
                throw new KeyNotFoundException("Key not found.");
            }
        }
    }
}

public enum ColumnIndexType
{
    None,
    Unique,
    NonUnique
}

[AttributeUsage(AttributeTargets.Property, AllowMultiple = false)]
public class ColumnAttribute : Attribute, IColumnMetadata
{
    // if null, use the property name.
    public string? ColumnName { get; init; }

    // default false.
    public bool NotNull { get; init; }

    // default false
    public bool IsPrimaryKey { get; init; }

    // default false
    public bool IsAutoIncrement { get; init; }

    // default None
    public ColumnIndexType Index { get; init; } = ColumnIndexType.None;

    /// <seealso cref="ColumnMetadataKeys.DefaultEmptyForString"/>
    public bool DefaultEmptyForString { get; init; }

    /// <seealso cref="ColumnMetadataKeys.OnlyGenerated"/>
    public bool OnlyGenerated { get; init; }

    /// <seealso cref="ColumnMetadataKeys.DefaultValueGenerator"/>
    public string? DefaultValueGenerator { get; init; }

    /// <seealso cref="ColumnMetadataKeys.Validator"/>
    public string? Validator { get; init; }

    /// <seealso cref="ColumnMetadataKeys.NoUpdate"/>
    public bool NoUpdate { get; init; }

    /// <seealso cref="ColumnMetadataKeys.ActAsKey"/>
    public bool ActAsKey { get; init; }

    public object? DefaultValue { get; init; }

    public bool TryGetValue(string key, out object? value)
    {
        var property = GetType().GetProperty(key);
        if (property is null)
        {
            value = null;
            return false;
        }
        value = property.GetValue(this);
        return true;
    }
}

public class AggregateColumnMetadata : IColumnMetadata
{
    private IDictionary<string, object?> _own = new Dictionary<string, object?>();
    private IList<IColumnMetadata> _children = new List<IColumnMetadata>();

    public void Add(string key, object? value)
    {
        _own[key] = value;
    }

    public void Remove(string key)
    {
        _own.Remove(key);
    }

    public void Add(IColumnMetadata child)
    {
        _children.Add(child);
    }

    public void Remove(IColumnMetadata child)
    {
        _children.Remove(child);
    }

    public bool TryGetValue(string key, out object? value)
    {
        if (_own.ContainsKey(key))
        {
            value = _own[key];
            return true;
        }

        bool found = false;
        value = null;
        foreach (var child in _children)
        {
            if (child.TryGetValue(key, out var tempValue))
            {
                value = tempValue;
                found = true;
            }
        }

        return found;
    }
}
