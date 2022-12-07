using System.Text;
using Dapper;

namespace CrupestApi.Commons.Crud;

public class UpdateItem
{
    public UpdateItem(string columnName, object? value)
    {
        ColumnName = columnName;
        Value = value;
    }

    public string ColumnName { get; set; }
    public object? Value { get; set; }
}

// TODO: Continue...
public class UpdateClause
{
    public List<UpdateItem> Items { get; } = new List<UpdateItem>();

    public UpdateClause(IEnumerable<UpdateItem> items)
    {
        Items.AddRange(items);
    }

    public UpdateClause(params UpdateItem[] items)
    {
        Items.AddRange(items);
    }

    public UpdateClause Add(params UpdateItem[] items)
    {
        Items.AddRange(items);
        return this;
    }

    public UpdateClause Add(string column, object? value)
    {
        return Add(new UpdateItem(column, value));
    }

    public static UpdateClause Create(params UpdateItem[] items)
    {
        return new UpdateClause(items);
    }

    public List<string> GetRelatedColumns()
    {
        return Items.Select(i => i.ColumnName).ToList();
    }

    public string GenerateSql(DynamicParameters parameters)
    {
        StringBuilder result = new StringBuilder();

        foreach (var item in Items)
        {
            if (result.Length > 0)
            {
                result.Append(", ");
            }

            var parameterName = parameters.AddRandomNameParameter(item.Value);
            result.Append($"{item.ColumnName} = @{parameterName}");
        }

        return result.ToString();
    }
}
