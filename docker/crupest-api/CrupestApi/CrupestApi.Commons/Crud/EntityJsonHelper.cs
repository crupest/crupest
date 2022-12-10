using System.Text.Json;

namespace CrupestApi.Commons.Crud;

public class EntityJsonHelper
{
    private readonly TableInfo _table;

    public EntityJsonHelper(TableInfo table)
    {
        _table = table;
    }

    public virtual JsonDocument ConvertEntityToJson(object? entity)
    {
        if (entity is null) return JsonSerializer.SerializeToDocument<object?>(null);

        var result = new Dictionary<string, object?>();

        foreach (var column in _table.ColumnInfos)
        {
            if (column.PropertyInfo is not null)
            {
                result.Add(column.ColumnName, column.PropertyInfo.GetValue(entity));
            }
        }

        return JsonSerializer.SerializeToDocument(result);
    }

    public virtual object? ConvertJsonToEntity(JsonDocument? json)
    {
        // TODO: Implement this.
        throw new NotImplementedException();
    }
}
