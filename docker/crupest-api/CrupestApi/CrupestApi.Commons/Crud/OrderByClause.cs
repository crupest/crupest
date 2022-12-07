using Dapper;

namespace CrupestApi.Commons.Crud;

public class OrderByItem
{
    public OrderByItem(string columnName, bool isAscending)
    {
        ColumnName = columnName;
        IsAscending = isAscending;
    }

    public string ColumnName { get; }
    public bool IsAscending { get; }

    public string GenerateSql()
    {
        return $"{ColumnName} {(IsAscending ? "ASC" : "DESC")}";
    }
}

public interface IOrderByClause : IClause
{
    List<OrderByItem> Items { get; }
    (string sql, DynamicParameters parameters) GenerateSql(string? dbProviderId = null);
}

public class OrderByClause : IOrderByClause
{
    public List<OrderByItem> Items { get; } = new List<OrderByItem>();

    public OrderByClause(params OrderByItem[] items)
    {
        Items.AddRange(items);
    }

    public static OrderByClause Create(params OrderByItem[] items)
    {
        return new OrderByClause(items);
    }

    public List<string> GetRelatedColumns()
    {
        return Items.Select(x => x.ColumnName).ToList();
    }

    public (string sql, DynamicParameters parameters) GenerateSql(string? dbProviderId = null)
    {
        return ("ORDER BY " + string.Join(", ", Items.Select(i => i.GenerateSql())), new DynamicParameters());
    }
}
