using System.Diagnostics;

namespace CrupestApi.Commons;

public interface IColumnTypeInfo
{
    Type GetDataType();
    Type GetDatabaseType();
    object ConvertToDatabase(object data);
    object ConvertFromDatabase(object databaseData);

    void Validate(IReadOnlyDictionary<Type, IColumnTypeInfo> typeInfoMap)
    {
        var typeSet = new HashSet<Type>();

        IColumnTypeInfo current = this;

        while (!typeof(BuiltinColumnTypeInfo<>).IsInstanceOfType(current))
        {
            var dataType = GetDataType();

            if (typeSet.Contains(dataType))
            {
                throw new Exception("Circular reference detected.");
            }
            typeSet.Add(dataType);

            var databaseType = GetDatabaseType();
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
    string GetSqlType();
}

public class BuiltinColumnTypeInfo<T> : IBuiltinColumnTypeInfo
{
    private readonly string _sqlType;

    public BuiltinColumnTypeInfo(string sqlType)
    {
        _sqlType = sqlType;
    }

    public Type GetDataType()
    {
        return typeof(T);
    }

    public Type GetDatabaseType()
    {
        return typeof(T);
    }

    public string GetSqlType()
    {
        return _sqlType;
    }

    public T ConvertToDatabase(T data)
    {
        return data;
    }

    public T ConvertFromDatabase(T databaseData)
    {
        return databaseData;
    }

    object IColumnTypeInfo.ConvertToDatabase(object data)
    {
        return data;
    }

    object IColumnTypeInfo.ConvertFromDatabase(object databaseData)
    {
        return databaseData;
    }
}

public abstract class CustomColumnTypeInfo<TDataType, TDatabaseType> : IColumnTypeInfo
 where TDataType : notnull where TDatabaseType : notnull
{

    public Type GetDataType()
    {
        return typeof(TDataType);
    }

    public Type GetDatabaseType()
    {
        return typeof(TDatabaseType);
    }

    public abstract TDatabaseType ConvertToDatabase(TDataType data);
    public abstract TDataType ConvertFromDatabase(TDatabaseType databaseData);

    object IColumnTypeInfo.ConvertToDatabase(object data)
    {
        Debug.Assert(typeof(TDataType).IsInstanceOfType(data));
        return ConvertToDatabase((TDataType)data);
    }

    object IColumnTypeInfo.ConvertFromDatabase(object databaseData)
    {
        Debug.Assert(typeof(TDatabaseType).IsInstanceOfType(databaseData));
        return ConvertFromDatabase((TDatabaseType)databaseData);
    }
}

public class ColumnTypeInfoRegistry
{
    public static IReadOnlyList<IColumnTypeInfo> BuiltinList = new List<IColumnTypeInfo>()
    {
        new BuiltinColumnTypeInfo<char>("INTEGER"),
        new BuiltinColumnTypeInfo<short>("INTEGER"),
        new BuiltinColumnTypeInfo<int>("INTEGER"),
        new BuiltinColumnTypeInfo<long>("INTEGER"),
        new BuiltinColumnTypeInfo<float>("REAL"),
        new BuiltinColumnTypeInfo<double>("REAL"),
        new BuiltinColumnTypeInfo<string>("TEXT"),
        new BuiltinColumnTypeInfo<byte[]>("BLOB"),
    };


    public static IReadOnlyList<IColumnTypeInfo> CustomList = new List<IColumnTypeInfo>()
    {
        // TODO: Add custom ones.
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
        _map.Add(columnTypeInfo.GetDataType(), columnTypeInfo);
        _dirty = true;
    }

    public IColumnTypeInfo? GetByDataType(Type type)
    {
        return _map.GetValueOrDefault(type);
    }

    public string GetSqlType(Type type)
    {
        EnsureValidity();

        IColumnTypeInfo? current = GetByDataType(type);
        if (current is null)
        {
            throw new Exception("Unsupported type for sql.");
        }

        while (!typeof(IBuiltinColumnTypeInfo).IsInstanceOfType(current))
        {
            current = GetByDataType(current.GetDatabaseType());
            Debug.Assert(current is not null);
        }

        return ((IBuiltinColumnTypeInfo)current).GetSqlType();
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

}
