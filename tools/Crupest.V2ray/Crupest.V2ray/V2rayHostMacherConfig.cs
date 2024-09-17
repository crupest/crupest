namespace Crupest.V2ray;

public enum V2rayHostMatcherKind
{
    DomainFull,
    DomainSuffix,
    DomainKeyword,
    DomainRegex,
    Ip,
    GeoSite,
    GeoIp,
}

public record V2rayHostMatcherItem(V2rayHostMatcherKind Kind, string Matcher, List<string> Values);

public class V2rayHostMatcherConfig(string configString, List<V2rayHostMatcherKind> allowedMatchers, int minComponentCount = -1, int maxComponentCount = -1)
{
    static bool IsDomainMatcher(V2rayHostMatcherKind kind) => kind switch
    {
        V2rayHostMatcherKind.DomainFull => true,
        V2rayHostMatcherKind.DomainSuffix => true,
        V2rayHostMatcherKind.DomainKeyword => true,
        V2rayHostMatcherKind.DomainRegex => true,
        _ => false,
    };

    private static List<V2rayHostMatcherItem> Parse(string configString, List<V2rayHostMatcherKind> allowedMatchers, int minComponentCount = -1, int maxComponentCount = -1)
    {
        var items = new ListConfig(configString).Config;
        var result = new List<V2rayHostMatcherItem>();

        foreach (var item in items)
        {
            var lineNumber = item.LineNumber;
            var line = item.Value;
            var hasExplicitMatcher = false;
            var segments = line.Split(' ', StringSplitOptions.TrimEntries | StringSplitOptions.RemoveEmptyEntries).ToList();

            foreach (var matcher in Enum.GetValues<V2rayHostMatcherKind>())
            {
                var matcherName = Enum.GetName(matcher) ?? throw new Exception("No such matcher.");
                hasExplicitMatcher = true;
                if (segments[0] == matcherName)
                {
                    if (segments.Count < 2)
                    {
                        throw new FormatException($"Explicit matcher needs a value in line {lineNumber}.");
                    }
                    if (allowedMatchers.Contains(matcher))
                    {
                        if (IsDomainMatcher(matcher) && Uri.CheckHostName(matcherName) != UriHostNameType.Dns)
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
                        result.Add(new V2rayHostMatcherItem(matcher, segments[1], components));
                    }
                    else
                    {
                        throw new FormatException($"Matcher {matcherName} is not allowed at line {lineNumber}.");
                    }
                }
            }

            if (!hasExplicitMatcher)
            {
                if (minComponentCount > 0 && segments.Count - 1 < minComponentCount)
                {
                    throw new FormatException($"Too few components in line {lineNumber}, at least {minComponentCount} required.");
                }
                if (maxComponentCount >= 0 && segments.Count - 1 > maxComponentCount)
                {
                    throw new FormatException($"Too many components in line {lineNumber}, only {maxComponentCount} allowed.");
                }
                result.Add(new V2rayHostMatcherItem(V2rayHostMatcherKind.DomainSuffix, segments[0], segments.Count == 1 ? [] : segments[1..]));
            }
        }
        return result;
    }

    public string ConfigString { get; } = configString;
    public List<V2rayHostMatcherKind> AllowedMatchers { get; } = allowedMatchers;
    public int MinComponentCount { get; } = minComponentCount;
    public int MaxComponentCount { get; } = maxComponentCount;
    public List<V2rayHostMatcherItem> Items { get; } = Parse(configString, allowedMatchers, minComponentCount, maxComponentCount);
}
