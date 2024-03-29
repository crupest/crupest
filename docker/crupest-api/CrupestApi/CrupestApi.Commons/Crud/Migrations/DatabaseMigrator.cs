using System.Data;

namespace CrupestApi.Commons.Crud.Migrations;

public class TableColumn
{
    public TableColumn(string name, string type, bool notNull, int primaryKey)
    {
        Name = name;
        Type = type;
        NotNull = notNull;
        PrimaryKey = primaryKey;
    }

    public string Name { get; set; }
    public string Type { get; set; }
    public bool NotNull { get; set; }

    /// <summary>
    /// 0 if not primary key. 1-based index if in primary key.
    /// </summary>
    public int PrimaryKey { get; set; }
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
    Table? GetTable(IDbConnection dbConnection, string tableName);
    Table ConvertTableInfoToTable(TableInfo tableInfo);
    string GenerateCreateTableColumnSqlSegment(TableColumn column);
    string GenerateCreateTableSql(string tableName, IEnumerable<TableColumn> columns);
    bool NeedMigrate(IDbConnection dbConnection, TableInfo tableInfo);
    void AutoMigrate(IDbConnection dbConnection, TableInfo tableInfo);
}
