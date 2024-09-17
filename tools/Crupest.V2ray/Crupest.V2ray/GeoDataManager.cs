using System.IO.Compression;

namespace Crupest.V2ray;

public interface IGeoSiteEntry
{
    bool IsInclude { get; }
    string Value { get; }
}

public record GeoSiteIncludeEntry(string Value, string ContainingSite) : IGeoSiteEntry
{
    public bool IsInclude => true;
}

public record GeoSiteRuleEntry(V2rayHostMatcherKind Kind, string Value, List<string> Attributes, string ContainingSite) : IGeoSiteEntry
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
                    throw new FormatException($"Invalid geo site rule in line {line}. Invalid include value.");
                }
                entries.Add(new GeoSiteIncludeEntry(include, name));
                continue;
            }

            var segments = value.Split(':', StringSplitOptions.TrimEntries | StringSplitOptions.RemoveEmptyEntries);
            if (segments.Length > 2)
            {
                throw new FormatException($"Invalid geo site rule in line {line}. More than one ':'.");
            }

            V2rayHostMatcherKind kind;
            if (segments.Length == 2)
            {
                kind = segments[0] switch
                {
                    "domain" => kind = V2rayHostMatcherKind.DomainSuffix,
                    "full" => kind = V2rayHostMatcherKind.DomainFull,
                    "keyword" => kind = V2rayHostMatcherKind.DomainKeyword,
                    "regexp" => kind = V2rayHostMatcherKind.DomainRegex,
                    _ => throw new FormatException($"Invalid geo site rule in line {line}. Unknown matcher.")
                };
            }
            else
            {
                kind = V2rayHostMatcherKind.DomainSuffix;
            }

            var domainSegments = segments[^1].Split('@', StringSplitOptions.TrimEntries);
            var domain = domainSegments[0];
            if (Uri.CheckHostName(domain) != UriHostNameType.Dns)
            {
                throw new FormatException($"Invalid geo site rule in line {line}. Invalid domain.");
            }

            List<string> attributes = [];
            foreach (var s in domainSegments)
            {
                if (s.Length == 0)
                {
                    throw new FormatException($"Invalid geo site rule in line {line}. Empty attribute value.");
                }
                attributes.Add(s);
            }

            entries.Add(new GeoSiteRuleEntry(kind, domain, attributes, name));
        }
        return new GeoSite(name, entries);
    }
}

public class GeoSiteDataParser(string directory)
{
    private static List<GeoSite> Parse(string directory)
    {
        var sites = new List<GeoSite>();
        foreach (var file in Directory.GetFileSystemEntries(directory))
        {
            var path = Path.Combine(directory, file);
            var content = File.ReadAllText(path);
            sites.Add(GeoSite.Parse(file, content));
        }
        return sites;
    }

    public string DataDirectory { get; } = directory;

    public List<GeoSite> Sites { get; } = Parse(directory);
}

public class GeoDataManager
{
    public const string GeoSiteFileName = "geosite.dat";
    public const string GeoIpFileName = "geoip.dat";
    public const string GeoIpCnFileName = "geoip-only-cn-private.dat";
    public const string V2rayGithubOrganization = "v2fly";
    public const string V2rayGeoSiteGithubRepository = "domain-list-community";
    public const string V2rayGeoIpGithubRepository = "geoip";
    public const string V2rayGeoSiteCnGithubReleaseFilename = "dlc.dat";
    public const string V2rayGeoIpGithubReleaseFilename = "geoip.dat";
    public const string V2rayGeoIpCnGithubReleaseFilename = "geoip-only-cn-private.dat";

    public static GeoDataManager Instance { get; } = new GeoDataManager();

    public record GeoDataAsset(string Name, string FileName, string GithubUser, string GithubRepo, string GithubReleaseFileName);

    public GeoDataManager()
    {
        Assets =
        [
            new("geosite", GeoSiteFileName, V2rayGithubOrganization, V2rayGeoSiteGithubRepository, V2rayGeoSiteGithubRepository),
            new("geoip", GeoIpFileName, V2rayGithubOrganization, V2rayGeoIpGithubRepository, V2rayGeoIpGithubReleaseFilename),
            new("geoip-cn", GeoIpCnFileName, V2rayGithubOrganization, V2rayGeoIpGithubRepository, V2rayGeoIpCnGithubReleaseFilename),
        ];
    }

    public List<GeoDataAsset> Assets { get; set; }

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

    private static void GithubDownloadRepository(HttpClient httpClient, string user, string repo, string outputPath)
    {
        using var responseStream = httpClient.GetStreamAsync(GetGithubRepositoryArchiveUrl(user, repo)).Result;
        using var outputFileStream = File.OpenWrite(outputPath);
        responseStream.CopyTo(outputFileStream);
    }

    private static void Unzip(string zipPath, string outputPath)
    {
        using var zip = ZipFile.OpenRead(zipPath) ?? throw new Exception($"Failed to open zip file {zipPath}");
        zip.ExtractToDirectory(outputPath);
    }

    private string DownloadAndExtractGeoSiteRepository(bool silent)
    {
        const string zipFileName = "v2ray-geosite-master.zip";
        using var httpClient = new HttpClient();
        var tempDirectory = Directory.CreateTempSubdirectory(Program.Name);
        var archivePath = Path.Combine(tempDirectory.FullName, zipFileName);
        var extractPath = Path.Combine(tempDirectory.FullName, "repo");
        GithubDownloadRepository(httpClient, V2rayGithubOrganization, V2rayGeoSiteGithubRepository, archivePath);
        Directory.CreateDirectory(extractPath);
        Unzip(archivePath, extractPath);
        return Path.Join(extractPath, "domain-list-community-master");
    }
}
