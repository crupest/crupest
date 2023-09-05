namespace Crupest.V2ray;

public class GeoDataDownloader
{
    public record GithubReleaseAsset(string ResourceName, string User, string Repo, string AssetName, string Output);

    public GeoDataDownloader()
    {
        Resources = new()
        {
            new("geosite", "v2fly", "domain-list-community", "dlc.dat", "geosite.dat"),
            new("geoip", "v2fly", "geoip", "geoip.dat", "geoip.dat"),
            new("geosite", "v2fly", "geoip", "geoip-only-cn-private.dat", "geoip-only-cn-private.dat")
        };
    }

    public List<GithubReleaseAsset> Resources { get; set; }

    public static string GetReleaseFileUrl(string user, string repo, string assetName)
    {
        return $"https://github.com/{user}/{repo}/releases/latest/download/{assetName}";
    }

    public static void GithubDownload(HttpClient httpClient, string user, string repo, string assetName, string outputPath)
    {
        using var responseStream = httpClient.GetStreamAsync(GetReleaseFileUrl(user, repo, assetName)).Result;
        using var outputFileStream = File.OpenWrite(outputPath);
        responseStream.CopyTo(outputFileStream);
    }

    public void Download(string outputDir)
    {
        using var httpClient = new HttpClient();

        foreach (var resource in Resources)
        {
            Console.WriteLine($"Downloading {resource.ResourceName}...");
            GithubDownload(httpClient, resource.User, resource.Repo, resource.AssetName, Path.Combine(outputDir, resource.Output));
            Console.WriteLine($"Downloaded {resource.ResourceName}!");
        }
    }
}
