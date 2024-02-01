namespace Crupest.V2ray;

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

