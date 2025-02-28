namespace Crupest.SecretTool;

public class ProxyFile : HostMatchConfigFile
{
    public ProxyFile(string path) : base(path, [.. Enum.GetValues<HostMatchKind>()], maxComponentCount: 0)
    {
        RoutingRuleMatchers = Config.Items.Select(i => new RoutingRuleMatcher(i.Kind, i.MatchString)).ToList();
    }

    public List<RoutingRuleMatcher> RoutingRuleMatchers { get; }

    public List<RoutingRuleMatcher> GetChinaRulesByGeoSite(GeoSiteData geoSiteData)
    {
        var geoSites = RoutingRuleMatchers.Where(m => m.MatchKind == HostMatchKind.GeoSite).Select(i => i.MatchString).ToList();
        return geoSiteData.GetEntriesRecursive(geoSites, HostMatchKindExtensions.DomainMatchKinds, ["cn"]).Select(e => e.GetRoutingRuleMatcher()).ToList();
    }

    public List<RoutingRuleMatcher> GetRulesFlattenGeoSite(GeoSiteData geoSiteData, bool noCn = false)
    {
        var geoSites = RoutingRuleMatchers.Where(m => m.MatchKind == HostMatchKind.GeoSite).Select(i => i.MatchString).ToList();
        var flattenGeoSiteRules = geoSiteData.GetEntriesRecursive(geoSites, HostMatchKindExtensions.DomainMatchKinds)
            .Where(e => !noCn || !e.Attributes.Contains("cn"))
            .Select(e => e.GetRoutingRuleMatcher())
            .ToList();
        var otherRules = RoutingRuleMatchers.Where(m => m.MatchKind != HostMatchKind.GeoSite).ToList();
        return [
            ..flattenGeoSiteRules,
            ..otherRules
        ];
    }
}
