namespace Crupest.SecretTool;

public record RoutingRuleMatcher(HostMatchKind MatchKind, string MatchString)
{
    public RoutingRule ToRoutingRule(string OutboundTag) => new(MatchKind, MatchString, OutboundTag);
}

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

    public string ToolConfigStringSing => MatchKind.IsSupportedInSingRoute() ? MatchString : throw new ArgumentException("Unsupported matcher kind for sing.");

    public static Dictionary<string, List<RoutingRule>> GroupByOutboundTag(List<RoutingRule> rules)
        => rules.GroupBy(r => r.OutboundTag).Select(g => (g.Key, g.ToList())).ToDictionary();

    public static Dictionary<HostMatchKind, List<RoutingRule>> GroupByMatchKind(List<RoutingRule> rules)
        => rules.GroupBy(r => r.MatchKind).Select(g => (g.Key, g.ToList())).ToDictionary();

    public static List<List<RoutingRule>> GroupByOutboundTagAndMatcherKind(List<RoutingRule> rules)
        => GroupByOutboundTag(rules).Values.SelectMany((groupByTag) => GroupByMatchKind(groupByTag).Values).ToList();

    public static SingConfigJsonObjects.RouteRule ListToJsonObjectSing(List<RoutingRule> rules)
    {
        if (rules.Count == 0)
        {
            throw new ArgumentException("Rule list is empty.");
        }

        var outboundTag = rules[0].OutboundTag;

        if (rules.Any(r => !r.MatchKind.IsSupportedInSingRoute()))
        {
            throw new ArgumentException("Rules must have matcher kinds supported in sing.");
        }

        if (rules.Any(r => r.OutboundTag != outboundTag))
        {
            throw new ArgumentException("Rules must have the same outbound tag.");
        }

        return new SingConfigJsonObjects.RouteRule(Outbound: outboundTag,
            Domain: rules.Where(r => r.MatchKind == HostMatchKind.DomainFull).Select(r => r.ToolConfigStringSing).ToList(),
            DomainSuffix: rules.Where(r => r.MatchKind == HostMatchKind.DomainSuffix).Select(r => r.ToolConfigStringSing).ToList(),
            DomainKeyword: rules.Where(r => r.MatchKind == HostMatchKind.DomainKeyword).Select(r => r.ToolConfigStringSing).ToList(),
            DomainRegex: rules.Where(r => r.MatchKind == HostMatchKind.DomainRegex).Select(r => r.ToolConfigStringSing).ToList(),
            IpCidr: rules.Where(r => r.MatchKind == HostMatchKind.Ip).Select(r => r.ToolConfigStringSing).ToList()
        );
    }

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

    public RoutingRuleMatcher GetMatcher() => new(MatchKind, MatchString);

    public V4ConfigJsonObjects.RoutingRule ToJsonObjectV4() => ListToJsonObject([this]);

    object IV4ConfigObject.ToJsonObjectV4() => ToJsonObjectV4();
}

public record Routing(List<RoutingRule> Rules) : IV4ConfigObject, ISingConfigObject
{
    public List<RoutingRule> CreateGeositeCnDirectRules()
    {
        return Rules.Where(r => r.MatchKind is HostMatchKind.GeoSite)
            .Select(r => r.CloneGeositeWithCnAttribute("direct")).ToList();
    }

    public SingConfigJsonObjects.Route ToJsonObjectSing()
    {
        List<SingConfigJsonObjects.RouteRule> ruleJsonObjects = [ new SingConfigJsonObjects.RouteRule(Outbound: "dns-out", Protocol: "dns")];
        ruleJsonObjects.AddRange(RoutingRule.GroupByOutboundTag(Rules).Values.Select(RoutingRule.ListToJsonObjectSing));
        return new SingConfigJsonObjects.Route(ruleJsonObjects);
    }

    public V4ConfigJsonObjects.Routing ToJsonObjectV4(string domainStrategy = "IpOnDemand", bool directGeositeCn = true)
    {
        List<V4ConfigJsonObjects.RoutingRule> ruleJsonObjects = [];

        if (directGeositeCn)
        {
            ruleJsonObjects.Add(RoutingRule.ListToJsonObject(CreateGeositeCnDirectRules()));
        }

        ruleJsonObjects.AddRange(RoutingRule.GroupByOutboundTagAndMatcherKind(Rules).Select(RoutingRule.ListToJsonObject));

        return new V4ConfigJsonObjects.Routing(ruleJsonObjects, domainStrategy);
    }

    object IV4ConfigObject.ToJsonObjectV4() => ToJsonObjectV4();

    object ISingConfigObject.ToJsonObjectSing() => ToJsonObjectSing();

    public static Routing FromProxyFile(ProxyFile proxyFile, string outboundTag)
    {
        return new Routing(
            proxyFile.RoutingRuleMatchers.Select(m => m.ToRoutingRule(outboundTag)).ToList());
    }

    public static Routing FromProxyFileForSing(ProxyFile proxyFile, GeoSiteData geoSiteData, string outboundTag, string? directCnOutboundTag = null)
    {
        List<RoutingRule> rules = [];

        if (directCnOutboundTag is not null)
        {
            rules.AddRange(proxyFile.GetChinaRulesByGeoSite(geoSiteData).Select(m => m.ToRoutingRule(directCnOutboundTag)).ToList());
        }

        rules.AddRange(proxyFile.GetRulesFlattenGeoSite(geoSiteData).Where(m => m.MatchKind.IsSupportedInSingRoute()).Select(m => m.ToRoutingRule(outboundTag)).ToList());

        return new Routing(
            rules
        );
    }
}
