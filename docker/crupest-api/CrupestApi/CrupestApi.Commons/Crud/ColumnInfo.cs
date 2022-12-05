using System.Reflection;
using System.Text;

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
    public ColumnInfo(Type entityType, string sqlColumnName, bool isPrimaryKey, bool isAutoIncrement, IColumnTypeInfo typeInfo, ColumnTypeInfoRegistry? typeRegistry = null)
    {
        if (typeRegistry is null)
        {
            typeRegistry = ColumnTypeInfoRegistry.Singleton;
        }

        EntityType = entityType;
        PropertyName = null;
        PropertyType = typeof(int);
        PropertyRealType = typeof(int);
        SqlColumnName = sqlColumnName;
        ColumnTypeInfo = typeInfo;
        Nullable = false;
        IsPrimaryKey = isPrimaryKey;
        IsAutoIncrement = isAutoIncrement;
        TypeRegistry = typeRegistry;
    }

    public ColumnInfo(Type entityType, string entityPropertyName, ColumnTypeInfoRegistry? typeRegistry = null)
    {
        if (typeRegistry is null)
        {
            typeRegistry = ColumnTypeInfoRegistry.Singleton;
        }

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

        ColumnTypeInfo = typeRegistry.GetRequiredByDataType(PropertyRealType);
        TypeRegistry = typeRegistry;
    }

    public Type EntityType { get; }
    // If null, there is no corresponding property.
    public string? PropertyName { get; }
    public Type PropertyType { get; }
    public Type PropertyRealType { get; }
    public string SqlColumnName { get; }
    public ColumnTypeInfoRegistry TypeRegistry { get; set; }
    public IColumnTypeInfo ColumnTypeInfo { get; }
    public bool Nullable { get; }
    public bool IsPrimaryKey { get; }
    public bool IsAutoIncrement { get; }

    public string SqlType => TypeRegistry.GetSqlType(ColumnTypeInfo);

    public string GenerateCreateTableColumnString()
    {
        StringBuilder result = new StringBuilder();
        result.Append(SqlColumnName);
        result.Append(' ');
        result.Append(SqlType);
        if (IsPrimaryKey)
        {
            result.Append(' ');
            result.Append("PRIMARY KEY");
        }
        else if (!Nullable)
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
