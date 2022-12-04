namespace CrupestApi.Commons;


public static class DatabaseHelper
{
    public static string GenerateUpdateColumnString(this IEnumerable<string> updateColumnList, IEnumerable<KeyValuePair<string, string>>? paramNameMap = null)
    {
        paramNameMap = paramNameMap ?? Enumerable.Empty<KeyValuePair<string, string>>();
        var paramNameDictionary = new Dictionary<string, string>(paramNameMap);

        return string.Join(", ", updateColumnList.Select(x => $"{x} = @{paramNameDictionary.GetValueOrDefault(x) ?? x}"));
    }
}