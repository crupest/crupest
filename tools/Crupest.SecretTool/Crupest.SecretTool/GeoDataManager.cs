using System.IO.Compression;

namespace Crupest.SecretTool;

public interface IGeoSiteEntry
{
    bool IsInclude { get; }
    string Value { get; }
}

public record GeoSiteIncludeEntry(string Value, string ContainingSite) : IGeoSiteEntry
{
    public bool IsInclude => true;
}

public record GeoSiteRuleEntry(HostMatchKind Kind, string Value, List<string> Attributes, string ContainingSite) : IGeoSiteEntry
{
    public bool IsInclude => false;
}

public record GeoSite(string Name, List<IGeoSiteEntry> Entries)
{
    public static GeoSite Parse(string name, string str)
    {
        List<IGeoSiteEntry> entries = [];
        var listConfig = new ListConfig(str);
        foreach (var item in listConfig.Config)
        {
            var (value, line) = item;

            if (value.StartsWith("include:"))
            {
                var include = value["include:".Length..].Trim();
                if (include.Length == 0 || include.Contains(' '))
                {
                    throw new FormatException($"Invalid geo site rule '{name}' in line {line}. Invalid include value.");
                }
                entries.Add(new GeoSiteIncludeEntry(include, name));
                continue;
            }

            var segments = value.Split(':', StringSplitOptions.TrimEntries | StringSplitOptions.RemoveEmptyEntries);
            if (segments.Length > 2)
            {
                throw new FormatException($"Invalid geo site rule '{name}' in line {line}. More than one ':'.");
            }

            HostMatchKind kind;
            if (segments.Length == 2)
            {
                kind = segments[0] switch
                {
                    "domain" => kind = HostMatchKind.DomainSuffix,
                    "full" => kind = HostMatchKind.DomainFull,
                    "keyword" => kind = HostMatchKind.DomainKeyword,
                    "regexp" => kind = HostMatchKind.DomainRegex,
                    _ => throw new FormatException($"Invalid geo site rule '{name}' in line {line}. Unknown matcher.")
                };
            }
            else
            {
                kind = HostMatchKind.DomainSuffix;
            }

            var domainSegments = segments[^1].Split('@', StringSplitOptions.TrimEntries);
            var domain = domainSegments[0];
            if (kind != HostMatchKind.DomainRegex && Uri.CheckHostName(domain) != UriHostNameType.Dns)
            {
                throw new FormatException($"Invalid geo site rule '{name}' in line {line}. Invalid domain.");
            }

            List<string> attributes = [];
            foreach (var s in domainSegments[1..])
            {
                if (s.Length == 0)
                {
                    throw new FormatException($"Invalid geo site rule '{name}' in line {line}. Empty attribute value.");
                }
                attributes.Add(s);
            }

            entries.Add(new GeoSiteRuleEntry(kind, domain, attributes, name));
        }
        return new GeoSite(name, entries);
    }
}

public class GeoSiteData(string directory)
{
    private static List<GeoSite> Parse(string directory)
    {
        var sites = new List<GeoSite>();
        foreach (var path in Directory.GetFileSystemEntries(directory))
        {
            var content = File.ReadAllText(path);
            sites.Add(GeoSite.Parse(Path.GetFileName(path), content));
        }
        return sites;
    }

    public string DataDirectory { get; } = directory;

    public List<GeoSite> Sites { get; } = Parse(directory);

    public GeoSite? GetSite(string name)
    {
        return Sites.Where(s => s.Name == name).FirstOrDefault();
    }

    public List<GeoSiteRuleEntry> GetEntriesRecursive(List<string> sites,
        List<HostMatchKind>? onlyMatcherKinds = null, List<string>? onlyAttributes = null)
    {
        List<GeoSiteRuleEntry> entries = [];
        HashSet<string> visited = [];
        HashSet<HostMatchKind>? kinds = onlyMatcherKinds?.ToHashSet();

        void Visit(string site)
        {
            if (visited.Contains(site))
            {
                return;
            }

            visited.Add(site);
            var siteData = GetSite(site);
            if (siteData == null)
            {
                return;
            }
            foreach (var entry in siteData.Entries)
            {
                if (entry is GeoSiteIncludeEntry includeEntry)
                {
                    Visit(includeEntry.Value);
                }
                else if (entry is GeoSiteRuleEntry geoSiteRuleEntry)
                {
                    if (kinds != null && !kinds.Contains(geoSiteRuleEntry.Kind))
                    {
                        continue;
                    }

                    if (onlyAttributes != null && !geoSiteRuleEntry.Attributes.Intersect(onlyAttributes).Any())
                    {
                        continue;
                    }

                    entries.Add(geoSiteRuleEntry);
                }
            }
        }

        foreach (var s in sites)
        {
            Visit(s);
        }

        return entries;
    }
}

public class GeoDataManager
{
    public const string GeoSiteFileName = "geosite.dat";
    public const string GeoIpFileName = "geoip.dat";
    public const string GeoIpCnFileName = "geoip-only-cn-private.dat";

    public static class ToolGithub
    {
        public const string Organization = "v2fly";
        public const string GeoSiteRepository = "domain-list-community";
        public const string GeoIpRepository = "geoip";
        public const string GeoSiteReleaseFilename = "dlc.dat";
        public const string GeoIpReleaseFilename = "geoip.dat";
        public const string GeoIpCnReleaseFilename = "geoip-only-cn-private.dat";
    }

    public static GeoDataManager Instance { get; } = new GeoDataManager();

    public record GeoDataAsset(string Name, string FileName, string GithubUser, string GithubRepo, string GithubReleaseFileName);

    public GeoDataManager()
    {
        Assets =
        [
            new("geosite", GeoSiteFileName, ToolGithub.Organization, ToolGithub.GeoSiteRepository, ToolGithub.GeoSiteRepository),
            new("geoip", GeoIpFileName, ToolGithub.Organization, ToolGithub.GeoIpRepository, ToolGithub.GeoIpReleaseFilename),
            new("geoip-cn", GeoIpCnFileName, ToolGithub.Organization, ToolGithub.GeoIpRepository, ToolGithub.GeoIpCnReleaseFilename),
        ];
    }

    public List<GeoDataAsset> Assets { get; set; }

    public GeoSiteData? GeoSiteData { get; set; }

    public GeoSiteData GetOrCreateGeoSiteData(bool clean, bool silent)
    {
        if (GeoSiteData is not null) { return GeoSiteData; }
        GeoSiteData = DownloadAndGenerateGeoSiteData(clean, silent);
        return GeoSiteData;
    }

    private static string GetReleaseFileUrl(string user, string repo, string fileName)
    {
        return $"https://github.com/{user}/{repo}/releases/latest/download/{fileName}";
    }

    private static void GithubDownloadRelease(HttpClient httpClient, string user, string repo, string fileName, string outputPath)
    {
        using var responseStream = httpClient.GetStreamAsync(GetReleaseFileUrl(user, repo, fileName)).Result;
        using var outputFileStream = File.OpenWrite(outputPath);
        responseStream.CopyTo(outputFileStream);
    }

    public bool HasAllAssets(string directory, out List<string> missing)
    {
        missing = [];
        foreach (var asset in Assets)
        {
            var assetPath = Path.Combine(directory, asset.FileName);
            if (!File.Exists(assetPath))
            {
                missing.Add(asset.Name);
            }
        }
        return missing.Count == 0;
    }

    public void Download(string outputDir, bool silent)
    {
        using var httpClient = new HttpClient();

        foreach (var asset in Assets)
        {
            if (!silent)
            {
                Console.WriteLine($"Downloading {asset.Name}...");
            }
            GithubDownloadRelease(httpClient, asset.GithubUser, asset.GithubRepo, asset.GithubReleaseFileName, Path.Combine(outputDir, asset.FileName));
            if (!silent)
            {
                Console.WriteLine($"Downloaded {asset.Name}!");
            }
        }
    }

    private static string GetGithubRepositoryArchiveUrl(string user, string repo)
    {
        return $"https://github.com/{user}/{repo}/archive/refs/heads/master.zip";
    }

    private static void GithubDownloadRepository(HttpClient httpClient, string user, string repo, string outputPath, bool silent)
    {
        var url = GetGithubRepositoryArchiveUrl(user, repo);
        if (!silent) { Console.WriteLine($"Begin to download data from {url} to {outputPath}."); }
        using var responseStream = httpClient.GetStreamAsync(url).Result;
        using var outputFileStream = File.OpenWrite(outputPath);
        responseStream.CopyTo(outputFileStream);
        if (!silent) { Console.WriteLine("Succeeded to download."); }
    }

    private static void Unzip(string zipPath, string outputPath)
    {
        using var zip = ZipFile.OpenRead(zipPath) ?? throw new Exception($"Failed to open zip file {zipPath}");
        zip.ExtractToDirectory(outputPath);
    }

    private static string DownloadAndExtractGeoDataRepository(bool cleanTempDirIfFailed, bool silent, out string tempDirectoryPath)
    {
        tempDirectoryPath = "";
        const string zipFileName = "v2ray-geosite-master.zip";
        using var httpClient = new HttpClient();
        var tempDirectory = Directory.CreateTempSubdirectory(Program.Name);
        tempDirectoryPath = tempDirectory.FullName;
        try
        {
            var archivePath = Path.Combine(tempDirectoryPath, zipFileName);
            var extractPath = Path.Combine(tempDirectoryPath, "repo");
            GithubDownloadRepository(httpClient, ToolGithub.Organization, ToolGithub.GeoSiteRepository, archivePath, silent);
            if (!silent) { Console.WriteLine($"Extract geo data to {extractPath}."); }
            Directory.CreateDirectory(extractPath);
            Unzip(archivePath, extractPath);
            if (!silent) { Console.WriteLine($"Extraction done."); }
            return Path.Join(extractPath, "domain-list-community-master");
        }
        catch (Exception)
        {
            if (cleanTempDirIfFailed)
            {
                Directory.Delete(tempDirectoryPath, true);
            }
            throw;
        }
    }

    private static GeoSiteData DownloadAndGenerateGeoSiteData(bool clean, bool silent)
    {
        var repoDirectory = DownloadAndExtractGeoDataRepository(clean, silent, out var tempDirectoryPath);
        try
        {
            return new GeoSiteData(Path.Join(repoDirectory, "data"));
        }
        finally
        {
            if (clean)
            {
                Directory.Delete(tempDirectoryPath, true);
            }
        }
    }
}
