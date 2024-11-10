using System.Globalization;
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

    public EntityJsonHelper(ITableInfoFactory tableInfoFactory, IOptionsMonitor<JsonSerializerOptions> jsonSerializerOptions)
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

    private object? ConvertJsonValue(JsonElement? optionalJsonElement, Type type, string propertyName)
    {
        if (optionalJsonElement is null)
        {
            return null;
        }

        var jsonElement = optionalJsonElement.Value;

        if (jsonElement.ValueKind is JsonValueKind.Null or JsonValueKind.Undefined)
        {
            return null;
        }

        if (jsonElement.ValueKind is JsonValueKind.String)
        {
            if (type != typeof(string))
            {
                throw new UserException($"Property {propertyName} must be a string.");
            }
            return jsonElement.GetString()!;
        }

        if (jsonElement.ValueKind is JsonValueKind.True or JsonValueKind.False)
        {
            if (type != typeof(bool))
            {
                throw new UserException($"Property {propertyName} must be a boolean.");
            }
            return jsonElement.GetBoolean();
        }

        if (jsonElement.ValueKind is JsonValueKind.Number)
        {
            try
            {
                return Convert.ChangeType(jsonElement.GetRawText(), type, CultureInfo.InvariantCulture);
            }
            catch (Exception)
            {
                throw new UserException($"Property {propertyName} must be a valid number.");
            }
        }

        throw new UserException($"Property {propertyName} is of wrong type.");
    }

    public Dictionary<string, JsonElement> ConvertJsonObjectToDictionary(JsonElement jsonElement)
    {
        var result = new Dictionary<string, JsonElement>();

        foreach (var property in jsonElement.EnumerateObject())
        {
            result[property.Name.ToLower()] = property.Value;
        }

        return result;
    }

    public TEntity ConvertJsonToEntityForInsert(JsonElement jsonElement)
    {
        if (jsonElement.ValueKind is not JsonValueKind.Object)
            throw new ArgumentException("The jsonElement must be an object.");

        var result = Activator.CreateInstance<TEntity>();

        Dictionary<string, JsonElement> jsonProperties = ConvertJsonObjectToDictionary(jsonElement);

        foreach (var column in _table.PropertyColumns)
        {
            var jsonPropertyValue = jsonProperties.GetValueOrDefault(column.ColumnName.ToLower());
            var value = ConvertJsonValue(jsonPropertyValue, column.ColumnType.DatabaseClrType, column.ColumnName);
            if (column.IsOnlyGenerated && value is not null)
            {
                throw new UserException($"Property {column.ColumnName} is auto generated, you cannot set it.");
            }
            if (!column.CanBeGenerated && value is null && column.IsNotNull)
            {
                throw new UserException($"Property {column.ColumnName} can NOT be generated, you must set it.");
            }
            var realValue = column.ColumnType.ConvertFromDatabase(value);
            column.PropertyInfo!.SetValue(result, realValue);
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

        Dictionary<string, JsonElement> jsonProperties = ConvertJsonObjectToDictionary(jsonElement);

        bool saveNull = false;
        if (jsonProperties.TryGetValue("$saveNull".ToLower(), out var saveNullValue))
        {
            if (saveNullValue.ValueKind is JsonValueKind.True)
            {
                updateBehavior |= UpdateBehavior.SaveNull;
                saveNull = true;
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
            if (jsonProperties.TryGetValue(column.ColumnName.ToLower(), out var jsonPropertyValue))
            {
                if (jsonPropertyValue.ValueKind is JsonValueKind.Null or JsonValueKind.Undefined)
                {
                    if ((column.IsOnlyGenerated || column.IsNoUpdate) && saveNull)
                    {
                        throw new UserException($"Property {column.ColumnName} is auto generated or not updatable, you cannot set it.");
                    }

                    column.PropertyInfo!.SetValue(result, null);
                }
                else
                {
                    if (column.IsOnlyGenerated || column.IsNoUpdate)
                    {
                        throw new UserException($"Property {column.ColumnName} is auto generated or not updatable, you cannot set it.");
                    }

                    var value = ConvertJsonValue(jsonPropertyValue, column.ColumnType.DatabaseClrType, column.ColumnName);
                    var realValue = column.ColumnType.ConvertFromDatabase(value);
                    column.PropertyInfo!.SetValue(result, realValue);
                }
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
