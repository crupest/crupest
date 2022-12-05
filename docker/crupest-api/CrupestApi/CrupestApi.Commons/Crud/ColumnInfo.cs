using System.Reflection;

namespace CrupestApi.Commons.Crud;

public class ColumnInfo
{
    private Type ExtractRealTypeFromNullable(Type type)
    {
        if (type.IsGenericType && type.GetGenericTypeDefinition() == typeof(Nullable<>))
        {
            return type.GetGenericArguments()[0];
        }

        return type;
    }

    // A column with no property.
    public ColumnInfo(Type entityType, string sqlColumnName, bool isPrimaryKey, bool isAutoIncrement, IColumnTypeInfo typeInfo)
    {
        EntityType = entityType;
        PropertyName = null;
        PropertyType = typeof(int);
        PropertyRealType = typeof(int);
        SqlColumnName = sqlColumnName;
        ColumnTypeInfo = typeInfo;
        Nullable = false;
        IsPrimaryKey = isPrimaryKey;
        IsAutoIncrement = isAutoIncrement;
    }

    public ColumnInfo(Type entityType, string entityPropertyName)
    {
        EntityType = entityType;
        PropertyName = entityPropertyName;

        var property = entityType.GetProperty(entityPropertyName);

        if (property is null)
            throw new Exception("Public property with given name does not exist.");

        PropertyType = property.PropertyType;
        PropertyRealType = ExtractRealTypeFromNullable(PropertyType);

        var columnAttribute = property.GetCustomAttribute<ColumnAttribute>();
        if (columnAttribute is null)
        {
            SqlColumnName = PropertyName;
            Nullable = true;
        }
        else
        {
            SqlColumnName = columnAttribute.DatabaseName ?? PropertyName;
            Nullable = !columnAttribute.NonNullable;
        }
        ColumnTypeInfo = ColumnTypeInfoRegistry.Singleton.GetRequiredByDataType(PropertyRealType);

    }

    public Type EntityType { get; }
    // If null, there is no corresponding property.
    public string? PropertyName { get; }
    public Type PropertyType { get; }
    public Type PropertyRealType { get; }
    public string SqlColumnName { get; }
    public IColumnTypeInfo ColumnTypeInfo { get; }
    public bool Nullable { get; }
    public bool IsPrimaryKey { get; }
    public bool IsAutoIncrement { get; }
}