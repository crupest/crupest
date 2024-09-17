namespace Crupest.V2ray;

public record V2rayRoutingRule(V2rayHostMatcherKind MatcherKind, string MatcherString, string OutboundTag) : IV2rayV4ConfigObject
{
    public string ComposedMatcherString => MatcherKind switch
    {
        V2rayHostMatcherKind.DomainFull => $"full:{MatcherString}",
        V2rayHostMatcherKind.DomainSuffix => $"domain:{MatcherString}",
        V2rayHostMatcherKind.DomainKeyword => MatcherString,
        V2rayHostMatcherKind.DomainRegex => $"regexp:{MatcherString}",
        V2rayHostMatcherKind.Ip => MatcherString,
        V2rayHostMatcherKind.GeoSite => $"geosite:{MatcherString}",
        V2rayHostMatcherKind.GeoIp => $"geoip:{MatcherString}",
        _ => throw new ArgumentException("Invalid matcher kind.")
    };

    public static Dictionary<string, List<V2rayRoutingRule>> GroupByOutboundTag(List<V2rayRoutingRule> rules)
        => rules.GroupBy(r => r.OutboundTag).Select(g => (g.Key, g.ToList())).ToDictionary();

    public static Dictionary<V2rayHostMatcherKind, List<V2rayRoutingRule>> GroupByMatcherKind(List<V2rayRoutingRule> rules)
        => rules.GroupBy(r => r.MatcherKind).Select(g => (g.Key, g.ToList())).ToDictionary();

    public static List<List<V2rayRoutingRule>> GroupByOutboundTagAndMatcherKind(List<V2rayRoutingRule> rules)
        => GroupByOutboundTag(rules).Values.SelectMany((groupByTag) => GroupByMatcherKind(groupByTag).Values).ToList();

    public static V2rayV4ConfigJsonObjects.RoutingRule ListToJsonObject(List<V2rayRoutingRule> rules)
    {
        if (rules.Count == 0)
        {
            throw new ArgumentException("Rule list is empty.");
        }

        var matcherKind = rules[0].MatcherKind;
        var outboundTag = rules[0].OutboundTag;

        if (rules.Any(r => r.OutboundTag != outboundTag) || rules.Any(r => r.MatcherKind != matcherKind))
        {
            throw new ArgumentException("Rules must have the same matcher kind and outbound tag.");
        }

        List<string> composedMatcherStringList = rules.Select(r => r.ComposedMatcherString).ToList();

        return new V2rayV4ConfigJsonObjects.RoutingRule(OutboundTag: outboundTag,
            Ip: (matcherKind is V2rayHostMatcherKind.Ip or V2rayHostMatcherKind.GeoIp) ? composedMatcherStringList : null,
            Domains: (matcherKind is V2rayHostMatcherKind.DomainFull or V2rayHostMatcherKind.DomainSuffix or V2rayHostMatcherKind.DomainKeyword or V2rayHostMatcherKind.DomainRegex or V2rayHostMatcherKind.GeoSite) ? composedMatcherStringList : null
        );
    }

    public V2rayRoutingRule CloneGeositeWithCnAttribute(string outboundTag)
    {
        if (MatcherKind is not V2rayHostMatcherKind.GeoSite)
        {
            throw new ArgumentException("Matcher kind must be GeoSite.");
        }

        return new V2rayRoutingRule(V2rayHostMatcherKind.GeoSite, $"{MatcherString}@cn", outboundTag);
    }

    public V2rayV4ConfigJsonObjects.RoutingRule ToJsonObjectV4() => ListToJsonObject([this]);

    object IV2rayV4ConfigObject.ToJsonObjectV4() => ToJsonObjectV4();
}

public record V2rayRouting(List<V2rayRoutingRule> Rules, bool DirectGeositeCn = true, string DomainStrategy = "IpOnDemand") : IV2rayV4ConfigObject
{
    public List<V2rayRoutingRule> CreateGeositeCnDirectRules()
    {
        return Rules.Where(r => r.MatcherKind is V2rayHostMatcherKind.GeoSite)
            .Select(r => r.CloneGeositeWithCnAttribute("direct")).ToList();
    }

    public V2rayV4ConfigJsonObjects.Routing ToJsonObjectV4(bool directGeositeCn = true)
    {
        List<V2rayV4ConfigJsonObjects.RoutingRule> ruleJsonObjects = [];

        if (directGeositeCn)
        {
            ruleJsonObjects.Add(V2rayRoutingRule.ListToJsonObject(CreateGeositeCnDirectRules()));
        }

        ruleJsonObjects.AddRange(V2rayRoutingRule.GroupByOutboundTagAndMatcherKind(Rules).Select(V2rayRoutingRule.ListToJsonObject));

        return new V2rayV4ConfigJsonObjects.Routing(ruleJsonObjects);
    }

    object IV2rayV4ConfigObject.ToJsonObjectV4() => ToJsonObjectV4();
}
