using System.Diagnostics;
using System.Text.Json;
using System.Text.Json.Serialization;
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

    public virtual Dictionary<string, object?> ConvertEntityToDictionary(TEntity entity, bool includeNonColumnProperties = false)
    {
        var result = new Dictionary<string, object?>();

        foreach (var propertyInfo in _table.ColumnProperties)
        {
            var value = propertyInfo.GetValue(entity);
            result[propertyInfo.Name] = value;
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

    public virtual string ConvertEntityToJson(TEntity entity, bool includeNonColumnProperties = false)
    {
        var dictionary = ConvertEntityToDictionary(entity, includeNonColumnProperties);
        return JsonSerializer.Serialize(dictionary, _jsonSerializerOptions.CurrentValue);
    }

    public virtual IInsertClause ConvertJsonElementToInsertClauses(JsonElement rootElement)
    {
        var insertClause = InsertClause.Create();

        if (rootElement.ValueKind != JsonValueKind.Object)
        {
            throw new UserException("The root element must be an object.");
        }

        foreach (var column in _table.PropertyColumns)
        {
            object? value = null;
            if (rootElement.TryGetProperty(column.ColumnName, out var propertyElement))
            {
                value = propertyElement.ValueKind switch
                {
                    JsonValueKind.Null or JsonValueKind.Undefined => null,
                    JsonValueKind.Number => propertyElement.GetDouble(),
                    JsonValueKind.True => true,
                    JsonValueKind.False => false,
                    JsonValueKind.String => propertyElement.GetString(),
                    _ => throw new Exception($"Bad json value of property {column.ColumnName}.")
                };
            }

            if (column.IsGenerated && value is not null)
            {
                throw new UserException($"The property {column.ColumnName} is generated. You cannot specify its value.");
            }

            if (column.IsNotNull && !column.CanBeGenerated && value is null)
            {
                throw new UserException($"The property {column.ColumnName} can't be null or generated. But you specify a null value.");
            }

            insertClause.Add(column.ColumnName, value);
        }

        return insertClause;
    }

    public IInsertClause ConvertJsonToInsertClauses(string json)
    {
        var document = JsonSerializer.Deserialize<JsonDocument>(json, _jsonSerializerOptions.CurrentValue)!;
        return ConvertJsonElementToInsertClauses(document.RootElement);
    }

    public IUpdateClause ConvertJsonElementToUpdateClause(JsonDocument json)
    {
        var updateClause = UpdateClause.Create();

        if (json.RootElement.ValueKind != JsonValueKind.Object)
        {
            throw new UserException("The root element must be an object.");
        }

        bool saveNull = false;

        if (json.RootElement.TryGetProperty("$saveNull", out var propertyElement))
        {
            if (propertyElement.ValueKind is not JsonValueKind.True or JsonValueKind.False)
            {
                throw new UserException("$saveNull can only be true or false.");
            }

            if (propertyElement.ValueKind is JsonValueKind.True)
            {
                saveNull = true;
            }
        }


        foreach (var column in _table.PropertyColumns)
        {
            object? value = null;

            if (json.RootElement.TryGetProperty(column.ColumnName, out propertyElement))
            {
                value = propertyElement.ValueKind switch
                {
                    JsonValueKind.Null or JsonValueKind.Undefined => null,
                    JsonValueKind.Number => propertyElement.GetDouble(),
                    JsonValueKind.True => true,
                    JsonValueKind.False => false,
                    JsonValueKind.String => propertyElement.GetString(),
                    _ => throw new Exception($"Bad json value of property {column.ColumnName}.")
                };

                if (column.IsNoUpdate && (value is not null || saveNull))
                {
                    throw new UserException($"The property {column.ColumnName} is not updatable. You cannot specify its value.");
                }
            }

            if (value is null && !saveNull)
            {
                continue;
            }

            updateClause.Add(column.ColumnName, value ?? DbNullValue.Instance);
        }

        return updateClause;
    }

    public IUpdateClause ConvertJsonToUpdateClause(string json)
    {
        var document = JsonSerializer.Deserialize<JsonDocument>(json, _jsonSerializerOptions.CurrentValue)!;
        return ConvertJsonElementToUpdateClause(document);
    }
}
