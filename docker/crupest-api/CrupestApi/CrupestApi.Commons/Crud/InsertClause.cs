using System.Text;

namespace CrupestApi.Commons.Crud;

public class InsertItem
{
    /// <summary>
    /// Null means use default value. Use <see cref="DbNullValue"/>.
    /// </summary>
    public InsertItem(string columnName, object? value)
    {
        ColumnName = columnName;
        Value = value;
    }

    public string ColumnName { get; set; }
    public object? Value { get; set; }
}

public interface IInsertClause : IClause
{
    List<InsertItem> Items { get; }
    string GenerateColumnListSql(string? dbProviderId = null);
    (string sql, ParamList parameters) GenerateValueListSql(string? dbProviderId = null);
}

public class InsertClause : IInsertClause
{
    public List<InsertItem> Items { get; } = new List<InsertItem>();

    public InsertClause(params InsertItem[] items)
    {
        Items.AddRange(items);
    }

    public InsertClause Add(params InsertItem[] items)
    {
        Items.AddRange(items);
        return this;
    }

    public InsertClause Add(string column, object? value)
    {
        return Add(new InsertItem(column, value));
    }

    public static InsertClause Create(params InsertItem[] items)
    {
        return new InsertClause(items);
    }

    public List<string> GetRelatedColumns()
    {
        return Items.Select(i => i.ColumnName).ToList();
    }

    public string GenerateColumnListSql(string? dbProviderId = null)
    {
        return string.Join(", ", Items.Where(i => i.Value is not null).Select(i => i.ColumnName));
    }

    public (string sql, ParamList parameters) GenerateValueListSql(string? dbProviderId = null)
    {
        var parameters = new ParamList();
        var sb = new StringBuilder();
        for (var i = 0; i < Items.Count; i++)
        {
            var item = Items[i];
            if (item.Value is null) continue;
            var parameterName = parameters.AddRandomNameParameter(item.Value, item.ColumnName);
            sb.Append($"@{parameterName}");
            if (i != Items.Count - 1)
                sb.Append(", ");
        }

        return (sb.ToString(), parameters);
    }
}
