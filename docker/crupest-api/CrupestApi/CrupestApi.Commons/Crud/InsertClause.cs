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

    public InsertItem(KeyValuePair<string, object?> pair)
    {
        ColumnName = pair.Key;
        Value = pair.Value;
    }

    public string ColumnName { get; set; }
    public object? Value { get; set; }

    public static implicit operator KeyValuePair<string, object?>(InsertItem item)
    {
        return new(item.ColumnName, item.Value);
    }

    public static implicit operator InsertItem(KeyValuePair<string, object?> pair)
    {
        return new(pair);
    }
}

public class InsertClause
{
    public List<InsertItem> Items { get; } = new List<InsertItem>();

    public InsertClause(IEnumerable<InsertItem> items)
    {
        Items.AddRange(items);
    }

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

    public string GenerateColumnListSql()
    {
        return string.Join(", ", Items.Select(i => i.ColumnName));
    }

    public string GenerateValueListSql(DynamicParameters parameters)
    {
        var sb = new StringBuilder();
        for (var i = 0; i < Items.Count; i++)
        {
            var item = Items[i];
            var parameterName = parameters.AddRandomNameParameter(item.Value);
            sb.Append($"@{parameterName}");
            if (i != Items.Count - 1)
                sb.Append(", ");
        }

        return sb.ToString();
    }
}
