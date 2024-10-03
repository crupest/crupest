namespace Crupest.SecretTool;

public record RoutingRule(HostMatchKind MatchKind, string MatchString, string OutboundTag) : IV4ConfigObject
{
    public string ToolConfigString => MatchKind switch
    {
        HostMatchKind.DomainFull => $"full:{MatchString}",
        HostMatchKind.DomainSuffix => $"domain:{MatchString}",
        HostMatchKind.DomainKeyword => MatchString,
        HostMatchKind.DomainRegex => $"regexp:{MatchString}",
        HostMatchKind.Ip => MatchString,
        HostMatchKind.GeoSite => $"geosite:{MatchString}",
        HostMatchKind.GeoIp => $"geoip:{MatchString}",
        _ => throw new ArgumentException("Invalid matcher kind.")
    };

    public static Dictionary<string, List<RoutingRule>> GroupByOutboundTag(List<RoutingRule> rules)
        => rules.GroupBy(r => r.OutboundTag).Select(g => (g.Key, g.ToList())).ToDictionary();

    public static Dictionary<HostMatchKind, List<RoutingRule>> GroupByMatchKind(List<RoutingRule> rules)
        => rules.GroupBy(r => r.MatchKind).Select(g => (g.Key, g.ToList())).ToDictionary();

    public static List<List<RoutingRule>> GroupByOutboundTagAndMatcherKind(List<RoutingRule> rules)
        => GroupByOutboundTag(rules).Values.SelectMany((groupByTag) => GroupByMatchKind(groupByTag).Values).ToList();

    public static V4ConfigJsonObjects.RoutingRule ListToJsonObject(List<RoutingRule> rules)
    {
        if (rules.Count == 0)
        {
            throw new ArgumentException("Rule list is empty.");
        }

        var matchKind = rules[0].MatchKind;
        var outboundTag = rules[0].OutboundTag;

        if (rules.Any(r => r.OutboundTag != outboundTag) || rules.Any(r => r.MatchKind != matchKind))
        {
            throw new ArgumentException("Rules must have the same matcher kind and outbound tag.");
        }

        List<string> toolConfigList = rules.Select(r => r.ToolConfigString).ToList();

        return new V4ConfigJsonObjects.RoutingRule(OutboundTag: outboundTag,
            Ip: (matchKind is HostMatchKind.Ip or HostMatchKind.GeoIp) ? toolConfigList : null,
            Domains: (matchKind.IsDomain() || matchKind == HostMatchKind.GeoSite) ? toolConfigList : null
        );
    }

    public RoutingRule CloneGeositeWithCnAttribute(string outboundTag)
    {
        if (MatchKind is not HostMatchKind.GeoSite)
        {
            throw new ArgumentException("Matcher kind must be GeoSite.");
        }

        return new RoutingRule(HostMatchKind.GeoSite, $"{MatchString}@cn", outboundTag);
    }

    public V4ConfigJsonObjects.RoutingRule ToJsonObjectV4() => ListToJsonObject([this]);

    object IV4ConfigObject.ToJsonObjectV4() => ToJsonObjectV4();
}

public record Routing(List<RoutingRule> Rules, bool DirectGeositeCn = true, string DomainStrategy = "IpOnDemand") : IV4ConfigObject
{
    public List<RoutingRule> CreateGeositeCnDirectRules()
    {
        return Rules.Where(r => r.MatchKind is HostMatchKind.GeoSite)
            .Select(r => r.CloneGeositeWithCnAttribute("direct")).ToList();
    }

    public V4ConfigJsonObjects.Routing ToJsonObjectV4(bool directGeositeCn = true)
    {
        List<V4ConfigJsonObjects.RoutingRule> ruleJsonObjects = [];

        if (directGeositeCn)
        {
            ruleJsonObjects.Add(RoutingRule.ListToJsonObject(CreateGeositeCnDirectRules()));
        }

        ruleJsonObjects.AddRange(RoutingRule.GroupByOutboundTagAndMatcherKind(Rules).Select(RoutingRule.ListToJsonObject));

        return new V4ConfigJsonObjects.Routing(ruleJsonObjects);
    }

    object IV4ConfigObject.ToJsonObjectV4() => ToJsonObjectV4();

    public static Routing FromProxyFile(ProxyFile proxyFile, string outboundTag, bool directGeositeCn)
    {

        return new Routing(
            proxyFile.Config.Items.Select(
                i => new RoutingRule(i.Kind, i.MatchString, outboundTag)).ToList(),
            directGeositeCn
        );
    }
}
