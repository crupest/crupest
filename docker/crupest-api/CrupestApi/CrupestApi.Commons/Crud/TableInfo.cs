namespace CrupestApi.Commons.Crud;

public class TableInfo
{
    public TableInfo(Type entityType)
    {
        EntityType = entityType;

        var properties = entityType.GetProperties();

        var columnInfos = new List<ColumnInfo>();

        bool hasPrimaryKey = false;
        bool hasId = false;

        foreach (var property in properties)
        {
            var columnInfo = new ColumnInfo(entityType, property.Name);
            columnInfos.Add(columnInfo);
            if (columnInfo.IsPrimaryKey)
                hasPrimaryKey = true;
            if (columnInfo.SqlColumnName.Equals("id", StringComparison.OrdinalIgnoreCase))
            {
                hasId = true;
            }
        }

        if (!hasPrimaryKey)
        {
            if (hasId) throw new Exception("A column named id already exists but is not primary key.");
            var columnInfo = new ColumnInfo(entityType, "id", true, true, ColumnTypeInfoRegistry.Singleton.GetRequiredByDataType(typeof(int)));
            columnInfos.Add(columnInfo);
        }

        ColumnInfos = columnInfos;

        CheckValidity();
    }

    public Type EntityType { get; }
    public IReadOnlyList<ColumnInfo> ColumnInfos { get; }

    public void CheckValidity()
    {
        // Check if there is only one primary key.
        bool hasPrimaryKey = false;
        foreach (var column in ColumnInfos)
        {
            if (column.IsPrimaryKey)
            {
                if (hasPrimaryKey) throw new Exception("Two columns are primary key.");
                hasPrimaryKey = true;
            }
        }

        if (!hasPrimaryKey) throw new Exception("No column is primary key.");

        // Check two columns have the same sql name.
        HashSet<string> sqlNameSet = new HashSet<string>();

        foreach (var column in ColumnInfos)
        {
            if (sqlNameSet.Contains(column.SqlColumnName))
                throw new Exception($"Two columns have the same sql name '{column.SqlColumnName}'.");
            sqlNameSet.Add(column.SqlColumnName);
        }
    }

    public string GenerateCreateTableSql()
    {
        throw new NotImplementedException();
    }
}