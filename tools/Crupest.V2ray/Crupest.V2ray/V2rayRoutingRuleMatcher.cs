namespace Crupest.V2ray;

public record V2rayRoutingRuleMatcher(V2rayRoutingRuleMatcher.MatchKind Kind, string Value)
{
    public enum MatchByKind
    {
        Domain,
        Ip
    }

    public enum V5MatchByKind
    {
        Domain,
        // Ip,
        GeoIp,
        GeoSite,
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

    public V5MatchByKind V5MatchBy
    {
        get
        {
            return Kind switch
            {
                MatchKind.GeoIp => V5MatchByKind.GeoIp,
                MatchKind.GeoSite => V5MatchByKind.GeoSite,
                _ => V5MatchByKind.Domain,
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

        foreach (var name in Enum.GetNames<MatchKind>())
        {
            if (line.StartsWith(name))
            {
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

    public enum V5DomainObjectType
    {
        Plain,
        Regex,
        RootDomain,
        Full,
    }

    public record V5DomainObject(V5DomainObjectType Type, string Value);

    public V5DomainObject ToDomainObject()
    {
        return new V5DomainObject(Kind switch
        {
            MatchKind.DomainFull => V5DomainObjectType.Full,
            MatchKind.DomainPlain => V5DomainObjectType.Plain,
            MatchKind.DomainRegex => V5DomainObjectType.Regex,
            MatchKind.DomainSuffix => V5DomainObjectType.RootDomain,
            _ => throw new Exception("Not a domain matcher."),
        }, Value);
    }

    public record V5GeoDomainObject(string Code);

    public V5GeoDomainObject ToGeoDomainObject()
    {
        if (Kind != MatchKind.GeoSite)
        {
            throw new Exception("Not a geo-domain matcher.");
        }

        return new V5GeoDomainObject(Value);
    }

    public record V5GeoIpObject(string Code);

    public V5GeoIpObject ToGeoIpObject()
    {
        if (Kind != MatchKind.GeoIp)
        {
            throw new Exception("Not a geo-ip matcher.");
        }

        return new V5GeoIpObject(Value);
    }
}

