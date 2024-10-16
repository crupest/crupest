namespace Crupest.SecretTool;

public enum HostMatchKind
{
    DomainFull,
    DomainSuffix,
    DomainKeyword,
    DomainRegex,
    Ip,
    GeoSite,
    GeoIp,
}

public static class HostMatchKindExtensions
{
    public static bool IsDomain(this HostMatchKind kind)
    {
        return kind.IsNonRegexDomain() || kind == HostMatchKind.DomainRegex;
    }

    public static bool IsNonRegexDomain(this HostMatchKind kind)
    {
        return kind is HostMatchKind.DomainFull or HostMatchKind.DomainSuffix or HostMatchKind.DomainKeyword;
    }


    public static List<HostMatchKind> DomainMatchKinds { get; } = [HostMatchKind.DomainFull, HostMatchKind.DomainSuffix, HostMatchKind.DomainKeyword, HostMatchKind.DomainRegex];

    public static List<HostMatchKind> NonRegexDomainMatchKinds { get; } = [HostMatchKind.DomainFull, HostMatchKind.DomainSuffix, HostMatchKind.DomainKeyword];
}

public record HostMatchConfigItem(HostMatchKind Kind, string MatchString, List<string> Values);

public class HostMatchConfig(string configString, List<HostMatchKind> allowedMatchKinds, int minComponentCount = -1, int maxComponentCount = -1)
{
    private static List<HostMatchConfigItem> Parse(string configString, List<HostMatchKind> allowedMatchKinds, int minComponentCount = -1, int maxComponentCount = -1)
    {
        var items = new ListConfig(configString).Config;
        var result = new List<HostMatchConfigItem>();

        foreach (var item in items)
        {
            var lineNumber = item.LineNumber;
            var line = item.Value;
            var hasExplicitMatchKind = false;
            var segments = line.Split(' ', StringSplitOptions.TrimEntries | StringSplitOptions.RemoveEmptyEntries).ToList();

            foreach (var matchKind in Enum.GetValues<HostMatchKind>())
            {
                var matchKindName = Enum.GetName(matchKind) ?? throw new Exception("No such match kind.");
                if (segments[0] == matchKindName)
                {
                    hasExplicitMatchKind = true;

                    if (segments.Count < 2)
                    {
                        throw new FormatException($"Explicit match item needs a value in line {lineNumber}.");
                    }
                    if (allowedMatchKinds.Contains(matchKind))
                    {
                        if (matchKind.IsNonRegexDomain() && Uri.CheckHostName(matchKindName) != UriHostNameType.Dns)
                        {
                            throw new FormatException($"Invalid domain format in line {lineNumber}.");
                        }

                        var components = segments[2..].ToList();
                        if (minComponentCount > 0 && components.Count < minComponentCount)
                        {
                            throw new FormatException($"Too few components in line {lineNumber}, at least {minComponentCount} required.");
                        }
                        if (maxComponentCount >= 0 && components.Count > maxComponentCount)
                        {
                            throw new FormatException($"Too many components in line {lineNumber}, only {maxComponentCount} allowed.");
                        }
                        result.Add(new HostMatchConfigItem(matchKind, segments[1], components));
                    }
                    else
                    {
                        throw new FormatException($"Match kind {matchKindName} is not allowed at line {lineNumber}.");
                    }
                }
            }

            if (!hasExplicitMatchKind)
            {
                if (minComponentCount > 0 && segments.Count - 1 < minComponentCount)
                {
                    throw new FormatException($"Too few components in line {lineNumber}, at least {minComponentCount} required.");
                }
                if (maxComponentCount >= 0 && segments.Count - 1 > maxComponentCount)
                {
                    throw new FormatException($"Too many components in line {lineNumber}, only {maxComponentCount} allowed.");
                }
                result.Add(new HostMatchConfigItem(HostMatchKind.DomainSuffix, segments[0], segments.Count == 1 ? [] : segments[1..]));
            }
        }
        return result;
    }

    public string ConfigString { get; } = configString;
    public List<HostMatchKind> AllowedMatchKinds { get; } = allowedMatchKinds;
    public int MinComponentCount { get; } = minComponentCount;
    public int MaxComponentCount { get; } = maxComponentCount;
    public List<HostMatchConfigItem> Items { get; } = Parse(configString, allowedMatchKinds, minComponentCount, maxComponentCount);
}

public class HostMatchConfigFile
{
    public HostMatchConfigFile(string path, List<HostMatchKind> allowedMatchKinds, int minComponentCount = -1, int maxComponentCount = -1)
    {
        Path = path;
        FileContent = File.ReadAllText(path);
        Config = new HostMatchConfig(FileContent, allowedMatchKinds, minComponentCount, maxComponentCount); ;
    }

    public string Path { get; }
    public string FileContent { get; }
    public HostMatchConfig Config { get; }
}

public class ProxyFile(string path) :
    HostMatchConfigFile(path, [.. Enum.GetValues<HostMatchKind>()], maxComponentCount: 0)
{
}
