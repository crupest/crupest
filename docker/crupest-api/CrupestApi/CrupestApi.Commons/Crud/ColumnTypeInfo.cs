using System.Collections.Generic;
using System.Data;
using System.Diagnostics;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace CrupestApi.Commons.Crud;

/// <summary> Represents a type of one column. </summary>
public abstract class ColumnTypeInfo
{
    protected ColumnTypeInfo(Type supportedType)
    {
        SupportedType = supportedType;
    }

    public Type SupportedType { get; }

    public bool IsOfSupportedType(object value)
    {
        return value is not null && SupportedType.IsAssignableFrom(value.GetType());
    }

    public abstract BasicColumnTypeInfo UnderlineType { get; }

    public abstract IReadOnlyList<DerivedColumnTypeInfo> DerivedTypes { get; }

    public abstract string SqlType { get; }

    public abstract DbType DbType { get; }

    /// <summary>
    /// An optional json converter for this type.
    /// </summary>
    /// <returns>The converter if this type needs a json converter. Otherwise null.</returns>
    public abstract JsonConverter? GetJsonConverter();

    /// <summary>
    /// Convert a value into underline type. 
    /// </summary>
    public abstract object? ConvertToUnderline(object? value);

    /// <summary>
    /// Convert to a value of this type from value of underline type.
    /// </summary>
    public abstract object? ConvertFromUnderline(object? underlineValue);
}

public class BasicColumnTypeInfo : ColumnTypeInfo
{
    public static BasicColumnTypeInfo<char> CharColumnTypeInfo { get; } = new BasicColumnTypeInfo<char>("INTEGER", DbType.Int32);
    public static BasicColumnTypeInfo<short> ShortColumnTypeInfo { get; } = new BasicColumnTypeInfo<short>("INTEGER", DbType.Int32);
    public static BasicColumnTypeInfo<int> IntColumnTypeInfo { get; } = new BasicColumnTypeInfo<int>("INTEGER", DbType.Int32);
    public static BasicColumnTypeInfo<long> LongColumnTypeInfo { get; } = new BasicColumnTypeInfo<long>("INTEGER", DbType.Int64);
    public static BasicColumnTypeInfo<float> FloatColumnTypeInfo { get; } = new BasicColumnTypeInfo<float>("REAL", DbType.Double);
    public static BasicColumnTypeInfo<double> DoubleColumnTypeInfo { get; } = new BasicColumnTypeInfo<double>("REAL", DbType.Double);
    public static BasicColumnTypeInfo<string> StringColumnTypeInfo { get; } = new BasicColumnTypeInfo<string>("TEXT", DbType.String);
    public static BasicColumnTypeInfo<byte[]> ByteColumnTypeInfo { get; } = new BasicColumnTypeInfo<byte[]>("BLOB", DbType.Binary);

    private readonly string _sqlType;
    private readonly DbType _dbType;
    internal List<DerivedColumnTypeInfo> _derivedTypes = new List<DerivedColumnTypeInfo>();

    public BasicColumnTypeInfo(Type type, string sqlType, DbType dbType)
    : base(type)
    {
        _sqlType = sqlType;
        _dbType = dbType;
    }

    public override BasicColumnTypeInfo UnderlineType => this;

    public override IReadOnlyList<DerivedColumnTypeInfo> DerivedTypes => _derivedTypes;

    public override string SqlType => _sqlType;

    public override DbType DbType => _dbType;

    public override object? ConvertToUnderline(object? value)
    {
        Debug.Assert(value is null || SupportedType.IsInstanceOfType(value));
        return value;
    }

    public override object? ConvertFromUnderline(object? underlineValue)
    {
        Debug.Assert(underlineValue is null || SupportedType.IsInstanceOfType(underlineValue));
        return underlineValue;
    }

    public override JsonConverter? GetJsonConverter()
    {
        return null;
    }
}

public class BasicColumnTypeInfo<T> : BasicColumnTypeInfo
{
    public BasicColumnTypeInfo(string sqlType, DbType dbType) : base(typeof(T), sqlType, dbType) { }
}

public abstract class DerivedColumnTypeInfo : ColumnTypeInfo
{
    protected DerivedColumnTypeInfo(Type supportedType, BasicColumnTypeInfo underlineType)
        : base(supportedType)
    {
        UnderlineType = underlineType;
        UnderlineType._derivedTypes.Add(this);
    }

    public override BasicColumnTypeInfo UnderlineType { get; }

    private static readonly List<DerivedColumnTypeInfo> _emptyList = new List<DerivedColumnTypeInfo>();

    public override IReadOnlyList<DerivedColumnTypeInfo> DerivedTypes => _emptyList;

    public override string SqlType => UnderlineType!.SqlType;

    public override DbType DbType => UnderlineType!.DbType;
}

public class DateTimeColumnTypeInfo : DerivedColumnTypeInfo
{
    private readonly DateTimeJsonConverter _jsonConverter = new DateTimeJsonConverter();

    public DateTimeColumnTypeInfo()
        : base(typeof(DateTime), BasicColumnTypeInfo.LongColumnTypeInfo)
    {

    }

    public override JsonConverter GetJsonConverter()
    {
        return _jsonConverter;
    }

    public override object? ConvertToUnderline(object? value)
    {
        if (value is null) return null;

        Debug.Assert(value is DateTime);
        return new DateTimeOffset((DateTime)value).ToUnixTimeSeconds();
    }

    public override object? ConvertFromUnderline(object? underlineValue)
    {
        if (underlineValue is null) return null;

        Debug.Assert(typeof(long).IsAssignableFrom(underlineValue.GetType()));
        return DateTimeOffset.FromUnixTimeSeconds((long)underlineValue).LocalDateTime;
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

public class ColumnTypeRegistry
{
    public static IReadOnlyList<BasicColumnTypeInfo> BasicTypeList = new List<BasicColumnTypeInfo>()
    {
        BasicColumnTypeInfo.CharColumnTypeInfo,
        BasicColumnTypeInfo.ShortColumnTypeInfo,
        BasicColumnTypeInfo.IntColumnTypeInfo,
        BasicColumnTypeInfo.LongColumnTypeInfo,
        BasicColumnTypeInfo.FloatColumnTypeInfo,
        BasicColumnTypeInfo.DoubleColumnTypeInfo,
        BasicColumnTypeInfo.StringColumnTypeInfo,
        BasicColumnTypeInfo.ByteColumnTypeInfo,
    };

    public static ColumnTypeRegistry Instance { get; }

    static ColumnTypeRegistry()
    {
        Instance = new ColumnTypeRegistry();

        foreach (var basicColumnTypeInfo in BasicTypeList)
        {
            Instance.Register(basicColumnTypeInfo);
        }

        Instance.Register(new DateTimeColumnTypeInfo());
    }

    private readonly List<ColumnTypeInfo> _list;
    private readonly Dictionary<Type, ColumnTypeInfo> _map;

    public ColumnTypeRegistry()
    {
        _list = new List<ColumnTypeInfo>();
        _map = new Dictionary<Type, ColumnTypeInfo>();
    }

    public void Register(ColumnTypeInfo columnTypeInfo)
    {
        Debug.Assert(!_list.Contains(columnTypeInfo));
        Debug.Assert(!_map.ContainsKey(columnTypeInfo.SupportedType));
        _list.Add(columnTypeInfo);
        _map.Add(columnTypeInfo.SupportedType, columnTypeInfo);
    }

    public ColumnTypeInfo? Get(Type type)
    {
        return _map.GetValueOrDefault(type);
    }

    public ColumnTypeInfo? Get<T>()
    {
        return Get(typeof(T));
    }

    public ColumnTypeInfo GetRequired(Type type)
    {
        return Get(type) ?? throw new Exception("Unsupported type.");
    }

    public ColumnTypeInfo GetRequired<T>()
    {
        return GetRequired(typeof(T));
    }

    public object? ConvertToUnderline(object? value)
    {
        if (value is null) return null;

        var type = value.GetType();
        var columnTypeInfo = Get(type);
        if (columnTypeInfo is null) throw new Exception("Unsupported type.");

        return columnTypeInfo.ConvertToUnderline(value);
    }

    public IEnumerable<JsonConverter> GetJsonConverters()
    {
        foreach (var columnTypeInfo in _list)
        {
            var converter = columnTypeInfo.GetJsonConverter();
            if (converter is not null)
                yield return converter;
        }
    }
}
