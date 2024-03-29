namespace Crupest.V2ray;

public record V2rayRouting(List<V2rayRoutingRule> Rules, string DomainStrategy = "IpOnDemand")
{
    public record DomainRuleJsonObject(List<string> Domains, string OutboundTag, string Type = "field");

    public record IpRuleJsonObject(List<string> Ip, string OutboundTag, string Type = "field");

    public record V5DomainRuleJsonObject(List<V2rayRoutingRuleMatcher.V5DomainObject> Domain, string OutboundTag);

    public record V5GeoDomainRuleJsonObject(List<V2rayRoutingRuleMatcher.V5GeoDomainObject> GeoDomain, string OutboundTag);

    public record V5GeoIpRuleJsonObject(List<V2rayRoutingRuleMatcher.V5GeoIpObject> Geoip, string OutboundTag);

    public record RoutingJsonObject(string DomainStrategy, List<object> Rules);

    public record V5RouterJsonObject(string DomainStrategy, List<object> Rule);

    public V2rayRouting() : this(new List<V2rayRoutingRule>())
    {

    }

    public RoutingJsonObject ToJsonObject()
    {
        var ruleJsonObjects = new List<object>();

        foreach (var (outBoundTag, proxyRules) in V2rayRoutingRule.GroupByOutboundTag(Rules))
        {
            foreach (var (matchByKind, rules) in V2rayRoutingRule.GroupByMatchByKind(proxyRules))
            {
                ruleJsonObjects.Add(
                    matchByKind switch
                    {
                        V2rayRoutingRuleMatcher.MatchByKind.Ip => new IpRuleJsonObject(rules.Select(r => r.Matcher.ToString()).ToList(), outBoundTag),
                        V2rayRoutingRuleMatcher.MatchByKind.Domain => new DomainRuleJsonObject(rules.Select(r => r.Matcher.ToString()).ToList(), outBoundTag),
                        _ => throw new Exception("Unknown match by kind."),
                    }
                );
            }
        }

        return new RoutingJsonObject(DomainStrategy, ruleJsonObjects);
    }

    public V5RouterJsonObject V5ToJsonObject()
    {
        throw new NotImplementedException();
    }

    public static V2rayRouting FromStringList(List<string> list, string outboundTag = "proxy")
    {
        var router = new V2rayRouting();

        foreach (var line in list)
        {
            var matcher = V2rayRoutingRuleMatcher.Parse(line);
            if (matcher != null)
                router.Rules.Add(new V2rayRoutingRule(matcher, outboundTag));
        }

        return router;
    }
}

