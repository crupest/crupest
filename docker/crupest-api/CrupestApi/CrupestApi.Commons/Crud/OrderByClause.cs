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

public class OrderByClause : List<OrderByItem>
{
    public OrderByClause(IEnumerable<OrderByItem> items)
        : base(items)
    {
    }

    public OrderByClause(params OrderByItem[] items)
        : base(items)
    {
    }

    public static OrderByClause Create(params OrderByItem[] items)
    {
        return new OrderByClause(items);
    }

    public string GenerateSql()
    {
        return "ORDER BY " + string.Join(", ", this.Select(i => i.GenerateSql()));
    }
}