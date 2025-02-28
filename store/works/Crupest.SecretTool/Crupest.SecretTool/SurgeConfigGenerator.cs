namespace Crupest.SecretTool;

public class SurgeConfigGenerator(ProxyFile proxyFile, GeoSiteData geoData)
{
    public ProxyFile ProxyFile => proxyFile;
    public GeoSiteData GeoData => geoData;

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

    public static string GenerateSurgeRuleSetString(List<RoutingRuleMatcher> rules)
    {
        return string.Join('\n', rules.Select(r => ToSurgeRuleString(r.MatchKind, r.MatchString)));
    }

    public string GenerateChinaRuleSet()
    {
        return GenerateSurgeRuleSetString(proxyFile.GetChinaRulesByGeoSite(GeoData));
    }

    public string GenerateGlobalRuleSet()
    {
        return GenerateSurgeRuleSetString(proxyFile.GetRulesFlattenGeoSite(geoData, true));
    }

    public static void GenerateTo(ProxyFile proxyFile, GeoSiteData geoSiteData, string cnPath, string globalPath, bool silent)
    {
        var generator = new SurgeConfigGenerator(proxyFile, geoSiteData);
        File.WriteAllText(cnPath, generator.GenerateChinaRuleSet());
        if (!silent) Console.WriteLine($"China rule set written to {cnPath}.");
        File.WriteAllText(globalPath, generator.GenerateGlobalRuleSet());
        if (!silent) Console.WriteLine($"Global rule set written to {globalPath}.");
    }

    public static void GenerateTo(string directory, string cnPath, string globalPath, bool clean, bool silent)
    {
        var geoSiteData = GeoDataManager.Instance.GetOrCreateGeoSiteData(clean, silent);
        var proxyFile = new ProxyFile(Path.Combine(directory, ToolConfig.ProxyConfigFileName));
        var generator = new SurgeConfigGenerator(proxyFile, geoSiteData);
        File.WriteAllText(cnPath, generator.GenerateChinaRuleSet());
        if (!silent) Console.WriteLine($"China rule set written to {cnPath}.");
        File.WriteAllText(globalPath, generator.GenerateGlobalRuleSet());
        if (!silent) Console.WriteLine($"Global rule set written to {globalPath}.");
    }
}
