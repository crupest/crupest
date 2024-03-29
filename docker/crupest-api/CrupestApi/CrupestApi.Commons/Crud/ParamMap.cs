using System.Data;
using System.Diagnostics;

namespace CrupestApi.Commons.Crud;

/// <summary>
/// <see cref="ColumnName"/> is an optional column name related to the param. You may use it to do some column related things. Like use a more accurate conversion.
/// </summary>
/// <remarks>
/// If value is DbNullValue, it will be treated as null. 
/// </remarks>
public record ParamInfo(string Name, object? Value, string? ColumnName = null);

public class ParamList : List<ParamInfo>
{
    private static Random random = new Random();
    private const string chars = "abcdefghijklmnopqrstuvwxyz";
    public static string GenerateRandomKey(int length)
    {
        lock (random)
        {
            var result = new string(Enumerable.Repeat(chars, length)
                .Select(s => s[random.Next(s.Length)]).ToArray());
            return result;
        }
    }

    public string GenerateRandomParameterName()
    {
        var parameterName = GenerateRandomKey(10);
        int retryTimes = 1;
        while (ContainsKey(parameterName))
        {
            retryTimes++;
            Debug.Assert(retryTimes <= 100);
            parameterName = GenerateRandomKey(10);
        }
        return parameterName;
    }


    public bool ContainsKey(string name)
    {
        return this.SingleOrDefault(p => p.Name.Equals(name, StringComparison.OrdinalIgnoreCase)) is not null;
    }

    public T? Get<T>(string key)
    {
        return (T?)this.SingleOrDefault(p => p.Name.Equals(key, StringComparison.OrdinalIgnoreCase))?.Value;
    }

    public object? this[string key]
    {
        get
        {
            return this.SingleOrDefault(p => p.Name.Equals(key, StringComparison.OrdinalIgnoreCase)) ?? throw new KeyNotFoundException("Key not found.");
        }
    }

    public void Add(string name, object? value, string? columnName = null)
    {
        Add(new ParamInfo(name, value, columnName));
    }

    // Return the random name.
    public string AddRandomNameParameter(object? value, string? columnName = null)
    {
        var parameterName = GenerateRandomParameterName();
        var param = new ParamInfo(parameterName, value, columnName);
        Add(param);
        return parameterName;
    }
}
