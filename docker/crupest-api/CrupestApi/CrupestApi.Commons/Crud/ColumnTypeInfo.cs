using System.Data;
using System.Diagnostics;
using System.Globalization;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace CrupestApi.Commons.Crud;

public interface IColumnTypeInfo
{
    public static IColumnTypeInfo IntColumnTypeInfo { get; } = new SimpleColumnTypeInfo<int>();
    public static IColumnTypeInfo ShortColumnTypeInfo { get; } = new SimpleColumnTypeInfo<short>();
    public static IColumnTypeInfo SByteColumnTypeInfo { get; } = new SimpleColumnTypeInfo<sbyte>();
    public static IColumnTypeInfo LongColumnTypeInfo { get; } = new SimpleColumnTypeInfo<long>();
    public static IColumnTypeInfo FloatColumnTypeInfo { get; } = new SimpleColumnTypeInfo<float>();
    public static IColumnTypeInfo DoubleColumnTypeInfo { get; } = new SimpleColumnTypeInfo<double>();
    public static IColumnTypeInfo StringColumnTypeInfo { get; } = new SimpleColumnTypeInfo<string>();
    public static IColumnTypeInfo BytesColumnTypeInfo { get; } = new SimpleColumnTypeInfo<byte[]>();
    public static IColumnTypeInfo DateTimeColumnTypeInfo { get; } = new DateTimeColumnTypeInfo();

    Type ClrType { get; }
    Type DatabaseClrType { get; }
    bool IsSimple { get { return ClrType == DatabaseClrType; } }
    DbType DbType
    {
        get
        {
            if (DatabaseClrType == typeof(int))
            {
                return DbType.Int32;
            }
            else if (DatabaseClrType == typeof(long))
            {
                return DbType.Int64;
            }
            else if (DatabaseClrType == typeof(short))
            {
                return DbType.Int16;
            }
            else if (DatabaseClrType == typeof(sbyte))
            {
                return DbType.SByte;
            }
            else if (DatabaseClrType == typeof(double))
            {
                return DbType.Double;
            }
            else if (DatabaseClrType == typeof(float))
            {
                return DbType.Single;
            }
            else if (DatabaseClrType == typeof(string))
            {
                return DbType.String;
            }
            else if (DatabaseClrType == typeof(byte[]))
            {
                return DbType.Binary;
            }
            else
            {
                throw new Exception("Can't deduce DbType.");
            }
        }
    }

    string GetSqlTypeString(string? dbProviderId = null)
    {
        // Default implementation for SQLite
        return DbType switch
        {
            DbType.String => "TEXT",
            DbType.Int16 or DbType.Int32 or DbType.Int64 => "INTEGER",
            DbType.Single or DbType.Double => "REAL",
            DbType.Binary => "BLOB",
            _ => throw new Exception($"Unsupported DbType: {DbType}"),
        };
    }

    JsonConverter? JsonConverter { get { return null; } }

    // You must override this method if ClrType != DatabaseClrType
    object? ConvertFromDatabase(object? databaseValue)
    {
        Debug.Assert(IsSimple);
        return databaseValue;
    }

    // You must override this method if ClrType != DatabaseClrType
    object? ConvertToDatabase(object? value)
    {
        Debug.Assert(IsSimple);
        return value;
    }
}

public interface IColumnTypeProvider
{
    IReadOnlyList<IColumnTypeInfo> GetAll();
    IColumnTypeInfo Get(Type clrType);

    IList<IColumnTypeInfo> GetAllCustom()
    {
        return GetAll().Where(t => !t.IsSimple).ToList();
    }
}

public class SimpleColumnTypeInfo<T> : IColumnTypeInfo
{
    public Type ClrType => typeof(T);
    public Type DatabaseClrType => typeof(T);
}

public class DateTimeColumnTypeInfo : IColumnTypeInfo
{
    private JsonConverter<DateTime> _jsonConverter;

    public DateTimeColumnTypeInfo()
    {
        _jsonConverter = new DateTimeJsonConverter(this);
    }

    public Type ClrType => typeof(DateTime);
    public Type DatabaseClrType => typeof(string);

    public JsonConverter JsonConverter => _jsonConverter;

    public object? ConvertToDatabase(object? value)
    {
        if (value is null) return null;
        Debug.Assert(value is DateTime);
        return ((DateTime)value).ToUniversalTime().ToString("s") + "Z";
    }

    public object? ConvertFromDatabase(object? databaseValue)
    {
        if (databaseValue is null) return null;
        Debug.Assert(databaseValue is string);
        var databaseString = (string)databaseValue;
        var dateTimeStyles = DateTimeStyles.None;
        if (databaseString.Length > 0 && databaseString[^1] == 'Z')
        {
            databaseString = databaseString.Substring(0, databaseString.Length - 1);
            dateTimeStyles = DateTimeStyles.AssumeUniversal & DateTimeStyles.AdjustToUniversal;
        }
        return DateTime.ParseExact(databaseString, "s", null, dateTimeStyles);
    }
}

public class DateTimeJsonConverter : JsonConverter<DateTime>
{
    private readonly DateTimeColumnTypeInfo _typeInfo;

    public DateTimeJsonConverter(DateTimeColumnTypeInfo typeInfo)
    {
        _typeInfo = typeInfo;
    }

    public override DateTime Read(ref Utf8JsonReader reader, Type typeToConvert, JsonSerializerOptions options)
    {
        var databaseValue = reader.GetString();
        return (DateTime)_typeInfo.ConvertFromDatabase(databaseValue)!;
    }

    public override void Write(Utf8JsonWriter writer, DateTime value, JsonSerializerOptions options)
    {
        var databaseValue = _typeInfo.ConvertToDatabase(value);
        writer.WriteStringValue((string)databaseValue!);
    }
}

public class ColumnTypeProvider : IColumnTypeProvider
{
    private Dictionary<Type, IColumnTypeInfo> _typeMap = new Dictionary<Type, IColumnTypeInfo>();

    public ColumnTypeProvider()
    {
        _typeMap.Add(IColumnTypeInfo.IntColumnTypeInfo.ClrType, IColumnTypeInfo.IntColumnTypeInfo);
        _typeMap.Add(IColumnTypeInfo.ShortColumnTypeInfo.ClrType, IColumnTypeInfo.ShortColumnTypeInfo);
        _typeMap.Add(IColumnTypeInfo.SByteColumnTypeInfo.ClrType, IColumnTypeInfo.SByteColumnTypeInfo);
        _typeMap.Add(IColumnTypeInfo.LongColumnTypeInfo.ClrType, IColumnTypeInfo.LongColumnTypeInfo);
        _typeMap.Add(IColumnTypeInfo.FloatColumnTypeInfo.ClrType, IColumnTypeInfo.FloatColumnTypeInfo);
        _typeMap.Add(IColumnTypeInfo.DoubleColumnTypeInfo.ClrType, IColumnTypeInfo.DoubleColumnTypeInfo);
        _typeMap.Add(IColumnTypeInfo.StringColumnTypeInfo.ClrType, IColumnTypeInfo.StringColumnTypeInfo);
        _typeMap.Add(IColumnTypeInfo.BytesColumnTypeInfo.ClrType, IColumnTypeInfo.BytesColumnTypeInfo);
        _typeMap.Add(IColumnTypeInfo.DateTimeColumnTypeInfo.ClrType, IColumnTypeInfo.DateTimeColumnTypeInfo);
    }

    public IReadOnlyList<IColumnTypeInfo> GetAll()
    {
        return _typeMap.Values.ToList();
    }

    // This is thread-safe.
    public IColumnTypeInfo Get(Type clrType)
    {
        if (_typeMap.TryGetValue(clrType, out var typeInfo))
        {
            return typeInfo;
        }
        else
        {
            if (clrType.IsGenericType && clrType.GetGenericTypeDefinition() == typeof(Nullable<>))
            {
                clrType = clrType.GetGenericArguments()[0];
                return Get(clrType);
            }

            throw new Exception($"Unsupported type: {clrType}");
        }
    }
}
