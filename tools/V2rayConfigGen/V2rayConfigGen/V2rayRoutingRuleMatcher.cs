namespace Crupest.V2ray;

public record V2rayRoutingRuleMatcher(V2rayRoutingRuleMatcher.MatchKind Kind, string Value)
{
    public enum MatchByKind
    {
        Domain,
        Ip
    }

    public enum MatchKind
    {
        GeoIp,
        GeoSite,
        DomainPlain,
        DomainSuffix,
        DomainRegex,
        DomainFull,
    }

    public MatchByKind MatchBy
    {
        get
        {
            return Kind switch
            {
                MatchKind.GeoIp => MatchByKind.Ip,
                _ => MatchByKind.Domain
            };
        }
    }

    public static V2rayRoutingRuleMatcher? Parse(string line)
    {
        if (line.IndexOf('#') != -1)
        {
            line = line[..line.IndexOf('#')];
        }

        line = line.Trim();

        if (line.Length == 0) { return null; }

        var kind = MatchKind.DomainSuffix;

        foreach (var name in Enum.GetNames<MatchKind>()) {
            if (line.StartsWith(name)) {
                kind = Enum.Parse<MatchKind>(name);
                line = line[name.Length..];
                line = line.Trim();
                break;
            }
        }

        return new V2rayRoutingRuleMatcher(kind, line);
    }


    public override string ToString()
    {
        return Kind switch
        {
            MatchKind.GeoSite => $"geosite:{Value}",
            MatchKind.GeoIp => $"geoip:{Value}",
            MatchKind.DomainPlain => Value,
            MatchKind.DomainSuffix => $"domain:{Value}",
            MatchKind.DomainFull => $"full:{Value}",
            MatchKind.DomainRegex => $"regexp:{Value}",
            _ => throw new Exception("Unknown matcher kind."),
        };
    }
}
