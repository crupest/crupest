using System.Text.Json;
using Microsoft.Extensions.Options;

namespace CrupestApi.Commons.Crud;

/// <summary>
/// Contains all you need to do with json.
/// </summary>
public class EntityJsonHelper<TEntity> where TEntity : class
{
    private readonly TableInfo _table;
    private readonly IOptionsMonitor<JsonSerializerOptions> _jsonSerializerOptions;

    public EntityJsonHelper(TableInfoFactory tableInfoFactory, IOptionsMonitor<JsonSerializerOptions> jsonSerializerOptions)
    {
        _table = tableInfoFactory.Get(typeof(TEntity));
        _jsonSerializerOptions = jsonSerializerOptions;
    }

    public Dictionary<string, object?> ConvertEntityToDictionary(TEntity entity, bool includeNonColumnProperties = false)
    {
        var result = new Dictionary<string, object?>();

        foreach (var column in _table.PropertyColumns)
        {
            var value = column.PropertyInfo!.GetValue(entity);
            var realValue = column.ColumnType.ConvertToDatabase(value);
            result[column.ColumnName] = realValue;
        }

        if (includeNonColumnProperties)
        {
            foreach (var propertyInfo in _table.NonColumnProperties)
            {
                var value = propertyInfo.GetValue(entity);
                result[propertyInfo.Name] = value;
            }
        }

        return result;
    }

    public string ConvertEntityToJson(TEntity entity, bool includeNonColumnProperties = false)
    {
        var dictionary = ConvertEntityToDictionary(entity, includeNonColumnProperties);
        return JsonSerializer.Serialize(dictionary, _jsonSerializerOptions.CurrentValue);
    }

    private static Type MapJsonValueKindToType(JsonElement jsonElement, out object? value)
    {
        switch (jsonElement.ValueKind)
        {
            case JsonValueKind.String:
                {
                    value = jsonElement.GetString()!;
                    return typeof(string);
                }
            case JsonValueKind.Number:
                {
                    value = jsonElement.GetDouble();
                    return typeof(double);
                }
            case JsonValueKind.True:
            case JsonValueKind.False:
                {
                    value = jsonElement.GetBoolean();
                    return typeof(bool);
                }
            case JsonValueKind.Null:
                {
                    value = null;
                    return typeof(object);
                }
            default:
                throw new UserException("Unsupported json value type.");
        }
    }

    public TEntity ConvertJsonToEntityForInsert(JsonElement jsonElement)
    {
        if (jsonElement.ValueKind is not JsonValueKind.Object)
            throw new ArgumentException("The jsonElement must be an object.");

        var result = Activator.CreateInstance<TEntity>();
        foreach (var column in _table.PropertyColumns)
        {
            if (jsonElement.TryGetProperty(column.ColumnName, out var jsonValue))
            {
                if (column.IsGenerated)
                {
                    throw new UserException($"Property {column.ColumnName} is auto generated, you cannot set it.");
                }

                var valueType = MapJsonValueKindToType(jsonValue, out var value);
                if (!valueType.IsAssignableTo(column.ColumnType.DatabaseClrType))
                {
                    throw new UserException($"Property {column.ColumnName} is of wrong type.");
                }

                var realValue = column.ColumnType.ConvertFromDatabase(value);
                column.PropertyInfo!.SetValue(result, realValue);
            }
            else
            {
                if (!column.CanBeGenerated)
                {
                    throw new UserException($"Property {column.ColumnName} is not auto generated, you must set it.");
                }
            }
        }

        return result;
    }

    public TEntity ConvertJsonToEntityForInsert(string json)
    {
        var jsonElement = JsonSerializer.Deserialize<JsonElement>(json, _jsonSerializerOptions.CurrentValue);
        return ConvertJsonToEntityForInsert(jsonElement!);
    }

    public TEntity ConvertJsonToEntityForUpdate(JsonElement jsonElement, out UpdateBehavior updateBehavior)
    {
        if (jsonElement.ValueKind is not JsonValueKind.Object)
            throw new UserException("The jsonElement must be an object.");

        updateBehavior = UpdateBehavior.None;

        if (jsonElement.TryGetProperty("$saveNull", out var saveNullValue))
        {
            if (saveNullValue.ValueKind is JsonValueKind.True)
            {
                updateBehavior |= UpdateBehavior.SaveNull;
            }
            else if (saveNullValue.ValueKind is JsonValueKind.False)
            {

            }
            else
            {
                throw new UserException("The $saveNull must be a boolean.");
            }
        }

        var result = Activator.CreateInstance<TEntity>();
        foreach (var column in _table.PropertyColumns)
        {
            if (jsonElement.TryGetProperty(column.ColumnName, out var jsonValue))
            {
                if (column.IsGenerated)
                {
                    throw new UserException($"Property {column.ColumnName} is auto generated, you cannot set it.");
                }

                if (column.IsNoUpdate)
                {
                    throw new UserException($"Property {column.ColumnName} is not updatable, you cannot set it.");
                }

                var valueType = MapJsonValueKindToType(jsonValue, out var value);
                if (!valueType.IsAssignableTo(column.ColumnType.DatabaseClrType))
                {
                    throw new UserException($"Property {column.ColumnName} is of wrong type.");
                }

                var realValue = column.ColumnType.ConvertFromDatabase(value);
                column.PropertyInfo!.SetValue(result, realValue);
            }
        }

        return result;
    }

    public TEntity ConvertJsonToEntityForUpdate(string json, out UpdateBehavior updateBehavior)
    {
        var jsonElement = JsonSerializer.Deserialize<JsonElement>(json, _jsonSerializerOptions.CurrentValue);
        return ConvertJsonToEntityForUpdate(jsonElement!, out updateBehavior);
    }
}
