using System.Reflection;

namespace Crupest.V2ray;

public static class Program
{
    public static string CrupestV2rayDirectory { get; } =
        Environment.GetEnvironmentVariable("CRUPEST_V2RAY_DIR") ??
        Path.GetFullPath(Path.GetDirectoryName(
            Assembly.GetExecutingAssembly().Location) ?? throw new Exception("Can't get the path of Crupest.V2ray."));

    private const string ConfigOutputFileName = "config.json";

    public static void RunV2rayAndWatchConfigChange()
    {
        var v2rayPath = V2rayController.FindExecutable(CrupestV2rayDirectory) ??
            throw new Exception("Can't find v2ray executable either in Crupest.V2ray directory or in PATH.");

        var v2rayController = new V2rayController(v2rayPath, Path.Combine(CrupestV2rayDirectory, ConfigOutputFileName), CrupestV2rayDirectory);
        var configFileWatcher = new FileWatcher(CrupestV2rayDirectory, V2rayConfig.ConfigFileNames);

        V2rayConfig.FromDirectoryAndWriteToFile(CrupestV2rayDirectory, Path.Join(CrupestV2rayDirectory, ConfigOutputFileName));
        v2rayController.Start();

        configFileWatcher.OnChanged += () =>
        {
            V2rayConfig.FromDirectoryAndWriteToFile(CrupestV2rayDirectory, Path.Join(CrupestV2rayDirectory, ConfigOutputFileName));
            v2rayController.Restart();
        };

        configFileWatcher.Run();
    }

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
                geoDataDownloader.Download(CrupestV2rayDirectory);
                return;
            }
            else if (verb == "generate" || verb == "g")
            {
                var config = V2rayConfig.FromDirectory(CrupestV2rayDirectory);
                Console.Out.WriteLine(config.ToJsonStringV4());
                return;
            }
            throw new Exception("Invalid command line arguments.");
        }

        RunV2rayAndWatchConfigChange();
    }
}
