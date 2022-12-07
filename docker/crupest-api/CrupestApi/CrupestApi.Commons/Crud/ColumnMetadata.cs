namespace CrupestApi.Commons.Crud;

public static class ColumnMetadataKeys
{
    public const string ColumnName = nameof(ColumnAttribute.ColumnName);
    public const string NotNull = nameof(ColumnAttribute.NotNull);
    public const string IsPrimaryKey = nameof(ColumnAttribute.IsPrimaryKey);
    public const string IsAutoIncrement = nameof(ColumnAttribute.IsAutoIncrement);
    public const string Index = nameof(ColumnAttribute.Index);
    public const string DefaultEmptyForString = nameof(ColumnAttribute.DefaultEmptyForString);
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

    // Use empty string for default value of string type.
    public bool DefaultEmptyForString { get; init; }

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
