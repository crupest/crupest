namespace Crupest.SecretTool;

public class SurgeConfigGenerator(ProxyFile proxyFile, GeoSiteData geoSiteData)
{
    public ProxyFile ProxyFile { get; } = proxyFile;
    public GeoSiteData GeoSiteData { get; } = geoSiteData;

    private static string ToSurgeRuleString(HostMatchKind kind, string value)
    {
        var ruleType = kind switch
        {
            HostMatchKind.DomainFull => "DOMAIN",
            HostMatchKind.DomainSuffix => "DOMAIN-SUFFIX",
            HostMatchKind.DomainKeyword => "DOMAIN-KEYWORD",
            HostMatchKind.DomainRegex => "URL-REGEX",
            _ => throw new Exception("Unacceptable matcher kind for Surge rule.")
        };

        return $"{ruleType},{value}";
    }

    private static List<HostMatchKind> DomainMatcherKinds { get; } = [
        HostMatchKind.DomainFull, HostMatchKind.DomainKeyword,
        HostMatchKind.DomainRegex, HostMatchKind.DomainSuffix,
    ];

    public string GenerateChinaRuleSet()
    {
        var geoSites = ProxyFile.Config.Items.Where(i => i.Kind == HostMatchKind.GeoSite).Select(i => i.MatchString).ToList();
        var cnRules = GeoSiteData.GetEntriesRecursive(geoSites, DomainMatcherKinds, ["cn"]).ToList();
        return string.Join('\n', cnRules.Select(r => ToSurgeRuleString(r.Kind, r.Value)));
    }

    public string GenerateGlobalRuleSet()
    {
        var geoSites = ProxyFile.Config.Items.Where(i => i.Kind == HostMatchKind.GeoSite).Select(i => i.MatchString).ToList();
        var nonCnRules = GeoSiteData.GetEntriesRecursive(geoSites, DomainMatcherKinds).Where(e => !e.Attributes.Contains("cn")).ToList();
        var domainRules = ProxyFile.Config.Items.Where(i => DomainMatcherKinds.Contains(i.Kind)).ToList();
        return string.Join('\n', [
            ..nonCnRules.Select(r => ToSurgeRuleString(r.Kind, r.Value)),
            ..domainRules.Select(r => ToSurgeRuleString(r.Kind, r.MatchString))
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
