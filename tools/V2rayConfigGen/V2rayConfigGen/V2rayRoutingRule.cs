using System.Linq;

namespace Crupest.V2ray;

public record V2rayRoutingRule(V2rayRoutingRuleMatcher Matcher, string OutboundTag)
{
    public static Dictionary<string, List<V2rayRoutingRule>> GroupByOutboundTag(List<V2rayRoutingRule> rules)
    {
        var result = new Dictionary<string, List<V2rayRoutingRule>>();
        foreach (var group in rules.GroupBy(r => r.OutboundTag))
        {
            result[group.Key] = group.ToList();
        }
        return result;
    }

    public static Dictionary<V2rayRoutingRuleMatcher.MatchByKind, List<V2rayRoutingRule>> GroupByMatchByKind(List<V2rayRoutingRule> rules)
    {
        var result = new Dictionary<V2rayRoutingRuleMatcher.MatchByKind, List<V2rayRoutingRule>>();
        foreach (var group in rules.GroupBy(r => r.Matcher.MatchBy))
        {
            result[group.Key] = group.ToList();
        }
        return result;
    }
}

