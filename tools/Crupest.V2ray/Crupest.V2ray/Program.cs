using System.Reflection;

namespace Crupest.V2ray;

public static class Program
{
    public const string ConfigTemplateFileName = "config.json.template";
    public const string VmessConfigFileName = "vmess.txt";
    public const string ProxyConfigFileName = "proxy.txt";
    public const string HostsConfigFileName = "hosts.txt";
    public const string ConfigOutputFileName = "config.json";

    public static string ExeDir { get; } = Path.GetFullPath(Path.GetDirectoryName(Assembly.GetExecutingAssembly().Location) ?? throw new Exception("Can't get the path of exe."));


    public static void Main(string[] args)
    {
        if (args.Length != 0)
        {
            if (args.Length != 1)
            {
                throw new Exception("Invalid command line arguments.");
            }
            var verb = args[0].ToLower();
            if (verb == "download-geodata" || verb == "dg")
            {
                var geoDataDownloader = new GeoDataDownloader();
                geoDataDownloader.Download(ExeDir);
                return;
            }
            throw new Exception("Invalid command line arguments.");
        }

        var v2rayController = new V2rayController();
        var configGenerationWatcher = new ConfigGenerationWatcher();

        configGenerationWatcher.Generate();
        v2rayController.Start();

        configGenerationWatcher.Run(() =>
        {
            configGenerationWatcher.Generate();
            v2rayController.Restart();
        });
    }
}
