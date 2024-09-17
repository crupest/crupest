namespace Crupest.V2ray;

public class ProxyFile(string path) :
    HostMatcherConfigFile(path, [.. Enum.GetValues<V2rayHostMatcherKind>()], maxComponentCount: 0)
{
    public V2rayRouting ToV2rayRouting(string outboundTag, bool directGeositeCn)
    {
        return new V2rayRouting(
            MatcherConfig.Items.Select(
                i => new V2rayRoutingRule(i.Kind, i.Matcher, outboundTag)).ToList(),
            directGeositeCn
        );
    }
}
