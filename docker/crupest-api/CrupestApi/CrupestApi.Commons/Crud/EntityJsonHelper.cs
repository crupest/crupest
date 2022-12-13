using System.Diagnostics;
using System.Text.Json;
using System.Text.Json.Serialization;
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

    public virtual Dictionary<string, object?> ConvertEntityToDictionary(object? entity)
    {
        Debug.Assert(entity is null || entity is TEntity);

        var result = new Dictionary<string, object?>();

        foreach (var column in _table.PropertyColumns)
        {
            var propertyInfo = column.PropertyInfo;
            var value = propertyInfo!.GetValue(entity);
            result[column.ColumnName] = value;
        }

        return result;
    }

    public virtual string ConvertEntityToJson(object? entity)
    {
        Debug.Assert(entity is null || entity is TEntity);

        var dictionary = ConvertEntityToDictionary(entity);
        return JsonSerializer.Serialize(dictionary, _jsonSerializerOptions);
    }

    public virtual TEntity ConvertDictionaryToEntityForInsert(IReadOnlyDictionary<string, object?> dictionary)
    {
        var result = Activator.CreateInstance<TEntity>()!;

        foreach (var column in _table.PropertyColumns)
        {
            var propertyInfo = column.PropertyInfo!;
            var value = dictionary.GetValueOrDefault(column.ColumnName);
            if (column.IsGenerated)
            {
                if (value is not null)
                {
                    throw new UserException($"{propertyInfo.Name} is auto generated. Don't specify it.");
                }
            }

            if (value is null)
            {
                if (column.IsNotNull && !column.CanBeGenerated)
                {
                    throw new UserException($"{propertyInfo.Name} can't be null.");
                }
                propertyInfo.SetValue(result, null);
            }
            else
            {
                // Check type
                var columnType = column.ColumnType;
                if (columnType.ClrType.IsAssignableFrom(value.GetType()))
                    propertyInfo.SetValue(result, value);
                else
                    throw new UserException($"{propertyInfo.Name} is of wrong type.");
            }
        }

        return result;
    }
}
