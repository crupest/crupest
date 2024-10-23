using System.Reflection;

namespace Crupest.SecretTool;

public static class Program
{
    public static string Name { get; } = typeof(Program).Namespace ?? throw new Exception("Can't get the name of Crupest.SecretTool.");

    public static string CrupestSecretToolDirectory { get; } =
        Environment.GetEnvironmentVariable("CRUPEST_V2RAY_DIR") ??
        Path.GetFullPath(Path.GetDirectoryName(
            Assembly.GetExecutingAssembly().Location) ?? throw new Exception("Can't get the path of Crupest.SecretTool."));

    private const string ConfigOutputFileName = "config.json";
    private const string SurgeRuleSetChinaOutputFileName = "ChinaRuleSet.txt";
    private const string SurgeRuleSetGlobalOutputFileName = "GlobalRuleSet.txt";

    public const string RestartLabelFileName = "restart.label";
    public static string RestartLabelFilePath { get; } = Path.Combine(CrupestSecretToolDirectory, RestartLabelFileName);

    public static void RunToolAndWatchConfigChange()
    {
        var executablePath = Controller.FindExecutable(CrupestSecretToolDirectory, out var isLocal) ??
            throw new Exception("Can't find v2ray executable either in Crupest.SecretTool directory or in PATH.");

        string? assetsPath;
        if (isLocal)
        {
            assetsPath = CrupestSecretToolDirectory;
            var assetsComplete = GeoDataManager.Instance.HasAllAssets(CrupestSecretToolDirectory, out var missing);
            if (!assetsComplete)
            {
                throw new Exception($"Missing assets: {string.Join(", ", missing)} in {CrupestSecretToolDirectory}. This v2ray is local. So only use assets in Crupest.SecretTool directory.");
            }
        }
        else
        {
            assetsPath = CrupestSecretToolDirectory;
            var assetsComplete = GeoDataManager.Instance.HasAllAssets(CrupestSecretToolDirectory, out var missing);
            if (!assetsComplete)
            {
                Console.WriteLine($"Missing assets: {string.Join(", ", missing)} in {CrupestSecretToolDirectory}. This v2ray is global. So fallback to its own assets.");
                assetsPath = null;
            }
        }

        var controller = new Controller(executablePath, Path.Combine(CrupestSecretToolDirectory, ConfigOutputFileName), assetsPath);
        var configFileWatcher = new FileWatcher(CrupestSecretToolDirectory,
            [.. ToolConfig.ConfigFileNames, RestartLabelFileName]);

        ToolConfig.FromDirectoryAndWriteToFile(CrupestSecretToolDirectory, Path.Join(CrupestSecretToolDirectory, ConfigOutputFileName));
        controller.Start();

        configFileWatcher.OnChanged += () =>
        {
            ToolConfig.FromDirectoryAndWriteToFile(CrupestSecretToolDirectory, Path.Join(CrupestSecretToolDirectory, ConfigOutputFileName));
            controller.Restart();
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
                GeoDataManager.Instance.Download(CrupestSecretToolDirectory, false);
                return;
            }
            else if (verb == "generate-surge-rule-set" || verb == "gsr")
            {
                SurgeConfigGenerator.GenerateTo(
                    CrupestSecretToolDirectory,
                    Path.Join(CrupestSecretToolDirectory, SurgeRuleSetChinaOutputFileName),
                    Path.Join(CrupestSecretToolDirectory, SurgeRuleSetGlobalOutputFileName),
                    true, true
                );
                return;
            }
            else if (verb == "generate-sing-config" || verb == "gs")
            {
                var config = ToolConfig.FromDirectoryForSing(CrupestSecretToolDirectory, true, true);
                Console.Out.WriteLine(config.ToSingConfigString());
                return;
            }
            else if (verb == "generate" || verb == "g")
            {
                var config = ToolConfig.FromDirectory(CrupestSecretToolDirectory);
                Console.Out.WriteLine(config.ToJsonStringV4());
                return;
            }
            throw new Exception("Invalid command line arguments.");
        }

        RunToolAndWatchConfigChange();
    }
}
