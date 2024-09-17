namespace Crupest.V2ray;

public class SurgeConfigGenerator(ProxyFile proxyFile, GeoSiteData geoSiteData)
{
    public ProxyFile ProxyFile { get; } = proxyFile;
    public GeoSiteData GeoSiteData { get; } = geoSiteData;

    private static string ToSurgeRuleString(V2rayHostMatcherKind kind, string value)
    {
        var ruleType = kind switch
        {
            V2rayHostMatcherKind.DomainFull => "DOMAIN",
            V2rayHostMatcherKind.DomainSuffix => "DOMAIN-SUFFIX",
            V2rayHostMatcherKind.DomainKeyword => "DOMAIN-KEYWORD",
            V2rayHostMatcherKind.DomainRegex => "URL-REGEX",
            _ => throw new Exception("Unacceptable matcher kind for Surge rule.")
        };

        return $"{ruleType},{value}";
    }

    private static List<V2rayHostMatcherKind> DomainMatcherKinds { get; } = [
        V2rayHostMatcherKind.DomainFull, V2rayHostMatcherKind.DomainKeyword,
        V2rayHostMatcherKind.DomainRegex, V2rayHostMatcherKind.DomainSuffix,
    ];

    public string GenerateChinaRuleSet()
    {
        var geoSites = ProxyFile.MatcherConfig.Items.Where(i => i.Kind == V2rayHostMatcherKind.GeoSite).Select(i => i.Matcher).ToList();
        var cnRules = GeoSiteData.GetEntriesRecursive(geoSites, DomainMatcherKinds, ["cn"]).ToList();
        return string.Join('\n', cnRules.Select(r => ToSurgeRuleString(r.Kind, r.Value)));
    }

    public string GenerateGlobalRuleSet()
    {
        var geoSites = ProxyFile.MatcherConfig.Items.Where(i => i.Kind == V2rayHostMatcherKind.GeoSite).Select(i => i.Matcher).ToList();
        var nonCnRules = GeoSiteData.GetEntriesRecursive(geoSites, DomainMatcherKinds).Where(e => !e.Attributes.Contains("cn")).ToList();
        var domainRules = ProxyFile.MatcherConfig.Items.Where(i => DomainMatcherKinds.Contains(i.Kind)).ToList();
        return string.Join('\n', [
            ..nonCnRules.Select(r => ToSurgeRuleString(r.Kind, r.Value)),
            ..domainRules.Select(r => ToSurgeRuleString(r.Kind, r.Matcher))
        ]);
    }

    public static SurgeConfigGenerator Create(string proxyFilePath, bool clean, bool silent)
    {
        var proxyFile = new ProxyFile(proxyFilePath);
        var geoSiteData = GeoDataManager.Instance.GetOrCreateGeoSiteData(clean, silent);
        return new SurgeConfigGenerator(proxyFile, geoSiteData);
    }

    public static void GenerateTo(string proxyFilePath, string cnPath, string globalPath, bool clean, bool silent)
    {
        var generator = Create(proxyFilePath, clean, silent);
        File.WriteAllText(cnPath, generator.GenerateChinaRuleSet());
        if (!silent) Console.WriteLine($"China rule set written to {cnPath}.");
        File.WriteAllText(globalPath, generator.GenerateGlobalRuleSet());
        if (!silent) Console.WriteLine($"Global rule set written to {globalPath}.");
    }
}
