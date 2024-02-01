using System.Net;

namespace Crupest.V2ray;

public class V2rayV5StaticHostRule
{
    public enum MatcherKind
    {
        Full,
        Subdomain,
        Keyword,
        Regex
    }

    public V2rayV5StaticHostRule(MatcherKind matcher, string domain, IV2rayStaticHostResolveResult resolveResult)
    {
        Matcher = matcher;
        Domain = domain;
        ResolveResult = resolveResult;
    }

    public MatcherKind Matcher { get; }
    public string Domain { get; }
    public IV2rayStaticHostResolveResult ResolveResult { get; }

    public Dictionary<string, object> ToJsonObject()
    {
        var result = new Dictionary<string, object>
        {
            ["type"] = Enum.GetName(Matcher)!,
            ["domain"] = Domain
        };

        foreach (var (key, value) in ResolveResult.GetJsonProperties())
        {
            result.Add(key, value);
        }

        return result;
    }

    public static V2rayV5StaticHostRule IpRule(MatcherKind matcher, string domain, IEnumerable<string> ips)
    {
        return new V2rayV5StaticHostRule(matcher, domain, new V2rayStaticHostIpResolveResult(ips));
    }

    public static V2rayV5StaticHostRule DomainRule(MatcherKind matcher, string domain, string resolvedDomain)
    {
        return new V2rayV5StaticHostRule(matcher, domain, new V2rayStaticHostDomainResolveResult(resolvedDomain));
    }

    public static V2rayV5StaticHostRule Parse(string str)
    {
        var components = str.Trim().Split(' ', StringSplitOptions.TrimEntries | StringSplitOptions.RemoveEmptyEntries).ToList();

        if (components.Count <= 1)
        {
            throw new FormatException("The str only has one or no component.");
        }

        var matcher = MatcherKind.Subdomain;

        if (Enum.TryParse<MatcherKind>(components[0], out var m))
        {
            matcher = m;
            components.RemoveAt(0);
        }

        if (components.Count <= 1)
        {
            throw new FormatException("The str only has one component after remove matcher.");
        }

        var domain = components[0];
        components.RemoveAt(0);

        if (components.Count > 1 || IPAddress.TryParse(components[0], out var _))
        {
            return new V2rayV5StaticHostRule(matcher, domain, new V2rayStaticHostIpResolveResult(components));
        }
        else
        {
            return new V2rayV5StaticHostRule(matcher, domain, new V2rayStaticHostDomainResolveResult(domain));
        }
    }
}
