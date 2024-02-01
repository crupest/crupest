namespace Crupest.V2ray;

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

