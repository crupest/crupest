using System.Reflection;

namespace Crupest.V2ray;

public static class Program
{
    public static string Name { get; } = typeof(Program).Namespace ?? throw new Exception("Can't get the name of Crupest.V2ray.");

    public static string CrupestV2rayDirectory { get; } =
        Environment.GetEnvironmentVariable("CRUPEST_V2RAY_DIR") ??
        Path.GetFullPath(Path.GetDirectoryName(
            Assembly.GetExecutingAssembly().Location) ?? throw new Exception("Can't get the path of Crupest.V2ray."));

    private const string ConfigOutputFileName = "config.json";

    public static void RunV2rayAndWatchConfigChange()
    {
        var v2rayPath = V2rayController.FindExecutable(CrupestV2rayDirectory, out var isLocal) ??
            throw new Exception("Can't find v2ray executable either in Crupest.V2ray directory or in PATH.");

        string? assetsPath;
        if (isLocal)
        {
            assetsPath = CrupestV2rayDirectory;
            var assetsComplete = GeoDataManager.Instance.HasAllAssets(CrupestV2rayDirectory, out var missing);
            if (!assetsComplete)
            {
                throw new Exception($"Missing assets: {string.Join(", ", missing)} in {CrupestV2rayDirectory}. This v2ray is local. So only use assets in Crupest.V2ray directory.");
            }
        }
        else
        {
            assetsPath = CrupestV2rayDirectory;
            var assetsComplete = GeoDataManager.Instance.HasAllAssets(CrupestV2rayDirectory, out var missing);
            if (!assetsComplete)
            {
                Console.WriteLine($"Missing assets: {string.Join(", ", missing)} in {CrupestV2rayDirectory}. This v2ray is global. So fallback to its own assets.");
                assetsPath = null;
            }
        }

        var v2rayController = new V2rayController(v2rayPath, Path.Combine(CrupestV2rayDirectory, ConfigOutputFileName), assetsPath);
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
                GeoDataManager.Instance.Download(CrupestV2rayDirectory, false);
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
