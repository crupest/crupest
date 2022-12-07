using System.Data;
using System.Diagnostics;
using Dapper;

namespace CrupestApi.Commons.Crud;

public static class DynamicParametersExtensions
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

    public static string GenerateRandomParameterName(DynamicParameters parameters)
    {
        var parameterName = GenerateRandomKey(10);
        int retryTimes = 1;
        while (parameters.ParameterNames.Contains(parameterName))
        {
            retryTimes++;
            Debug.Assert(retryTimes <= 100);
            parameterName = GenerateRandomKey(10);
        }
        return parameterName;
    }

    public static string AddRandomNameParameter(this DynamicParameters parameters, object? value)
    {
        var parameterName = GenerateRandomParameterName(parameters);
        parameters.Add(parameterName, value);
        return parameterName;
    }
}
