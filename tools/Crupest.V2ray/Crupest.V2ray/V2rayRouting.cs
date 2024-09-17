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

    public static Dictionary<V2rayHostMatcherKind, List<V2rayRoutingRule>> GroupByMatcherByKind(List<V2rayRoutingRule> rules)
        => rules.GroupBy(r => r.MatcherKind).Select(g => (g.Key, g.ToList())).ToDictionary();

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

    public V2rayV4ConfigJsonObjects.RoutingRule ToJsonObjectV4() => ListToJsonObject([this]);

    object IV2rayV4ConfigObject.ToJsonObjectV4() => ToJsonObjectV4();
}

public record V2rayRouting(List<V2rayRoutingRule> Rules, string DomainStrategy = "IpOnDemand") : IV2rayV4ConfigObject
{
    public V2rayV4ConfigJsonObjects.Routing ToJsonObjectV4()
    {
        var ruleJsonObjects = new List<object>();

        var rules = V2rayRoutingRule.GroupByOutboundTag(Rules).ToList().SelectMany((groupByTag) =>
            V2rayRoutingRule.GroupByMatcherByKind(groupByTag.Value).ToList().Select((groupByMatcher) =>
                V2rayRoutingRule.ListToJsonObject(groupByMatcher.Value))
        ).ToList();

        return new V2rayV4ConfigJsonObjects.Routing(rules);
    }

    object IV2rayV4ConfigObject.ToJsonObjectV4() => ToJsonObjectV4();

    public static V2rayRouting CreateFromConfigString(string configString, string outboundTag)
    {
        var matcherConfig = new V2rayHostMatcherConfig(configString, [.. Enum.GetValues<V2rayHostMatcherKind>()], maxComponentCount: 0);
        return new V2rayRouting(matcherConfig.Items.Select(i => new V2rayRoutingRule(i.Kind, i.Matcher, outboundTag)).ToList());
    }
}
