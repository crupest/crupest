using System.Diagnostics;
using System.Text.Json;
using Microsoft.Extensions.Options;

namespace CrupestApi.Commons.Crud;

// TODO: Register this.
/// <summary>
/// Contains all you need to do with json.
/// </summary>
public class EntityJsonHelper<TEntity> where TEntity : class
{
    private readonly TableInfo _table;
    private readonly JsonSerializerOptions _jsonSerializerOptions;

    public EntityJsonHelper(TableInfoFactory tableInfoFactory)
    {
        _table = tableInfoFactory.Get(typeof(TEntity));
        _jsonSerializerOptions = new JsonSerializerOptions();
        _jsonSerializerOptions.AllowTrailingCommas = true;
        _jsonSerializerOptions.PropertyNameCaseInsensitive = true;
        _jsonSerializerOptions.PropertyNamingPolicy = JsonNamingPolicy.CamelCase;
        foreach (var type in _table.Columns.Select(c => c.ColumnType))
        {
            if (type.JsonConverter is not null)
            {
                _jsonSerializerOptions.Converters.Add(type.JsonConverter);
            }
        }
    }

    public virtual JsonDocument ConvertEntityToJson(object? entity)
    {
        Debug.Assert(entity is null || entity is TEntity);
        return JsonSerializer.SerializeToDocument<TEntity?>((TEntity?)entity, _jsonSerializerOptions);
    }

    public virtual TEntity? ConvertJsonToEntity(JsonDocument json)
    {
        var entity = json.Deserialize<TEntity>();
        if (entity is null) return null;

        foreach (var column in _table.Columns)
        {
            var propertyValue = column.PropertyInfo?.GetValue(entity);

            if ((column.IsAutoIncrement || column.IsGenerated) && propertyValue is not null)
            {
                throw new Exception("You can't specify this property because it is auto generated.");
            }
        }

        return entity;
    }
}
