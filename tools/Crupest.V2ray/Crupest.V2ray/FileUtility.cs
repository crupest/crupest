using System.Text.Json;
using System.Text.RegularExpressions;

namespace Crupest.V2ray;

public static partial class FileUtility
{
    public static List<string> ReadList(string str)
    {
        return str.Split("\n", StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries).ToList();
    }

    public static Dictionary<string, string> ReadDictionary(string str, bool keyToLower = true)
    {
        var lines = str.Split("\n", StringSplitOptions.RemoveEmptyEntries | StringSplitOptions.TrimEntries);
        var result = new Dictionary<string, string>();
        for (int lineNumber = 0; lineNumber < lines.Length; lineNumber++)
        {
            var line = lines[lineNumber];
            if (!line.Contains('='))
            {
                throw new FormatException($"Line {lineNumber + 1} does not contain a '='.");
            }
            var equalIndex = line.IndexOf('=');
            var key = line[..equalIndex].Trim();
            if (keyToLower) key = key.ToLower();
            var value = line[(equalIndex + 1)..].Trim();
            result[key] = value;
        }
        return result;
    }

    public static List<string> ReadListFile(string path, bool required = true)
    {
        if (File.Exists(path))
        {
            return ReadList(File.ReadAllText(path));
        }
        else
        {
            if (required)
            {
                throw new FileNotFoundException($"File {path} is required but it does not exist.");
            }
            return new();
        }
    }

    public static Dictionary<string, string> ReadDictionaryFile(string path, bool required = true, bool keyToLower = true)
    {
        if (File.Exists(path))
        {
            return ReadDictionary(File.ReadAllText(path), keyToLower);
        }
        else
        {
            if (required)
            {
                throw new FileNotFoundException($"File {path} is required but it does not exist.");
            }
            return new();
        }
    }

    private static Regex TemplateValuePattern { get; } = CreateTemplateValuePattern();

    [GeneratedRegex(@"\$\{\s*([_a-zA-Z][_a-zA-Z0-9]*)\s*\}")]
    private static partial Regex CreateTemplateValuePattern();

    public static string TextFromTemplate(string template, Dictionary<string, string> dict)
    {
        return TemplateValuePattern.Replace(template, (match) =>
        {
            var key = match.Groups[1].Value;
            if (dict.ContainsKey(key))
            {
                return dict[key];
            }
            return match.Value;
        });
    }

    public static string JsonFormat(string json)
    {
        var options = new JsonSerializerOptions
        {
            WriteIndented = true,
            AllowTrailingCommas = true,
            ReadCommentHandling = JsonCommentHandling.Skip
        };

        return JsonSerializer.Serialize(JsonSerializer.Deserialize<JsonDocument>(json, options), options);
    }
}
