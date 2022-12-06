using System.Data;
using System.Diagnostics;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace CrupestApi.Commons.Crud;

public interface IColumnTypeInfo
{
    JsonConverter? GetOptionalJsonConverter()
    {
        return null;
    }

    Type GetPropertyType();
    Type GetUnderlineType();
    object ConvertToUnderline(object data);
    object ConvertFromUnderline(object databaseData);

    void Validate(IReadOnlyDictionary<Type, IColumnTypeInfo> typeInfoMap)
    {
        var typeSet = new HashSet<Type>();

        IColumnTypeInfo current = this;

        while (current is not IBuiltinColumnTypeInfo)
        {
            var dataType = GetPropertyType();

            if (typeSet.Contains(dataType))
            {
                throw new Exception("Circular reference detected.");
            }
            typeSet.Add(dataType);

            var databaseType = GetUnderlineType();
            if (!typeInfoMap.ContainsKey(databaseType))
            {
                throw new Exception("Broken type chain.");
            }

            current = typeInfoMap[databaseType];
        }
    }
}

public interface IBuiltinColumnTypeInfo : IColumnTypeInfo
{
    /// To use for non-builtin type, use <see cref="ColumnTypeInfoRegistry.GetSqlTypeRecursive(IColumnTypeInfo)" /> because we need registry to query more information. 
    string GetSqlType();
    // To use for non-builtin type, use <see cref="ColumnTypeInfoRegistry.GetDbType(IColumnTypeInfo)" /> because we need registry to query more information.
    DbType GetDbType();
}

public class BuiltinColumnTypeInfo<T> : IBuiltinColumnTypeInfo
{
    private readonly string _sqlType;
    private readonly DbType _dbType;

    public BuiltinColumnTypeInfo(string sqlType, DbType dbType)
    {
        _sqlType = sqlType;
        _dbType = dbType;
    }

    public Type GetPropertyType()
    {
        return typeof(T);
    }

    public Type GetUnderlineType()
    {
        return typeof(T);
    }

    public string GetSqlType()
    {
        return _sqlType;
    }

    public DbType GetDbType()
    {
        return _dbType;
    }

    public T ConvertToDatabase(T data)
    {
        return data;
    }

    public T ConvertFromDatabase(T databaseData)
    {
        return databaseData;
    }

    object IColumnTypeInfo.ConvertToUnderline(object data)
    {
        return data;
    }

    object IColumnTypeInfo.ConvertFromUnderline(object databaseData)
    {
        return databaseData;
    }
}

public interface ICustomColumnTypeInfo : IColumnTypeInfo
{

}

public abstract class CustomColumnTypeInfo<TPropertyType, TUnderlineType> : ICustomColumnTypeInfo
 where TPropertyType : notnull where TUnderlineType : notnull
{

    public Type GetPropertyType()
    {
        return typeof(TPropertyType);
    }

    public Type GetUnderlineType()
    {
        return typeof(TUnderlineType);
    }

    public abstract TUnderlineType ConvertToUnderline(TPropertyType data);
    public abstract TPropertyType ConvertFromUnderline(TUnderlineType databaseData);

    object IColumnTypeInfo.ConvertToUnderline(object data)
    {
        Debug.Assert(data is TPropertyType);
        return ConvertToUnderline((TPropertyType)data);
    }

    object IColumnTypeInfo.ConvertFromUnderline(object databaseData)
    {
        Debug.Assert(databaseData is TUnderlineType);
        return ConvertFromUnderline((TUnderlineType)databaseData);
    }
}

public class DateTimeColumnTypeInfo : CustomColumnTypeInfo<DateTime, long>
{
    private readonly DateTimeJsonConverter _jsonConverter = new DateTimeJsonConverter();

    public JsonConverter GetJsonConverter()
    {
        return _jsonConverter;
    }

    public override long ConvertToUnderline(DateTime data)
    {
        return new DateTimeOffset(data).ToUnixTimeSeconds();
    }

    public override DateTime ConvertFromUnderline(long databaseData)
    {
        return DateTimeOffset.FromUnixTimeSeconds(databaseData).LocalDateTime;
    }
}

public class DateTimeJsonConverter : JsonConverter<DateTime>
{
    public override bool HandleNull => false;

    public override bool CanConvert(Type typeToConvert)
    {
        return typeToConvert == typeof(DateTime);
    }

    public override DateTime Read(ref Utf8JsonReader reader, Type typeToConvert, JsonSerializerOptions options)
    {
        return DateTimeOffset.FromUnixTimeSeconds(reader.GetInt64()).LocalDateTime;
    }

    public override void Write(Utf8JsonWriter writer, DateTime value, JsonSerializerOptions options)
    {
        writer.WriteNumberValue(new DateTimeOffset(value).ToUnixTimeSeconds());
    }
}

public class ColumnTypeInfoRegistry
{
    public static IReadOnlyList<IColumnTypeInfo> BuiltinList = new List<IColumnTypeInfo>()
    {
        new BuiltinColumnTypeInfo<char>("INTEGER", DbType.Int32),
        new BuiltinColumnTypeInfo<short>("INTEGER", DbType.Int32),
        new BuiltinColumnTypeInfo<int>("INTEGER", DbType.Int32),
        new BuiltinColumnTypeInfo<long>("INTEGER", DbType.Int64),
        new BuiltinColumnTypeInfo<float>("REAL", DbType.Double),
        new BuiltinColumnTypeInfo<double>("REAL", DbType.Double),
        new BuiltinColumnTypeInfo<string>("TEXT", DbType.String),
        new BuiltinColumnTypeInfo<byte[]>("BLOB", DbType.Binary),
    };


    public static IReadOnlyList<IColumnTypeInfo> CustomList = new List<IColumnTypeInfo>()
    {
        new DateTimeColumnTypeInfo(),
    };

    public static ColumnTypeInfoRegistry Singleton { get; }

    static ColumnTypeInfoRegistry()
    {
        Singleton = new ColumnTypeInfoRegistry();

        foreach (var builtinColumnTypeInfo in BuiltinList)
        {
            Singleton.Register(builtinColumnTypeInfo);
        }

        foreach (var customColumnTypeInfo in CustomList)
        {
            Singleton.Register(customColumnTypeInfo);
        }

        Singleton.Validate();
    }

    private readonly List<IColumnTypeInfo> _list;
    private readonly Dictionary<Type, IColumnTypeInfo> _map;
    private bool _dirty = false;

    public ColumnTypeInfoRegistry()
    {
        _list = new List<IColumnTypeInfo>();
        _map = new Dictionary<Type, IColumnTypeInfo>();
    }

    public void Register(IColumnTypeInfo columnTypeInfo)
    {
        Debug.Assert(!_list.Contains(columnTypeInfo));
        _list.Add(columnTypeInfo);
        _map.Add(columnTypeInfo.GetPropertyType(), columnTypeInfo);
        _dirty = true;
    }

    public IColumnTypeInfo? GetByDataType(Type type)
    {
        return _map.GetValueOrDefault(type);
    }

    public IColumnTypeInfo GetRequiredByDataType(Type type)
    {
        return GetByDataType(type) ?? throw new Exception("Unsupported type.");
    }

    public string GetSqlTypeRecursive(IColumnTypeInfo columnTypeInfo)
    {
        EnsureValidity();

        IColumnTypeInfo? current = columnTypeInfo;
        while (current is not IBuiltinColumnTypeInfo)
        {
            current = GetByDataType(current.GetUnderlineType());
            Debug.Assert(current is not null);
        }

        return ((IBuiltinColumnTypeInfo)current).GetSqlType();
    }

    public DbType GetDbTypeRecursive(IColumnTypeInfo columnTypeInfo)
    {
        EnsureValidity();

        IColumnTypeInfo? current = columnTypeInfo;
        if (current is not IBuiltinColumnTypeInfo)
        {
            current = GetByDataType(current.GetUnderlineType());
            Debug.Assert(current is not null);
        }

        return ((IBuiltinColumnTypeInfo)current).GetDbType();
    }

    public object? ConvertToUnderlineRecursive(object? value)
    {
        EnsureValidity();

        if (value is null)
        {
            return null;
        }

        IColumnTypeInfo? current = GetByDataType(value.GetType());
        if (current is null)
        {
            return value;
        }

        while (current is not IBuiltinColumnTypeInfo)
        {
            value = current.ConvertToUnderline(value);
            current = GetByDataType(current.GetUnderlineType());
            Debug.Assert(current is not null);
        }

        return value;
    }

    public string GetSqlType(Type type)
    {
        return GetSqlTypeRecursive(GetRequiredByDataType(type));
    }

    public DbType GetDbType(Type type)
    {
        return GetDbTypeRecursive(GetRequiredByDataType(type));
    }

    public object? ConvertToUnderline(object? value)
    {
        return ConvertToUnderlineRecursive(value);
    }

    public void Validate()
    {
        foreach (var columnTypeInfo in _list)
        {
            columnTypeInfo.Validate(_map);
        }
    }

    public void EnsureValidity()
    {
        if (_dirty)
        {
            Validate();
        }
    }

    public IEnumerable<JsonConverter> GetJsonConverters()
    {
        foreach (var columnTypeInfo in _list)
        {
            var converter = columnTypeInfo.GetOptionalJsonConverter();
            if (converter is not null)
                yield return converter;
        }
    }
}
