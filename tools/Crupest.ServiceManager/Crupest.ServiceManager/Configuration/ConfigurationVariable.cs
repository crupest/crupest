namespace Crupest.ServiceManager.Configuration;

public class ConfigurationVariable
{
    public enum ValueKind
    {
        Text,
        Integer
    }

    public static Type GetTypeOfValueKind(ValueKind kind) =>
        kind switch
        {
            ValueKind.Text => typeof(string),
            ValueKind.Integer => typeof(int),
            _ => throw new ArgumentException("Unknown value kind.")
        };

    public static object? TryConvert(ValueKind kind, object value)
    {
        ArgumentNullException.ThrowIfNull(value);

        if (kind == ValueKind.Text)
        {
            return value switch
            {
                string => value,
                int i => i.ToString(),
                _ => throw new ArgumentException("Invalid value type.")
            };

        }
        else if (kind == ValueKind.Integer)
        {
            return value switch
            {
                string s => int.TryParse(s, out var i) ? i : null,
                int => value,
                _ => throw new ArgumentException("Invalid value type.")
            };
        }
        throw new ArgumentException("Invalid value type.");
    }

    private object? _value;

    public ConfigurationVariable(string key, ValueKind kind, string? name = null)
    {
        Key = key;
        Name = name ?? key;
        Kind = kind;
    }

    public string Key { get; set; }
    public string Name { get; set; }
    public string Description { get; set; } = "";
    public ValueKind Kind { get; set; }


    public T? GetValue<T>()
    {
        if (GetTypeOfValueKind(Kind) != typeof(T))
        {
            throw new Exception("Not correct type of value kind.");
        }
        return (T?)_value;
    }

    public void SetValue(object? value, bool autoConvert = true)
    {
        if (value is null)
        {
            _value = null;
            return;
        }

        if (Kind == ValueKind.Text)
        {
            if (value is string)
            {
                _value = value;
            }
            else
            {
                if (autoConvert)
                {
                    _value = value.ToString();
                }
                else
                {
                    throw new ArgumentException("Value is not a string.");
                }
            }
        }
        else if (Kind == ValueKind.Integer)
        {
            if (value is int || value is int?)
            {
                _value = value;
            }
            else
            {
                if (autoConvert)
                {
                    if (value is string s)
                    {
                        if (!int.TryParse(s, out var i))
                        {
                            throw new ArgumentException("Value is not a integer string.");
                        }
                    }
                    else
                    {

                    }
                }
            }
        }
    }
}

