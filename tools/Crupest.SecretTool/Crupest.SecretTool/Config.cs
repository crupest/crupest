namespace Crupest.SecretTool;

public record ConfigItem(string Value, int LineNumber);

public class DictionaryConfig(string configString, List<string>? requiredKeys = null)
{
    private static Dictionary<string, ConfigItem> Parse(string configString, List<string>? requiredKeys = null)
    {
        var config = new Dictionary<string, ConfigItem>();
        var lines = configString.Split('\n');
        int lineNumber = 1;

        foreach (var line in lines)
        {
            var l = line;
            var beginOfComment = l.IndexOf('#');
            if (beginOfComment >= 0)
            {
                l = line[..beginOfComment];
            }
            l = l.Trim();
            if (!string.IsNullOrEmpty(l))
            {
                var equalIndex = l.IndexOf('=');
                if (equalIndex == -1)
                {
                    throw new FormatException($"No '=' found in line {lineNumber}.");
                }

                config.Add(l[..equalIndex].Trim(), new ConfigItem(l[(equalIndex + 1)..].Trim(), lineNumber));
            }

            lineNumber++;
        }

        if (requiredKeys is not null)
        {
            foreach (var key in requiredKeys)
            {
                if (!config.ContainsKey(key))
                {
                    throw new FormatException($"Required key '{key}' not found in config.");
                }
            }
        }

        return config;
    }

    public string ConfigString { get; } = configString;
    public List<string>? RequiredKeys { get; } = requiredKeys;
    public Dictionary<string, ConfigItem> Config { get; } = Parse(configString);
    public ConfigItem GetItemCaseInsensitive(string key)
    {
        foreach (var (originalKey, value) in Config)
        {
            if (string.Equals(originalKey, key, StringComparison.OrdinalIgnoreCase))
            {
                return value;
            }
        }
        throw new KeyNotFoundException($"Key '{key}' not found in config case-insensitively.");
    }
}

public class ListConfig(string configString)
{
    private static List<ConfigItem> Parse(string configString)
    {
        var config = new List<ConfigItem>();
        var lines = configString.Split('\n');
        int lineNumber = 1;

        foreach (var line in lines)
        {
            var l = line;
            var beginOfComment = l.IndexOf('#');
            if (beginOfComment >= 0)
            {
                l = line[..beginOfComment];
            }
            l = l.Trim();
            if (!string.IsNullOrEmpty(l))
            {
                config.Add(new ConfigItem(l, lineNumber));
            }
            lineNumber++;
        }

        return config;
    }

    public string ConfigString { get; } = configString;
    public List<ConfigItem> Config { get; } = Parse(configString);
}
