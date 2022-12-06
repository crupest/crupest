using System.Data;
using System.Reflection;
using System.Text;

namespace CrupestApi.Commons.Crud;

public delegate Task EntityPreSave(object? entity, ColumnInfo column, TableInfo table, IDbConnection connection);
public delegate Task EntityPostGet(object? entity, ColumnInfo column, TableInfo table, IDbConnection connection);

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
    public ColumnInfo(Type entityType, string sqlColumnName, bool isPrimaryKey, bool isAutoIncrement, ColumnTypeInfo typeInfo, ColumnIndexType indexType = ColumnIndexType.None, ColumnTypeRegistry? typeRegistry = null)
    {
        if (typeRegistry is null)
        {
            typeRegistry = ColumnTypeRegistry.Instance;
        }

        EntityType = entityType;
        PropertyName = sqlColumnName;
        PropertyType = typeof(int);
        PropertyRealType = typeof(int);
        SqlColumnName = sqlColumnName;
        ColumnTypeInfo = typeInfo;
        Nullable = false;
        IsPrimaryKey = isPrimaryKey;
        IsAutoIncrement = isAutoIncrement;
        TypeRegistry = typeRegistry;
        IndexType = indexType;
    }

    public ColumnInfo(Type entityType, string entityPropertyName, ColumnTypeRegistry? typeRegistry = null)
    {
        if (typeRegistry is null)
        {
            typeRegistry = ColumnTypeRegistry.Instance;
        }

        EntityType = entityType;
        PropertyName = entityPropertyName;
        PropertyInfo = entityType.GetProperty(entityPropertyName);

        if (PropertyInfo is null)
            throw new Exception("Public property with given name does not exist.");

        PropertyType = PropertyInfo.PropertyType;
        PropertyRealType = ExtractRealTypeFromNullable(PropertyType);

        var columnAttribute = PropertyInfo.GetCustomAttribute<ColumnAttribute>();
        if (columnAttribute is null)
        {
            SqlColumnName = PropertyName;
            Nullable = true;
            IndexType = ColumnIndexType.None;
            DefaultEmptyForString = false;
        }
        else
        {
            SqlColumnName = columnAttribute.DatabaseName ?? PropertyName;
            Nullable = !columnAttribute.NonNullable;
            IndexType = columnAttribute.IndexType;
            DefaultEmptyForString = columnAttribute.DefaultEmptyForString;
        }

        ColumnTypeInfo = typeRegistry.GetRequired(PropertyRealType);
        TypeRegistry = typeRegistry;
    }

    public Type EntityType { get; }
    // If null, there is no corresponding property.
    public PropertyInfo? PropertyInfo { get; } = null;
    public string PropertyName { get; }
    public Type PropertyType { get; }
    public Type PropertyRealType { get; }
    public string SqlColumnName { get; }
    public ColumnTypeRegistry TypeRegistry { get; set; }
    public ColumnTypeInfo ColumnTypeInfo { get; }
    public bool Nullable { get; }
    public bool IsPrimaryKey { get; }
    public bool IsAutoIncrement { get; }
    public ColumnIndexType IndexType { get; }

    // TODO: Implement this behavior.
    public bool DefaultEmptyForString { get; }

    public string SqlType => ColumnTypeInfo.SqlType;

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
