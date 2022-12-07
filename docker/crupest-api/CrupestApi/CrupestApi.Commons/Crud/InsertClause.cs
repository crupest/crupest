using System.Text;
using Dapper;

namespace CrupestApi.Commons.Crud;

public class InsertItem
{
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
    (string sql, DynamicParameters parameters) GenerateValueListSql(string? dbProviderId = null);
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
        return string.Join(", ", Items.Select(i => i.ColumnName));
    }

    public (string sql, DynamicParameters parameters) GenerateValueListSql(string? dbProviderId = null)
    {
        var parameters = new DynamicParameters();
        var sb = new StringBuilder();
        for (var i = 0; i < Items.Count; i++)
        {
            var item = Items[i];
            var parameterName = parameters.AddRandomNameParameter(item.Value);
            sb.Append($"@{parameterName}");
            if (i != Items.Count - 1)
                sb.Append(", ");
        }

        return (sb.ToString(), parameters);
    }
}
