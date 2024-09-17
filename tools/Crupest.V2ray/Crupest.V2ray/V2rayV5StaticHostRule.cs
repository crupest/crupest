using System.Net;

namespace Crupest.V2ray;

public interface IV2rayStaticHostResolveResult
{
    IDictionary<string, object> GetJsonProperties();
}

public class V2rayStaticHostDomainResolveResult : IV2rayStaticHostResolveResult
{
    public V2rayStaticHostDomainResolveResult(string domain)
    {
        Domain = domain;
    }

    public string Domain { get; }

    public IDictionary<string, object> GetJsonProperties()
    {
        return new Dictionary<string, object>
        {

            ["proxiedDomain"] = Domain
        };
    }
}

public class V2rayStaticHostIpResolveResult : IV2rayStaticHostResolveResult
{
    public V2rayStaticHostIpResolveResult(IEnumerable<string> ips)
    {
        Ips = ips.ToList();
    }

    public IReadOnlyList<string> Ips { get; }

    public IDictionary<string, object> GetJsonProperties()
    {
        return new Dictionary<string, object>
        {
            ["ip"] = Ips
        };
    }
}


public class V2rayV5StaticHostRule(V2rayV5StaticHostRule.MatcherKind matcher, string domain, IV2rayStaticHostResolveResult resolveResult)
{
    public enum MatcherKind
    {
        Full,
        Subdomain,
        Keyword,
        Regex
    }

    public MatcherKind Matcher { get; } = matcher;
    public string Domain { get; } = domain;
    public IV2rayStaticHostResolveResult ResolveResult { get; } = resolveResult;

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
