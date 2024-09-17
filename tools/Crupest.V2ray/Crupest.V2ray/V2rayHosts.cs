namespace Crupest.V2ray;

public record V2rayHostRule(V2rayHostMatcherKind MatcherKind, string MatcherString, List<string> ResolveResult)
{
    public string AddressString()
    {
        return MatcherKind switch
        {
            V2rayHostMatcherKind.DomainFull => MatcherString,
            V2rayHostMatcherKind.DomainSuffix => $"domain:{MatcherString}",
            V2rayHostMatcherKind.DomainKeyword => $"keyword:{MatcherString}",
            V2rayHostMatcherKind.DomainRegex => $"regexp:{MatcherString}",
            _ => throw new ArgumentOutOfRangeException($"Matcher {MatcherKind} is not allowed in host rule."),
        };
    }

    public object ResolveResultToJsonObject()
    {
        return ResolveResult.Count == 1 ? ResolveResult[0] : ResolveResult;
    }
}

public class V2rayHosts(List<V2rayHostRule> rules) : IV2rayV4ConfigObject
{
    public List<V2rayHostRule> Rules { get; } = rules;

    public Dictionary<string, object> ToJsonObjectV4() =>
        Rules.ToDictionary(rule => rule.AddressString(), rule => rule.ResolveResultToJsonObject());

    object IV2rayV4ConfigObject.ToJsonObjectV4()
    {
        return ToJsonObjectV4();
    }

    public static V2rayHosts CreateFromConfigString(string configString)
    {
        var matcherConfig = new V2rayHostMatcherConfig(configString,
            [V2rayHostMatcherKind.DomainFull, V2rayHostMatcherKind.DomainKeyword, V2rayHostMatcherKind.DomainRegex, V2rayHostMatcherKind.DomainSuffix], minComponentCount: 1);

        return new V2rayHosts(matcherConfig.Items.Select(i => new V2rayHostRule(i.Kind, i.Matcher, [.. i.Values])).ToList());
    }
}
