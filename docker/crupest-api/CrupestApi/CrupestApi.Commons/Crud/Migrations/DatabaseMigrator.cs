using System.Data;

namespace CrupestApi.Commons.Crud.Migrations;

public class TableColumn : IEquatable<TableColumn>
{
    public TableColumn(string name, string type, bool isNullable, int primaryKey)
    {
        Name = name.ToLowerInvariant();
        Type = type.ToLowerInvariant();
        IsNullable = isNullable;
        PrimaryKey = primaryKey;
    }

    public string Name { get; set; }
    public string Type { get; set; }
    public bool IsNullable { get; set; }

    /// <summary>
    /// 0 if not primary key. 1-based index if in primary key.
    /// </summary>
    public int PrimaryKey { get; set; }

    bool IEquatable<TableColumn>.Equals(TableColumn? other)
    {
        if (other is null)
        {
            return false;
        }

        return Name == other.Name && Type == other.Type && IsNullable == other.IsNullable && PrimaryKey == other.PrimaryKey;
    }

    public override bool Equals(object? obj)
    {
        return Equals(obj as TableColumn);
    }

    public override int GetHashCode()
    {
        return HashCode.Combine(Name, Type, IsNullable, PrimaryKey);
    }
}

public class Table
{
    public Table(string name)
    {
        Name = name;
    }

    public string Name { get; set; }
    public List<TableColumn> Columns { get; set; } = new List<TableColumn>();
}

public interface IDatabaseMigrator
{
    Table GetTable(IDbConnection dbConnection, string name);
    Table ConvertTableInfoToTable(TableInfo tableInfo);
    string GenerateCreateTableColumnSqlSegment(TableColumn column);
    string GenerateCreateTableSql(string tableName, IEnumerable<TableColumn> columns);
    bool TableExists(IDbConnection connection, string tableName);
    bool NeedMigrate(IDbConnection dbConnection, TableInfo tableInfo);
    bool CanAutoMigrate(IDbConnection dbConnection, TableInfo tableInfo);
    void AutoMigrate(IDbConnection dbConnection, TableInfo tableInfo);
}
