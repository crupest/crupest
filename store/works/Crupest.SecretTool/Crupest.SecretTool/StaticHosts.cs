namespace Crupest.SecretTool;

public record StaticHostRule(HostMatchKind MatchKind, string MatchString, List<string> ResolveResult)
{
    public string AddressString()
    {
        return MatchKind switch
        {
            HostMatchKind.DomainFull => MatchString,
            HostMatchKind.DomainSuffix => $"domain:{MatchString}",
            HostMatchKind.DomainKeyword => $"keyword:{MatchString}",
            HostMatchKind.DomainRegex => $"regexp:{MatchString}",
            _ => throw new ArgumentOutOfRangeException($"Match kind {MatchKind} is not allowed in static host rule."),
        };
    }

    public object ResolveResultToJsonObject()
    {
        return ResolveResult.Count == 1 ? ResolveResult[0] : ResolveResult;
    }
}

public class StaticHosts(List<StaticHostRule> rules) : IV4ConfigObject
{
    public List<StaticHostRule> Rules { get; } = rules;

    public Dictionary<string, object> ToJsonObjectV4() =>
        Rules.ToDictionary(rule => rule.AddressString(), rule => rule.ResolveResultToJsonObject());

    object IV4ConfigObject.ToJsonObjectV4()
    {
        return ToJsonObjectV4();
    }

    public static StaticHosts CreateFromHostMatchConfigString(string configString)
    {
        var config = new HostMatchConfig(configString, HostMatchKindExtensions.DomainMatchKinds, minComponentCount: 1);
        return new StaticHosts(config.Items.Select(i => new StaticHostRule(i.Kind, i.MatchString, [.. i.Values])).ToList());
    }
}
