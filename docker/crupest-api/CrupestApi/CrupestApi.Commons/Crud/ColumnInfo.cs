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
    public ColumnInfo(Type entityType, string sqlColumnName, bool isPrimaryKey, bool isAutoIncrement, IColumnTypeInfo typeInfo, ColumnIndexType indexType = ColumnIndexType.None, ColumnTypeInfoRegistry? typeRegistry = null)
    {
        if (typeRegistry is null)
        {
            typeRegistry = ColumnTypeInfoRegistry.Singleton;
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

    public ColumnInfo(Type entityType, string entityPropertyName, ColumnTypeInfoRegistry? typeRegistry = null)
    {
        if (typeRegistry is null)
        {
            typeRegistry = ColumnTypeInfoRegistry.Singleton;
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

        ColumnTypeInfo = typeRegistry.GetRequiredByDataType(PropertyRealType);
        TypeRegistry = typeRegistry;

        if (DefaultEmptyForString)
        {
            EntityPostGet += (entity, column, _, _) =>
            {
                var pi = column.PropertyInfo;
                if (pi is not null && column.ColumnTypeInfo.GetUnderlineType() == typeof(string))
                {
                    var value = pi.GetValue(entity);
                    if (value is null)
                    {
                        pi.SetValue(entity, string.Empty);
                    }
                }
                return Task.CompletedTask;
            };
        }
    }

    public Type EntityType { get; }
    // If null, there is no corresponding property.
    public PropertyInfo? PropertyInfo { get; } = null;
    public string PropertyName { get; }
    public Type PropertyType { get; }
    public Type PropertyRealType { get; }
    public string SqlColumnName { get; }
    public ColumnTypeInfoRegistry TypeRegistry { get; set; }
    public IColumnTypeInfo ColumnTypeInfo { get; }
    public bool Nullable { get; }
    public bool IsPrimaryKey { get; }
    public bool IsAutoIncrement { get; }
    public ColumnIndexType IndexType { get; }
    public bool DefaultEmptyForString { get; }

    public event EntityPreSave? EntityPreSave;
    public event EntityPostGet? EntityPostGet;

    public string SqlType => TypeRegistry.GetSqlTypeRecursive(ColumnTypeInfo);

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
