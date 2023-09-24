namespace Crupest.V2ray;

public record V2rayHosts(List<V2rayHostRule> Rules)
{
    public V2rayHosts() : this(new List<V2rayHostRule>()) { }

    public Dictionary<string, List<string>> ToJsonObject()
    {
        var result = new Dictionary<string, List<string>>();
        foreach (var rule in Rules)
        {
            result.Add(rule.Origin, rule.Resolved);
        }
        return result;
    }

    public static V2rayHosts FromStringList(List<string> list)
    {
        var hosts = new V2rayHosts();
        foreach (var str in list)
        {
            hosts.Rules.Add(V2rayHostRule.Parse(str));
        }
        return hosts;
    }
}
